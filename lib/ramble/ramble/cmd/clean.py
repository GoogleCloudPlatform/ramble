# Copyright 2022-2024 Google LLC and other Ramble developers
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import argparse
import os
import shutil

import ramble.caches
import ramble.config
import ramble.repository
import ramble.stage
from ramble.util.logger import logger
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
        logger.msg('Removing cached downloads')
        ramble.caches.fetch_cache.destroy()

    if args.misc_cache:
        logger.msg('Removing cached information on repositories')
        ramble.caches.misc_cache.destroy()

    if args.python_cache:
        logger.msg('Removing python cache files')
        for directory in [lib_path, var_path]:
            for root, dirs, files in os.walk(directory):
                for f in files:
                    if f.endswith('.pyc') or f.endswith('.pyo'):
                        fname = os.path.join(root, f)
                        logger.debug(f'Removing {fname}')
                        os.remove(fname)
                for d in dirs:
                    if d == '__pycache__':
                        dname = os.path.join(root, d)
                        logger.debug(f'Removing {dname}')
                        shutil.rmtree(dname)
