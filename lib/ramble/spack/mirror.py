# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

"""
This file contains code for creating spack mirror directories.  A
mirror is an organized hierarchy containing specially named archive
files.  This enabled spack to know where to find files in a mirror if
the main server for a particular package is down.  Or, if the computer
where spack is run is not connected to the internet, it allows spack
to download packages directly from a mirror (e.g., on an intranet).
"""
import collections
import operator
import os
import os.path
import sys
import traceback

import ruamel.yaml.error as yaml_error
import six

import llnl.util.tty as tty
from llnl.util.compat import Mapping
from llnl.util.filesystem import mkdirp

import spack.config
import spack.error
import spack.fetch_strategy as fs
import spack.spec
import spack.url as url
import spack.util.spack_json as sjson
import spack.util.spack_yaml as syaml
import spack.util.url as url_util
from spack.util.spack_yaml import syaml_dict
from spack.version import VersionList


def _is_string(url):
    return isinstance(url, six.string_types)


def _display_mirror_entry(size, name, url, type_=None):
    if type_:
        type_ = "".join((" (", type_, ")"))
    else:
        type_ = ""

    print("%-*s%s%s" % (size + 4, name, url, type_))


class Mirror(object):
    """Represents a named location for storing source tarballs and binary
    packages.

    Mirrors have a fetch_url that indicate where and how artifacts are fetched
    from them, and a push_url that indicate where and how artifacts are pushed
    to them.  These two URLs are usually the same.
    """

    def __init__(self, fetch_url, push_url=None,
                 name=None):
        self._fetch_url = fetch_url
        self._push_url = push_url
        self._name = name

    def __eq__(self, other):
        return (self._fetch_url == other._fetch_url and
                self._push_url == other._push_url)

    def to_json(self, stream=None):
        return sjson.dump(self.to_dict(), stream)

    def to_yaml(self, stream=None):
        return syaml.dump(self.to_dict(), stream)

    @staticmethod
    def from_yaml(stream, name=None):
        try:
            data = syaml.load(stream)
            return Mirror.from_dict(data, name)
        except yaml_error.MarkedYAMLError as e:
            raise six.raise_from(
                syaml.SpackYAMLError("error parsing YAML mirror:", str(e)),
                e,
            )

    @staticmethod
    def from_json(stream, name=None):
        try:
            d = sjson.load(stream)
            return Mirror.from_dict(d, name)
        except Exception as e:
            raise six.raise_from(
                sjson.SpackJSONError("error parsing JSON mirror:", str(e)),
                e,
            )

    def to_dict(self):
        if self._push_url is None:
            return syaml_dict([
                ('fetch', self._fetch_url),
                ('push', self._fetch_url)])
        else:
            return syaml_dict([
                ('fetch', self._fetch_url),
                ('push', self._push_url)])

    @staticmethod
    def from_dict(d, name=None):
        if isinstance(d, six.string_types):
            return Mirror(d, name=name)
        else:
            return Mirror(d['fetch'], d['push'], name=name)

    def display(self, max_len=0):
        if self._push_url is None:
            _display_mirror_entry(max_len, self._name, self.fetch_url)
        else:
            _display_mirror_entry(
                max_len, self._name, self.fetch_url, "fetch")
            _display_mirror_entry(
                max_len, self._name, self.push_url, "push")

    def __str__(self):
        name = self._name
        if name is None:
            name = ''
        else:
            name = ' "%s"' % name

        if self._push_url is None:
            return "[Mirror%s (%s)]" % (name, self._fetch_url)

        return "[Mirror%s (fetch: %s, push: %s)]" % (
            name, self._fetch_url, self._push_url)

    def __repr__(self):
        return ''.join((
            'Mirror(',
            ', '.join(
                '%s=%s' % (k, repr(v))
                for k, v in (
                    ('fetch_url', self._fetch_url),
                    ('push_url', self._push_url),
                    ('name', self._name))
                if k == 'fetch_url' or v),
            ')'
        ))

    @property
    def name(self):
        return self._name or "<unnamed>"

    def get_profile(self, url_type):
        if isinstance(self._fetch_url, dict):
            if url_type == "push":
                return self._push_url.get('profile', None)
            return self._fetch_url.get('profile', None)
        else:
            return None

    def set_profile(self, url_type, profile):
        if url_type == "push":
            self._push_url["profile"] = profile
        else:
            self._fetch_url["profile"] = profile

    def get_access_pair(self, url_type):
        if isinstance(self._fetch_url, dict):
            if url_type == "push":
                return self._push_url.get('access_pair', None)
            return self._fetch_url.get('access_pair', None)
        else:
            return None

    def set_access_pair(self, url_type, connection_tuple):
        if url_type == "push":
            self._push_url["access_pair"] = connection_tuple
        else:
            self._fetch_url["access_pair"] = connection_tuple

    def get_endpoint_url(self, url_type):
        if isinstance(self._fetch_url, dict):
            if url_type == "push":
                return self._push_url.get('endpoint_url', None)
            return self._fetch_url.get('endpoint_url', None)
        else:
            return None

    def set_endpoint_url(self, url_type, url):
        if url_type == "push":
            self._push_url["endpoint_url"] = url
        else:
            self._fetch_url["endpoint_url"] = url

    def get_access_token(self, url_type):
        if isinstance(self._fetch_url, dict):
            if url_type == "push":
                return self._push_url.get('access_token', None)
            return self._fetch_url.get('access_token', None)
        else:
            return None

    def set_access_token(self, url_type, connection_token):
        if url_type == "push":
            self._push_url["access_token"] = connection_token
        else:
            self._fetch_url["access_token"] = connection_token

    @property
    def fetch_url(self):
        return self._fetch_url if _is_string(self._fetch_url) \
            else self._fetch_url["url"]

    @fetch_url.setter
    def fetch_url(self, url):
        self._fetch_url["url"] = url
        self._normalize()

    @property
    def push_url(self):
        if self._push_url is None:
            return self._fetch_url if _is_string(self._fetch_url) \
                else self._fetch_url["url"]
        return self._push_url if _is_string(self._push_url) \
            else self._push_url["url"]

    @push_url.setter
    def push_url(self, url):
        self._push_url["url"] = url
        self._normalize()

    def _normalize(self):
        if self._push_url is not None and self._push_url == self._fetch_url:
            self._push_url = None


class MirrorCollection(Mapping):
    """A mapping of mirror names to mirrors."""

    def __init__(self, mirrors=None, scope=None):
        self._mirrors = collections.OrderedDict(
            (name, Mirror.from_dict(mirror, name))
            for name, mirror in (
                mirrors.items() if mirrors is not None else
                spack.config.get('mirrors', scope=scope).items()))

    def __eq__(self, other):
        return self._mirrors == other._mirrors

    def to_json(self, stream=None):
        return sjson.dump(self.to_dict(True), stream)

    def to_yaml(self, stream=None):
        return syaml.dump(self.to_dict(True), stream)

    # TODO: this isn't called anywhere
    @staticmethod
    def from_yaml(stream, name=None):
        try:
            data = syaml.load(stream)
            return MirrorCollection(data)
        except yaml_error.MarkedYAMLError as e:
            raise six.raise_from(
                syaml.SpackYAMLError("error parsing YAML mirror collection:", str(e)),
                e,
            )

    @staticmethod
    def from_json(stream, name=None):
        try:
            d = sjson.load(stream)
            return MirrorCollection(d)
        except Exception as e:
            raise six.raise_from(
                sjson.SpackJSONError("error parsing JSON mirror collection:", str(e)),
                e,
            )

    def to_dict(self, recursive=False):
        return syaml_dict(sorted(
            (
                (k, (v.to_dict() if recursive else v))
                for (k, v) in self._mirrors.items()
            ), key=operator.itemgetter(0)
        ))

    @staticmethod
    def from_dict(d):
        return MirrorCollection(d)

    def __getitem__(self, item):
        return self._mirrors[item]

    def display(self):
        max_len = max(len(mirror.name) for mirror in self._mirrors.values())
        for mirror in self._mirrors.values():
            mirror.display(max_len)

    def lookup(self, name_or_url):
        """Looks up and returns a Mirror.

        If this MirrorCollection contains a named Mirror under the name
        [name_or_url], then that mirror is returned.  Otherwise, [name_or_url]
        is assumed to be a mirror URL, and an anonymous mirror with the given
        URL is returned.
        """
        result = self.get(name_or_url)

        if result is None:
            result = Mirror(fetch_url=name_or_url)

        return result

    def __iter__(self):
        return iter(self._mirrors)

    def __len__(self):
        return len(self._mirrors)


def _determine_extension(fetcher):
    if isinstance(fetcher, fs.URLFetchStrategy):
        if fetcher.expand_archive:
            # If we fetch with a URLFetchStrategy, use URL's archive type
            ext = url.determine_url_file_extension(fetcher.url)

            if ext:
                # Remove any leading dots
                ext = ext.lstrip('.')
            else:
                msg = """\
Unable to parse extension from {0}.

If this URL is for a tarball but does not include the file extension
in the name, you can explicitly declare it with the following syntax:

    version('1.2.3', 'hash', extension='tar.gz')

If this URL is for a download like a .jar or .whl that does not need
to be expanded, or an uncompressed installation script, you can tell
Spack not to expand it with the following syntax:

    version('1.2.3', 'hash', expand=False)
"""
                raise MirrorError(msg.format(fetcher.url))
        else:
            # If the archive shouldn't be expanded, don't check extension.
            ext = None
    else:
        # Otherwise we'll make a .tar.gz ourselves
        ext = 'tar.gz'

    return ext


class MirrorReference(object):
    """A ``MirrorReference`` stores the relative paths where you can store a
    package/resource in a mirror directory.

    The appropriate storage location is given by ``storage_path``. The
    ``cosmetic_path`` property provides a reference that a human could generate
    themselves based on reading the details of the package.

    A user can iterate over a ``MirrorReference`` object to get all the
    possible names that might be used to refer to the resource in a mirror;
    this includes names generated by previous naming schemes that are no-longer
    reported by ``storage_path`` or ``cosmetic_path``.
    """
    def __init__(self, cosmetic_path, global_path=None):
        self.global_path = global_path
        self.cosmetic_path = cosmetic_path

    @property
    def storage_path(self):
        if self.global_path:
            return self.global_path
        else:
            return self.cosmetic_path

    def __iter__(self):
        if self.global_path:
            yield self.global_path
        yield self.cosmetic_path


def mirror_archive_paths(fetcher, per_package_ref, spec=None):
    """Returns a ``MirrorReference`` object which keeps track of the relative
    storage path of the resource associated with the specified ``fetcher``."""
    ext = None
    if spec:
        versions = spec.package.versions.get(spec.package.version, {})
        ext = versions.get('extension', None)
    # If the spec does not explicitly specify an extension (the default case),
    # then try to determine it automatically. An extension can only be
    # specified for the primary source of the package (e.g. the source code
    # identified in the 'version' declaration). Resources/patches don't have
    # an option to specify an extension, so it must be inferred for those.
    ext = ext or _determine_extension(fetcher)

    if ext:
        per_package_ref += ".%s" % ext

    global_ref = fetcher.mirror_id()
    if global_ref:
        global_ref = os.path.join('_source-cache', global_ref)
    if global_ref and ext:
        global_ref += ".%s" % ext

    return MirrorReference(per_package_ref, global_ref)


def get_all_versions(specs):
    """Given a set of initial specs, return a new set of specs that includes
    each version of each package in the original set.

    Note that if any spec in the original set specifies properties other than
    version, this information will be omitted in the new set; for example; the
    new set of specs will not include variant settings.
    """

    version_specs = []
    for spec in specs:
        pkg = spec.package

        # Skip any package that has no known versions.
        if not pkg.versions:
            tty.msg("No safe (checksummed) versions for package %s" % pkg.name)
            continue

        for version in pkg.versions:
            version_spec = spack.spec.Spec(pkg.name)
            version_spec.versions = VersionList([version])
            version_specs.append(version_spec)

    return version_specs


def get_matching_versions(specs, num_versions=1):
    """Get a spec for EACH known version matching any spec in the list.
    For concrete specs, this retrieves the concrete version and, if more
    than one version per spec is requested, retrieves the latest versions
    of the package.
    """
    matching = []
    for spec in specs:
        pkg = spec.package

        # Skip any package that has no known versions.
        if not pkg.versions:
            tty.msg("No safe (checksummed) versions for package %s" % pkg.name)
            continue

        pkg_versions = num_versions

        version_order = list(reversed(sorted(pkg.versions)))
        matching_spec = []
        if spec.concrete:
            matching_spec.append(spec)
            pkg_versions -= 1
            if spec.version in version_order:
                version_order.remove(spec.version)

        for v in version_order:
            # Generate no more than num_versions versions for each spec.
            if pkg_versions < 1:
                break

            # Generate only versions that satisfy the spec.
            if spec.concrete or v.satisfies(spec.versions):
                s = spack.spec.Spec(pkg.name)
                s.versions = VersionList([v])
                s.variants = spec.variants.copy()
                # This is needed to avoid hanging references during the
                # concretization phase
                s.variants.spec = s
                matching_spec.append(s)
                pkg_versions -= 1

        if not matching_spec:
            tty.warn("No known version matches spec: %s" % spec)
        matching.extend(matching_spec)

    return matching


def create(path, specs, skip_unstable_versions=False):
    """Create a directory to be used as a spack mirror, and fill it with
    package archives.

    Arguments:
        path: Path to create a mirror directory hierarchy in.
        specs: Any package versions matching these specs will be added \
            to the mirror.
        skip_unstable_versions: if true, this skips adding resources when
            they do not have a stable archive checksum (as determined by
            ``fetch_strategy.stable_target``)

    Return Value:
        Returns a tuple of lists: (present, mirrored, error)

        * present:  Package specs that were already present.
        * mirrored: Package specs that were successfully mirrored.
        * error:    Package specs that failed to mirror due to some error.

    This routine iterates through all known package versions, and
    it creates specs for those versions.  If the version satisfies any spec
    in the specs list, it is downloaded and added to the mirror.
    """
    parsed = url_util.parse(path)
    mirror_root = url_util.local_file_path(parsed)
    if not mirror_root:
        raise spack.error.SpackError(
            'MirrorCaches only work with file:// URLs')

    # automatically spec-ify anything in the specs array.
    specs = [
        s if isinstance(s, spack.spec.Spec) else spack.spec.Spec(s)
        for s in specs]

    # Get the absolute path of the root before we start jumping around.
    if not os.path.isdir(mirror_root):
        try:
            mkdirp(mirror_root)
        except OSError as e:
            raise MirrorError(
                "Cannot create directory '%s':" % mirror_root, str(e))

    mirror_cache = spack.caches.MirrorCache(
        mirror_root, skip_unstable_versions=skip_unstable_versions)
    mirror_stats = MirrorStats()

    # Iterate through packages and download all safe tarballs for each
    for spec in specs:
        mirror_stats.next_spec(spec)
        _add_single_spec(spec, mirror_cache, mirror_stats)

    return mirror_stats.stats()


def add(name, url, scope, args={}):
    """Add a named mirror in the given scope"""
    mirrors = spack.config.get('mirrors', scope=scope)
    if not mirrors:
        mirrors = syaml_dict()

    if name in mirrors:
        tty.die("Mirror with name %s already exists." % name)

    items = [(n, u) for n, u in mirrors.items()]
    mirror_data = url
    key_values = ["s3_access_key_id", "s3_access_token", "s3_profile"]
    # On creation, assume connection data is set for both
    if any(value for value in key_values if value in args):
        url_dict = {"url": url,
                    "access_pair": (args.s3_access_key_id, args.s3_access_key_secret),
                    "access_token": args.s3_access_token,
                    "profile": args.s3_profile,
                    "endpoint_url": args.s3_endpoint_url}
        mirror_data = {"fetch": url_dict, "push": url_dict}

    items.insert(0, (name, mirror_data))
    mirrors = syaml_dict(items)
    spack.config.set('mirrors', mirrors, scope=scope)


def remove(name, scope):
    """Remove the named mirror in the given scope"""
    mirrors = spack.config.get('mirrors', scope=scope)
    if not mirrors:
        mirrors = syaml_dict()

    if name not in mirrors:
        tty.die("No mirror with name %s" % name)

    old_value = mirrors.pop(name)
    spack.config.set('mirrors', mirrors, scope=scope)

    debug_msg_url = "url %s"
    debug_msg = ["Removed mirror %s with"]
    values = [name]

    try:
        fetch_value = old_value['fetch']
        push_value = old_value['push']

        debug_msg.extend(("fetch", debug_msg_url, "and push", debug_msg_url))
        values.extend((fetch_value, push_value))
    except TypeError:
        debug_msg.append(debug_msg_url)
        values.append(old_value)

    tty.debug(" ".join(debug_msg) % tuple(values))
    tty.msg("Removed mirror %s." % name)


class MirrorStats(object):
    def __init__(self):
        self.present = {}
        self.new = {}
        self.errors = set()

        self.current_spec = None
        self.added_resources = set()
        self.existing_resources = set()

    def next_spec(self, spec):
        self._tally_current_spec()
        self.current_spec = spec

    def _tally_current_spec(self):
        if self.current_spec:
            if self.added_resources:
                self.new[self.current_spec] = len(self.added_resources)
            if self.existing_resources:
                self.present[self.current_spec] = len(self.existing_resources)
            self.added_resources = set()
            self.existing_resources = set()
        self.current_spec = None

    def stats(self):
        self._tally_current_spec()
        return list(self.present), list(self.new), list(self.errors)

    def already_existed(self, resource):
        # If an error occurred after caching a subset of a spec's
        # resources, a secondary attempt may consider them already added
        if resource not in self.added_resources:
            self.existing_resources.add(resource)

    def added(self, resource):
        self.added_resources.add(resource)

    def error(self):
        self.errors.add(self.current_spec)


def _add_single_spec(spec, mirror, mirror_stats):
    tty.msg("Adding package {pkg} to mirror".format(
        pkg=spec.format("{name}{@version}")
    ))
    num_retries = 3
    while num_retries > 0:
        try:
            with spec.package.stage as pkg_stage:
                pkg_stage.cache_mirror(mirror, mirror_stats)
                for patch in spec.package.all_patches():
                    if patch.stage:
                        patch.stage.cache_mirror(mirror, mirror_stats)
                    patch.clean()
            exception = None
            break
        except Exception as e:
            exc_tuple = sys.exc_info()
            exception = e
        num_retries -= 1

    if exception:
        if spack.config.get('config:debug'):
            traceback.print_exception(file=sys.stderr, *exc_tuple)
        else:
            tty.warn(
                "Error while fetching %s" % spec.cformat('{name}{@version}'),
                getattr(exception, 'message', exception))
        mirror_stats.error()


def push_url_from_directory(output_directory):
    """Given a directory in the local filesystem, return the URL on
    which to push binary packages.
    """
    scheme = url_util.parse(output_directory, scheme='<missing>').scheme
    if scheme != '<missing>':
        raise ValueError('expected a local path, but got a URL instead')
    mirror_url = 'file://' + output_directory
    mirror = spack.mirror.MirrorCollection().lookup(mirror_url)
    return url_util.format(mirror.push_url)


def push_url_from_mirror_name(mirror_name):
    """Given a mirror name, return the URL on which to push binary packages."""
    mirror = spack.mirror.MirrorCollection().lookup(mirror_name)
    if mirror.name == "<unnamed>":
        raise ValueError('no mirror named "{0}"'.format(mirror_name))
    return url_util.format(mirror.push_url)


def push_url_from_mirror_url(mirror_url):
    """Given a mirror URL, return the URL on which to push binary packages."""
    scheme = url_util.parse(mirror_url, scheme='<missing>').scheme
    if scheme == '<missing>':
        raise ValueError('"{0}" is not a valid URL'.format(mirror_url))
    mirror = spack.mirror.MirrorCollection().lookup(mirror_url)
    return url_util.format(mirror.push_url)


class MirrorError(spack.error.SpackError):
    """Superclass of all mirror-creation related errors."""

    def __init__(self, msg, long_msg=None):
        super(MirrorError, self).__init__(msg, long_msg)
