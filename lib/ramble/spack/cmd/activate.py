# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import llnl.util.tty as tty

import spack.cmd
import spack.cmd.common.arguments as arguments
import spack.environment as ev
from spack.filesystem_view import YamlFilesystemView

description = "activate a package extension"
section = "extensions"
level = "long"


def setup_parser(subparser):
    subparser.add_argument(
        '-f', '--force', action='store_true',
        help="activate without first activating dependencies")
    subparser.add_argument(
        '-v', '--view', metavar='VIEW', type=str,
        help="the view to operate on")
    arguments.add_common_arguments(subparser, ['installed_spec'])


def activate(parser, args):

    tty.warn("spack activate is deprecated in favor of "
             "environments and will be removed in v0.19.0")

    specs = spack.cmd.parse_specs(args.spec)
    if len(specs) != 1:
        tty.die("activate requires one spec.  %d given." % len(specs))

    spec = spack.cmd.disambiguate_spec(specs[0], ev.active_environment())
    if not spec.package.is_extension:
        tty.die("%s is not an extension." % spec.name)

    if args.view:
        target = args.view
    else:
        target = spec.package.extendee_spec.prefix

    view = YamlFilesystemView(target, spack.store.layout)

    if spec.package.is_activated(view):
        tty.msg("Package %s is already activated." % specs[0].short_spec)
        return

    # TODO: refactor FilesystemView.add_extension and use that here (so there
    # aren't two ways of activating extensions)
    spec.package.do_activate(view, with_dependencies=not args.force)
