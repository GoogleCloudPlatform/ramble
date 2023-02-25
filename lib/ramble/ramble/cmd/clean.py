# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import argparse
import os
import shutil

import llnl.util.tty as tty

import ramble.caches
import ramble.config
import ramble.repository
import ramble.stage
from ramble.paths import lib_path, var_path

description = "remove temporary files and/or downloaded archives"
section = "cleanup"
level = "long"


class AllClean(argparse.Action):
    """Activates flags -d -m and -p simultaneously"""
    def __call__(self, parser, namespace, values, option_string=None):
        parser.parse_args(['-dmp'], namespace=namespace)


def setup_parser(subparser):
    subparser.add_argument(
        '-d', '--downloads', action='store_true',
        help="remove cached downloads (default)")
    subparser.add_argument(
        '-m', '--misc-cache', action='store_true',
        help="remove long-lived caches")
    subparser.add_argument(
        '-p', '--python-cache', action='store_true',
        help="remove .pyc, .pyo files and __pycache__ folders")
    subparser.add_argument(
        '-a', '--all', action=AllClean,
        help="equivalent to -dmp",
        nargs=0
    )


def clean(parser, args):
    # If nothing was set, activate the default
    if not any([args.downloads, args.misc_cache, args.python_cache]):
        args.downloads = True

    if args.downloads:
        tty.msg('Removing cached downloads')
        ramble.caches.fetch_cache.destroy()

    if args.misc_cache:
        tty.msg('Removing cached information on repositories')
        ramble.caches.misc_cache.destroy()

    if args.python_cache:
        tty.msg('Removing python cache files')
        for directory in [lib_path, var_path]:
            for root, dirs, files in os.walk(directory):
                for f in files:
                    if f.endswith('.pyc') or f.endswith('.pyo'):
                        fname = os.path.join(root, f)
                        tty.debug('Removing {0}'.format(fname))
                        os.remove(fname)
                for d in dirs:
                    if d == '__pycache__':
                        dname = os.path.join(root, d)
                        tty.debug('Removing {0}'.format(dname))
                        shutil.rmtree(dname)
