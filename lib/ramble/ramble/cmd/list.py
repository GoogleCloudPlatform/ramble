# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from __future__ import print_function
from __future__ import division

import argparse
import fnmatch
import os
import re
import sys
import math

import llnl.util.tty as tty
from llnl.util.tty.colify import colify

import ramble.repository
import ramble.cmd.common.arguments as arguments

if sys.version_info > (3, 1):
    from html import escape  # novm
else:
    from cgi import escape

description = "list and search available applications"
section = "basic"
level = "short"


formatters = {}


def formatter(func):
    """Decorator used to register formatters"""
    formatters[func.__name__] = func
    return func


def setup_parser(subparser):
    subparser.add_argument(
        'filter', nargs=argparse.REMAINDER,
        help='optional case-insensitive glob patterns to filter results')
    subparser.add_argument(
        '-d', '--search-description', action='store_true', default=False,
        help='filtering will also search the description for a match')
    subparser.add_argument(
        '--format', default='name_only', choices=formatters,
        help='format to be used to print the output [default: name_only]')
    subparser.add_argument(
        '--update', metavar='FILE', default=None, action='store',
        help='write output to the specified file, if any application is newer')

    arguments.add_common_arguments(subparser, ['tags'])


def filter_by_name(apps, args):
    """
    Filters the sequence of applications according to user prescriptions

    Args:
        apps: sequence of applications
        args: parsed command line arguments

    Returns:
        filtered and sorted list of applications
    """
    if args.filter:
        res = []
        for f in args.filter:
            if '*' not in f and '?' not in f:
                r = fnmatch.translate('*' + f + '*')
            else:
                r = fnmatch.translate(f)

            rc = re.compile(r, flags=re.IGNORECASE)
            res.append(rc)

        if args.search_description:
            def match(p, f):
                if f.match(p):
                    return True

                app = ramble.repository.get(p)
                if app.__doc__:
                    return f.match(app.__doc__)
                return False
        else:
            def match(p, f):
                return f.match(p)
        apps = [app for app in apps if any(match(app, f) for f in res)]

    return sorted(apps, key=lambda s: s.lower())


@formatter
def name_only(apps, out):
    indent = 0
    if out.isatty():
        tty.msg("%d applications." % len(apps))
    colify(apps, indent=indent, output=out)


def github_url(apps):
    """Link to an application file on github."""
    url = 'https://github.com/ramble/ramble/blob/develop/var/ramble/repos/builtin/appliactions/{0}/application.py'
    return url.format(apps.name)


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
def version_json(app_names, out):
    """Print all applications with their latest versions."""
    apps = [ramble.repository.get(name) for name in app_names]

    out.write('[\n')

    # output name and latest version for each application
    app_latest = ",\n".join([
        '  {{"name": "{0}"\n'
        '}}'.format(
            app.name,
        ) for app in apps
    ])
    out.write(app_latest)
    # important: no trailing comma in JSON arrays
    out.write('\n]\n')


@formatter
def html(app_names, out):
    """Print out information on all applications in Sphinx HTML.

    This is intended to be inlined directly into Sphinx documentation.
    We write HTML instead of RST for speed; generating RST from *all*
    applications causes the Sphinx build to take forever. Including this as
    raw HTML is much faster.
    """

    # Read in all applications
    apps = [ramble.repository.get(name) for name in app_names]

    # Start at 2 because the title of the page from Sphinx is id1.
    span_id = 2

    # HTML header with an increasing id span
    def head(n, span_id, title, anchor=None):
        if anchor is None:
            anchor = title
        out.write(('<span id="id%d"></span>'
                   '<h1>%s<a class="headerlink" href="#%s" '
                   'title="Permalink to this headline">&para;</a>'
                   '</h1>\n') % (span_id, title, anchor))

    # Start with the number of applications, skipping the title and intro
    # blurb, which we maintain in the RST file.
    out.write('<p>\n')
    out.write('Ramble currently has %d mainline applications:\n' % len(apps))
    out.write('</p>\n')

    # Table of links to all applications
    out.write('<table border="1" class="docutils">\n')
    out.write('<tbody valign="top">\n')
    for i, row in enumerate(rows_for_ncols(app_names, 3)):
        out.write('<tr class="row-odd">\n' if i % 2 == 0 else
                  '<tr class="row-even">\n')
        for name in row:
            out.write('<td>\n')
            out.write('<a class="reference internal" href="#%s">%s</a></td>\n'
                      % (name, name))
            out.write('</td>\n')
        out.write('</tr>\n')
    out.write('</tbody>\n')
    out.write('</table>\n')
    out.write('<hr class="docutils"/>\n')

    # Output some text for each applications.
    for app in apps:
        out.write('<div class="section" id="%s">\n' % app.name)
        head(2, span_id, app.name)
        span_id += 1

        out.write('<dl class="docutils">\n')

        # out.write('<dt>Homepage:</dt>\n')
        # out.write('<dd><ul class="first last simple">\n')
        # out.write(('<li>'
        #            '<a class="reference external" href="%s">%s</a>'
        #            '</li>\n') % (app.homepage, escape(app.homepage, True)))
        # out.write('</ul></dd>\n')

        out.write('<dt>Ramble applications:</dt>\n')
        out.write('<dd><ul class="first last simple">\n')
        out.write(('<li>'
                   '<a class="reference external" href="%s">%s/application.py</a>'  # noqa: E501
                   '</li>\n') % (github_url(app), app.name))
        out.write('</ul></dd>\n')

        # if app.versions:
        #     out.write('<dt>Versions:</dt>\n')
        #     out.write('<dd>\n')
        #     out.write(', '.join(
        #         str(v) for v in reversed(sorted(app.versions))))
        #     out.write('\n')
        #     out.write('</dd>\n')

        out.write('<dt>Description:</dt>\n')
        out.write('<dd>\n')
        out.write(escape(app.format_doc(indent=2), True))
        out.write('\n')
        out.write('</dd>\n')
        out.write('</dl>\n')

        out.write('<hr class="docutils"/>\n')
        out.write('</div>\n')


def list(parser, args):
    # retrieve the formatter to use from args
    formatter = formatters[args.format]

    app_type = ramble.repository.ObjectTypes.applications

    # Retrieve the names of all the applications
    apps = set(ramble.repository.all_object_names(app_type))
    # Filter the set appropriately
    sorted_applications = filter_by_name(apps, args)

    # Filter by tags
    if args.tags:
        applications_with_tags = set(
            ramble.repository.paths[app_type].objects_with_tags(*args.tags))
        sorted_applications = set(sorted_applications) & applications_with_tags
        sorted_applications = sorted(sorted_applications)

    if args.update:
        # change output stream if user asked for update
        if os.path.exists(args.update):
            if os.path.getmtime(args.update) > \
                    ramble.repository.paths[app_type].last_mtime():
                tty.msg('File is up to date: %s' % args.update)
                return

        tty.msg('Updating file: %s' % args.update)
        with open(args.update, 'w') as f:
            formatter(sorted_applications, f)

    else:
        # Print to stdout
        formatter(sorted_applications, sys.stdout)
