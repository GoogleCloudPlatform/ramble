# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
from __future__ import print_function

import os
import re
from collections import defaultdict

import ramble.paths
from ramble.util.logger import logger
from spack.util.executable import which

description = 'list and check license headers on files in ramble'
section = "developer"
level = "long"

#: need the git command to check new files
git = which('git')

#: SPDX license id must appear in the first <license_lines> lines of a file
license_lines = 9

#: Ramble's license identifier
apache2_mit_spdx = "(Apache-2.0 OR MIT)"

#: regular expressions for licensed files.
licensed_files = [
    # ramble scripts
    r'^bin/ramble$',
    r'^bin/ramble-python$',

    # all of ramble core
    r'^lib/ramble/ramble/.*\.py$',
    r'^lib/ramble/ramble/.*\.sh$',
    r'^lib/ramble/llnl/.*\.py$',

    # rst files in documentation
    r'^lib/ramble/docs/(?!command_index|ramble|llnl).*\.rst$',
    r'^lib/ramble/docs/.*\.py$',

    # 2 files in external
    r'^lib/ramble/external/__init__.py$',
    r'^lib/ramble/external/ordereddict_backport.py$',

    # shell scripts in share
    r'^share/ramble/.*\.sh$',
    r'^share/ramble/.*\.bash$',
    r'^share/ramble/.*\.csh$',
    r'^share/ramble/qa/run-[^/]*$',

    # all applications
    r'^var/ramble/repos/.*/application.py$'
]

#: licensed files that can have LGPL language in them
#: so far, just this command -- so it can find LGPL things elsewhere
lgpl_exceptions = [
    r'lib/ramble/ramble/cmd/license.py',
    r'lib/ramble/ramble/test/cmd/license.py',
]


def _all_ramble_files(root=ramble.paths.prefix):
    """Generates root-relative paths of all files in the ramble repository."""
    visited = set()
    for cur_root, folders, files in os.walk(root):
        for filename in files:
            path = os.path.realpath(os.path.join(cur_root, filename))

            if path not in visited:
                yield os.path.relpath(path, root)
                visited.add(path)


def _licensed_files(root=ramble.paths.prefix):
    for relpath in _all_ramble_files(root):
        if any(regex.match(relpath) for regex in licensed_files):
            yield relpath


def list_files(args):
    """list files in ramble that should have license headers"""
    for relpath in sorted(_licensed_files()):
        print(os.path.join(ramble.paths.ramble_root, relpath))


# Error codes for license verification. All values are chosen such that
# bool(value) evaluates to True
OLD_LICENSE, SPDX_MISMATCH, GENERAL_MISMATCH = range(1, 4)


class LicenseError(object):
    def __init__(self):
        self.error_counts = defaultdict(int)

    def add_error(self, error):
        self.error_counts[error] += 1

    def has_errors(self):
        return sum(self.error_counts.values()) > 0

    def error_messages(self):
        total = sum(self.error_counts.values())
        missing = self.error_counts[GENERAL_MISMATCH]
        spdx_mismatch = self.error_counts[SPDX_MISMATCH]
        old_license = self.error_counts[OLD_LICENSE]
        return (
            '%d improperly licensed files' % (total),
            'files with wrong SPDX-License-Identifier:   %d' % spdx_mismatch,
            'files with old license header:              %d' % old_license,
            'files not containing expected license:      %d' % missing)


def _check_license(lines, path):
    license_lines = [
        r'Copyright 2022-2023 Google LLC',  # noqa: E501
        r'Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or',  # noqa: E501
        r'https://www.apache.org/licenses/LICENSE-2.0> or the MIT license',  # noqa: E501
        r'<LICENSE-MIT or https://opensource.org/licenses/MIT>, at your',  # noqa: E501
        r'option. This file may not be copied, modified, or distributed',  # noqa: E501
        r'except according to those terms.'  # noqa: E501
    ]

    strict_date = r'Copyright 2022'

    found = []

    for line in lines:
        line = re.sub(r'^[\s#\.]*', '', line)
        line = line.rstrip()
        for i, license_line in enumerate(license_lines):
            if re.match(license_line, line):
                # The first line of the license contains the copyright date.
                # We allow it to be out of date but print a warning if it is
                # out of date.
                if i == 0:
                    if not re.search(strict_date, line):
                        logger.debug(f'{path}: copyright date mismatch')
                found.append(i)

    if len(found) == len(license_lines) and found == list(sorted(found)):
        return

    def old_license(line, path):
        if re.search('This program is free software', line):
            print('{0}: has old LGPL license header'.format(path))
            return OLD_LICENSE

    # If the SPDX identifier is present, then there is a mismatch (since it
    # did not match the above regex)
    def wrong_spdx_identifier(line, path):
        m = re.search(r'SPDX-License-Identifier: ([^\n]*)', line)
        if m and m.group(1) != apache2_mit_spdx:
            print('{0}: SPDX license identifier mismatch'
                  '(expecting {1}, found {2})'
                  .format(path, apache2_mit_spdx, m.group(1)))
            return SPDX_MISMATCH

    checks = [old_license, wrong_spdx_identifier]

    for line in lines:
        for check in checks:
            error = check(line, path)
            if error:
                return error

    print('{0}: the license does not match the expected format'.format(path))
    return GENERAL_MISMATCH


def verify(args):
    """verify that files in ramble have the right license header"""

    license_errors = LicenseError()

    for relpath in _licensed_files(args.root):
        path = os.path.join(args.root, relpath)
        with open(path) as f:
            lines = [line for line in f][:license_lines]

        error = _check_license(lines, path)
        if error:
            license_errors.add_error(error)

    if license_errors.has_errors():
        logger.die(*license_errors.error_messages())
    else:
        logger.msg('No license issues found.')


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar='SUBCOMMAND', dest='license_command')
    sp.add_parser('list-files', help=list_files.__doc__,
                  description=list_files.__doc__)

    verify_parser = sp.add_parser('verify', help=verify.__doc__,
                                  description=verify.__doc__)
    verify_parser.add_argument(
        '--root', action='store', default=ramble.paths.prefix,
        help='scan a different prefix for license issues')


def license(parser, args):
    if not git:
        logger.die('ramble license requires git in your environment')

    licensed_files[:] = [re.compile(regex) for regex in licensed_files]

    commands = {
        'list-files': list_files,
        'verify': verify,
    }
    return commands[args.license_command](args)
