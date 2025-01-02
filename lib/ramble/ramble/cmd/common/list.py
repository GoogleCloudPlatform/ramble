# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import argparse
import fnmatch
import os
import re
import sys
import math

from llnl.util.tty.colify import colify

import ramble.repository
import ramble.cmd.common.arguments as arguments
from ramble.util.logger import logger

from html import escape  # novm


formatters = {}


def formatter(func):
    """Decorator used to register formatters"""
    formatters[func.__name__] = func
    return func


def filter_by_name(objs, args, object_type):
    """
    Filters the sequence of objects according to user prescriptions

    Args:
        objs: sequence of objects
        args: parsed command line arguments

    Returns:
        filtered and sorted list of objects
    """
    if args.filter:
        res = []
        for f in args.filter:
            if "*" not in f and "?" not in f:
                r = fnmatch.translate("*" + f + "*")
            else:
                r = fnmatch.translate(f)

            rc = re.compile(r, flags=re.IGNORECASE)
            res.append(rc)

        if args.search_description:

            def match(p, f):
                if f.match(p):
                    return True

                obj = ramble.repository.get(p, object_type=object_type)
                if obj.__doc__:
                    return f.match(obj.__doc__)
                return False

        else:

            def match(p, f):
                return f.match(p)

        objs = [obj for obj in objs if any(match(obj, f) for f in res)]

    return sorted(objs, key=lambda s: s.lower())


@formatter
def name_only(objs, out, object_type):
    obj_def = ramble.repository.type_definitions[object_type]
    indent = 0
    if out.isatty():
        logger.msg(f'{len(objs)} {obj_def["dir_name"]}')
    colify(objs, indent=indent, output=out)


def github_url(objs, object_type):
    """Link to an object file on github."""
    obj_def = ramble.repository.type_definitions[object_type]
    url = (
        "https://github.com/ramble/ramble/blob/develop/var/ramble/repos/builtina/"
        + f'{obj_def["dir_name"]}/'
        + "{0}"
        + f'/{obj_def["file_name"]}'
    )
    return url.format(objs.name)


def rows_for_ncols(elts, ncols):
    """Print out rows in a table with ncols of elts laid out vertically."""
    clen = int(math.ceil(len(elts) / ncols))
    for r in range(clen):
        row = []
        for c in range(ncols):
            i = c * clen + r
            row.append(elts[i] if i < len(elts) else None)
        yield row


@formatter
def version_json(obj_names, out, object_type):
    """Print all objects with their latest versions."""
    objs = [ramble.repository.get(name, object_type=object_type) for name in obj_names]

    out.write("[\n")

    # output name and latest version for each object
    obj_latest = ",\n".join(
        [
            '  {{"name": "{0}"\n'
            "}}".format(
                obj.name,
            )
            for obj in objs
        ]
    )
    out.write(obj_latest)
    # important: no trailing comma in JSON arrays
    out.write("\n]\n")


@formatter
def html(obj_names, out, object_type):
    """Print out information on all objects in Sphinx HTML.

    This is intended to be inlined directly into Sphinx documentation.
    We write HTML instead of RST for speed; generating RST from *all*
    objects causes the Sphinx build to take forever. Including this as
    raw HTML is much faster.
    """

    obj_def = ramble.repository.type_definitions[object_type]

    # Read in all objects
    objs = [ramble.repository.get(name, object_type=object_type) for name in obj_names]

    # Start at 2 because the title of the page from Sphinx is id1.
    span_id = 2

    # HTML header with an increasing id span
    def head(n, span_id, title, anchor=None):
        if anchor is None:
            anchor = title
        out.write(
            (
                '<span id="id%d"></span>'
                '<h1>%s<a class="headerlink" href="#%s" '
                'title="Permalink to this headline">&para;</a>'
                "</h1>\n"
            )
            % (span_id, title, anchor)
        )

    # Start with the number of objects, skipping the title and intro
    # blurb, which we maintain in the RST file.
    out.write("<p>\n")
    out.write(f'Ramble currently has {len(objs)} mainline {obj_def["dir_name"]}:\n')
    out.write("</p>\n")

    # Table of links to all objects
    out.write('<table border="1" class="docutils">\n')
    out.write('<tbody valign="top">\n')
    for i, row in enumerate(rows_for_ncols(obj_names, 3)):
        out.write('<tr class="row-odd">\n' if i % 2 == 0 else '<tr class="row-even">\n')
        for name in row:
            out.write("<td>\n")
            out.write(f'<a class="reference internal" href="#{name}">{name}</a></td>\n')
            out.write("</td>\n")
        out.write("</tr>\n")
    out.write("</tbody>\n")
    out.write("</table>\n")
    out.write('<hr class="docutils"/>\n')

    # Output some text for each objects.
    for obj in objs:
        out.write('<div class="section" id="%s">\n' % obj.name)
        head(2, span_id, obj.name)
        span_id += 1

        out.write('<dl class="docutils">\n')

        # out.write('<dt>Homepage:</dt>\n')
        # out.write('<dd><ul class="first last simple">\n')
        # out.write(('<li>'
        #            '<a class="reference external" href="%s">%s</a>'
        #            '</li>\n') % (obj.homepage, escape(obj.homepage, True)))
        # out.write('</ul></dd>\n')

        out.write(f'<dt>Ramble {obj_def["dir_name"]}:</dt>\n')
        out.write('<dd><ul class="first last simple">\n')
        out.write(
            "<li>"
            '<a class="reference external" '
            f'href="{github_url(obj, object_type)}">'
            f'{obj.name}/{obj_def["file_name"]}</a>'  # noqa: E501
            "</li>\n"
        )
        out.write("</ul></dd>\n")

        # if obj.versions:
        #     out.write('<dt>Versions:</dt>\n')
        #     out.write('<dd>\n')
        #     out.write(', '.join(
        #         str(v) for v in reversed(sorted(obj.versions))))
        #     out.write('\n')
        #     out.write('</dd>\n')

        out.write("<dt>Description:</dt>\n")
        out.write("<dd>\n")
        out.write(escape(obj.format_doc(indent=2), True))
        out.write("\n")
        out.write("</dd>\n")
        out.write("</dl>\n")

        out.write('<hr class="docutils"/>\n')
        out.write("</div>\n")


def setup_list_parser(subparser):
    subparser.add_argument(
        "filter",
        nargs=argparse.REMAINDER,
        help="optional case-insensitive glob patterns to filter results",
    )
    subparser.add_argument(
        "-d",
        "--search-description",
        action="store_true",
        default=False,
        help="filtering will also search the description for a match",
    )
    subparser.add_argument(
        "--format",
        default="name_only",
        choices=formatters,
        help="format to be used to print the output [default: name_only]",
    )
    subparser.add_argument(
        "--update",
        metavar="FILE",
        default=None,
        action="store",
        help="write output to the specified file, if any object is newer",
    )

    arguments.add_common_arguments(subparser, ["tags", "obj_type"])


def perform_list(args):
    # retrieve the formatter to use from args
    formatter = formatters[args.format]

    object_type = ramble.repository.ObjectTypes[args.type]

    # Retrieve the names of all the objects
    objs = set(ramble.repository.all_object_names(object_type))
    # Filter the set appropriately
    sorted_objects = filter_by_name(objs, args, object_type)

    # Filter by tags
    if args.tags:
        objects_with_tags = set(ramble.repository.paths[object_type].objects_with_tags(*args.tags))
        sorted_objects = set(sorted_objects) & objects_with_tags
        sorted_objects = sorted(sorted_objects)

    if args.update:
        # change output stream if user asked for update
        if os.path.exists(args.update):
            if os.path.getmtime(args.update) > ramble.repository.paths[object_type].last_mtime():
                logger.msg(f"File is up to date: {args.update}")
                return

        logger.msg(f"Updating file: {args.update}")
        with open(args.update, "w") as f:
            formatter(sorted_objects, f, object_type)

    else:
        # Print to stdout
        formatter(sorted_objects, sys.stdout, object_type)
