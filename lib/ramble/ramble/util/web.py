# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import codecs
import errno
import multiprocessing.pool
import os
import os.path
import re
import shutil
import ssl
import sys
import traceback
from html.parser import HTMLParser
from typing import Any, Dict, List, Set, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

import llnl.util.lang
from llnl.util.filesystem import mkdirp, rename

import ramble
import ramble.config
from ramble.util.logger import logger

import spack.error
import spack.util.gcs as gcs_util
import spack.util.s3 as s3_util
import spack.util.url as url_util
from spack.util.compression import ALLOWED_ARCHIVE_TYPES
from spack.util.path import convert_to_posix_path

#: User-Agent used in Request objects
RAMBLE_USER_AGENT = f"Ramblebot/{ramble.ramble_version}"


# Also, HTMLParseError is deprecated and never raised.
class HTMLParseError(Exception):
    pass


class LinkParser(HTMLParser):
    """This parser just takes an HTML page and strips out the hrefs on the
    links.  Good enough for a really simple spider."""

    def __init__(self):
        HTMLParser.__init__(self)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr, val in attrs:
                if attr == "href":
                    self.links.append(val)


def uses_ssl(parsed_url):
    if parsed_url.scheme == "https":
        return True

    if parsed_url.scheme == "s3":
        endpoint_url = os.environ.get("S3_ENDPOINT_URL")
        if not endpoint_url:
            return True

        if url_util.parse(endpoint_url, scheme="https").scheme == "https":
            return True

    elif parsed_url.scheme == "gs":
        logger.debug("(uses_ssl) GCS Blob is https")
        return True

    return False


def read_from_url(url, accept_content_type=None):
    url = url_util.parse(url)

    verify_ssl = ramble.config.get("config:verify_ssl")

    # Timeout in seconds for web requests
    timeout = ramble.config.get("config:connect_timeout", 10)

    # Don't even bother with a context unless the URL scheme is one that uses
    # SSL certs.
    if uses_ssl(url):
        if verify_ssl:
            context = ssl.create_default_context()  # novm
        else:
            context = ssl._create_unverified_context()
    else:
        context = None

    url_scheme = url.scheme
    url = url_util.format(url)
    if sys.platform == "win32" and url_scheme == "file":
        url = convert_to_posix_path(url)
    req = Request(url, headers={"User-Agent": RAMBLE_USER_AGENT})

    content_type = None
    is_web_url = url_scheme in ("http", "https")
    if accept_content_type and is_web_url:
        # Make a HEAD request first to check the content type.  This lets
        # us ignore tarballs and gigantic files.
        # It would be nice to do this with the HTTP Accept header to avoid
        # one round-trip.  However, most servers seem to ignore the header
        # if you ask for a tarball with Accept: text/html.
        req.method = "HEAD"
        resp = _urlopen(req, timeout=timeout, context=context)

        content_type = get_header(resp.headers, "Content-type")

    # Do the real GET request when we know it's just HTML.
    req.method = "GET"

    try:
        response = _urlopen(req, timeout=timeout, context=context)
    except URLError as err:
        raise SpackWebError("Download failed") from err

    if accept_content_type and not is_web_url:
        content_type = get_header(response.headers, "Content-type")

    reject_content_type = accept_content_type and (
        content_type is None or not content_type.startswith(accept_content_type)
    )

    if reject_content_type:
        logger.debug(
            "ignoring page {}{}{}".format(
                url, " with content type " if content_type is not None else "", content_type or ""
            )
        )

        return None, None, None

    return response.geturl(), response.headers, response


def push_to_url(local_file_path, remote_path, keep_original=True, extra_args=None):
    if sys.platform == "win32":
        if remote_path[1] == ":":
            remote_path = "file://" + remote_path
    remote_url = url_util.parse(remote_path)
    remote_file_path = url_util.local_file_path(remote_url)
    logger.debug(f"Trying to backup file to: {remote_file_path}")
    if remote_file_path is not None:
        mkdirp(os.path.dirname(remote_file_path))
        if keep_original:
            shutil.copy(local_file_path, remote_file_path)
        else:
            try:
                rename(local_file_path, remote_file_path)
            except OSError as e:
                if e.errno == errno.EXDEV:
                    # NOTE(opadron): The above move failed because it crosses
                    # filesystem boundaries.  Copy the file (plus original
                    # metadata), and then delete the original.  This operation
                    # needs to be done in separate steps.
                    shutil.copy2(local_file_path, remote_file_path)
                    os.remove(local_file_path)
                else:
                    raise

    elif remote_url.scheme == "s3":
        if extra_args is None:
            extra_args = {}

        remote_path = remote_url.path
        while remote_path.startswith("/"):
            remote_path = remote_path[1:]

        s3 = s3_util.create_s3_session(
            remote_url, connection=s3_util.get_mirror_connection(remote_url)
        )
        s3.upload_file(local_file_path, remote_url.netloc, remote_path, ExtraArgs=extra_args)

        if not keep_original:
            os.remove(local_file_path)

    elif remote_url.scheme == "gs":
        gcs = gcs_util.GCSBlob(remote_url)
        gcs.upload_to_blob(local_file_path)
        if not keep_original:
            os.remove(local_file_path)

    else:
        raise NotImplementedError(f"Unrecognized URL scheme: {remote_url.scheme}")


def url_exists(url):
    url = url_util.parse(url)
    local_path = url_util.local_file_path(url)
    if local_path:
        return os.path.exists(local_path)

    if url.scheme == "s3":
        # Check for URL specific connection information
        s3 = s3_util.create_s3_session(url, connection=s3_util.get_mirror_connection(url))

        try:
            s3.get_object(Bucket=url.netloc, Key=url.path.lstrip("/"))
            return True
        except s3.ClientError as err:
            if err.response["Error"]["Code"] == "NoSuchKey":
                return False
            raise err

    elif url.scheme == "gs":
        gcs = gcs_util.GCSBlob(url)
        return gcs.exists()

    # otherwise, just try to "read" from the URL, and assume that *any*
    # non-throwing response contains the resource represented by the URL
    try:
        read_from_url(url)
        return True
    except (SpackWebError, URLError):
        return False


def _debug_print_delete_results(result):
    if "Deleted" in result:
        for d in result["Deleted"]:
            logger.debug(f'Deleted {d["Key"]}')
    if "Errors" in result:
        for e in result["Errors"]:
            logger.debug(f'Failed to delete {e["Key"]} ({e["Message"]})')


def remove_url(url, recursive=False):
    url = url_util.parse(url)

    local_path = url_util.local_file_path(url)
    if local_path:
        if recursive:
            shutil.rmtree(local_path)
        else:
            os.remove(local_path)
        return

    if url.scheme == "s3":
        # Try to find a mirror for potential connection information
        s3 = s3_util.create_s3_session(url, connection=s3_util.get_mirror_connection(url))
        bucket = url.netloc
        if recursive:
            # Because list_objects_v2 can only return up to 1000 items
            # at a time, we have to paginate to make sure we get it all
            prefix = url.path.strip("/")
            paginator = s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

            delete_request: Dict[str, List[Dict[str, Any]]] = {"Objects": []}
            for item in pages.search("Contents"):
                if not item:
                    continue

                delete_request["Objects"].append({"Key": item["Key"]})

                # Make sure we do not try to hit S3 with a list of more
                # than 1000 items
                if len(delete_request["Objects"]) >= 1000:
                    r = s3.delete_objects(Bucket=bucket, Delete=delete_request)
                    _debug_print_delete_results(r)
                    delete_request = {"Objects": []}

            # Delete any items that remain
            if len(delete_request["Objects"]):
                r = s3.delete_objects(Bucket=bucket, Delete=delete_request)
                _debug_print_delete_results(r)
        else:
            s3.delete_object(Bucket=bucket, Key=url.path.lstrip("/"))
        return

    elif url.scheme == "gs":
        if recursive:
            bucket = gcs_util.GCSBucket(url)
            bucket.destroy(recursive=recursive)
        else:
            blob = gcs_util.GCSBlob(url)
            blob.delete_blob()
        return

    # Don't even try for other URL schemes.


def _iter_s3_contents(contents, prefix):
    for entry in contents:
        key = entry["Key"]

        if not key.startswith("/"):
            key = "/" + key

        key = os.path.relpath(key, prefix)

        if key == ".":
            continue

        yield key


def _list_s3_objects(client, bucket, prefix, num_entries, start_after=None):
    list_args = {"Bucket": bucket, "Prefix": prefix[1:], "MaxKeys": num_entries}

    if start_after is not None:
        list_args["StartAfter"] = start_after

    result = client.list_objects_v2(**list_args)

    last_key = None
    if result["IsTruncated"]:
        last_key = result["Contents"][-1]["Key"]

    iter = _iter_s3_contents(result["Contents"], prefix)

    return iter, last_key


def _iter_s3_prefix(client, url, num_entries=1024):
    key = None
    bucket = url.netloc
    prefix = re.sub(r"^/*", "/", url.path)

    while True:
        contents, key = _list_s3_objects(client, bucket, prefix, num_entries, start_after=key)

        yield from contents

        if not key:
            break


def _iter_local_prefix(path):
    for root, _, files in os.walk(path):
        for f in files:
            yield os.path.relpath(os.path.join(root, f), path)


def list_url(url, recursive=False):
    url = url_util.parse(url)

    local_path = url_util.local_file_path(url)
    if local_path:
        if recursive:
            return list(_iter_local_prefix(local_path))
        return [
            subpath
            for subpath in os.listdir(local_path)
            if os.path.isfile(os.path.join(local_path, subpath))
        ]

    if url.scheme == "s3":
        s3 = s3_util.create_s3_session(url)
        if recursive:
            return list(_iter_s3_prefix(s3, url))

        return list({key.split("/", 1)[0] for key in _iter_s3_prefix(s3, url)})

    elif url.scheme == "gs":
        gcs = gcs_util.GCSBucket(url)
        return gcs.get_all_blobs(recursive=recursive)


def spider(root_urls, depth=0, concurrency=32):
    """Get web pages from root URLs.

    If depth is specified (e.g., depth=2), then this will also follow
    up to <depth> levels of links from each root.

    Args:
        root_urls (str | list): root urls used as a starting point
            for spidering
        depth (int): level of recursion into links
        concurrency (int): number of simultaneous requests that can be sent

    Returns:
        A dict of pages visited (URL) mapped to their full text and the
        set of visited links.
    """
    # Cache of visited links, meant to be captured by the closure below
    _visited = set()

    def _spider(url, collect_nested):
        """Fetches URL and any pages it links to.

        Prints out a warning only if the root can't be fetched; it ignores
        errors with pages that the root links to.

        Args:
            url (str): url being fetched and searched for links
            collect_nested (bool): whether we want to collect arguments
                for nested spidering on the links found in this url

        Returns:
            A tuple of:
            - pages: dict of pages visited (URL) mapped to their full text.
            - links: set of links encountered while visiting the pages.
            - spider_args: argument for subsequent call to spider
        """
        pages: Dict[str, str] = {}  # dict from page URL -> text content.
        links: Set[str] = set()  # set of all links seen on visited pages.
        subcalls: List[Tuple] = []

        try:
            response_url, _, response = read_from_url(url, "text/html")
            if not response_url or not response:
                return pages, links, subcalls

            page = codecs.getreader("utf-8")(response).read()
            pages[response_url] = page

            # Parse out the links in the page
            link_parser = LinkParser()
            link_parser.feed(page)

            while link_parser.links:
                raw_link = link_parser.links.pop()
                abs_link = url_util.join(response_url, raw_link.strip(), resolve_href=True)
                links.add(abs_link)

                # Skip stuff that looks like an archive
                if any(raw_link.endswith(s) for s in ALLOWED_ARCHIVE_TYPES):
                    continue

                # Skip already-visited links
                if abs_link in _visited:
                    continue

                # If we're not at max depth, follow links.
                if collect_nested:
                    subcalls.append((abs_link,))
                    _visited.add(abs_link)

        except URLError as e:
            logger.debug(str(e))

            if hasattr(e, "reason") and isinstance(e.reason, ssl.SSLError):
                logger.warn(
                    "Ramble was unable to fetch url list due to a "
                    "certificate verification problem. You can try "
                    "running ramble -k, which will not check SSL "
                    "certificates. Use this at your own risk."
                )

        except HTMLParseError as e:
            # This error indicates that Python's HTML parser sucks.
            msg = "Got an error parsing HTML."
            logger.warn(msg, url, "HTMLParseError: " + str(e))

        except Exception as e:
            # Other types of errors are completely ignored,
            # except in debug mode
            logger.debug(f"Error in _spider: {type(e)}:{str(e)}", traceback.format_exc())

        finally:
            logger.debug(f"SPIDER: [url={url}]")

        return pages, links, subcalls

    if isinstance(root_urls, str):
        root_urls = [root_urls]

    # Clear the local cache of visited pages before starting the search
    _visited.clear()

    current_depth = 0
    pages, links, spider_args = {}, set(), []

    collect = current_depth < depth
    for root in root_urls:
        root = url_util.parse(root)
        spider_args.append((root, collect))

    tp = multiprocessing.pool.ThreadPool(processes=concurrency)
    try:
        while current_depth <= depth:
            logger.debug(
                "SPIDER: [depth={}, max_depth={}, urls={}]".format(
                    current_depth, depth, len(spider_args)
                )
            )
            results = tp.map(llnl.util.lang.star(_spider), spider_args)
            spider_args = []
            collect = current_depth < depth
            for sub_pages, sub_links, sub_spider_args in results:
                sub_spider_args = [x + (collect,) for x in sub_spider_args]
                pages.update(sub_pages)
                links.update(sub_links)
                spider_args.extend(sub_spider_args)

            current_depth += 1
    finally:
        tp.terminate()
        tp.join()

    return pages, links


def _urlopen(req, *args, **kwargs):
    """Wrapper for compatibility with old versions of Python."""
    url = req
    try:
        url = url.get_full_url()
    except AttributeError:
        pass

    opener = urlopen
    if url_util.parse(url).scheme == "s3":
        import spack.s3_handler

        opener = spack.s3_handler.open  # type: ignore[assignment]
    elif url_util.parse(url).scheme == "gs":
        import spack.gcs_handler

        opener = spack.gcs_handler.gcs_open  # type: ignore[assignment]

    try:
        return opener(req, *args, **kwargs)
    except TypeError as err:
        # If the above fails because of 'context', call without 'context'.
        if "context" in kwargs and "context" in str(err):
            del kwargs["context"]
        return opener(req, *args, **kwargs)


def get_header(headers, header_name):
    """Looks up a dict of headers for the given header value.

    Looks up a dict of headers, [headers], for a header value given by
    [header_name].  Returns headers[header_name] if header_name is in headers.
    Otherwise, the first fuzzy match is returned, if any.

    This fuzzy matching is performed by discarding word separators and
    capitalization, so that for example, "Content-length", "content_length",
    "conTENtLength", etc., all match.  In the case of multiple fuzzy-matches,
    the returned value is the "first" such match given the underlying mapping's
    ordering, or unspecified if no such ordering is defined.

    If header_name is not in headers, and no such fuzzy match exists, then a
    KeyError is raised.
    """

    def unfuzz(header):
        return re.sub(r"[ _-]", "", header).lower()

    try:
        return headers[header_name]
    except KeyError:
        unfuzzed_header_name = unfuzz(header_name)
        for header, value in headers.items():
            if unfuzz(header) == unfuzzed_header_name:
                return value
        raise


class SpackWebError(spack.error.SpackError):
    """Superclass for Spack web spidering errors."""
