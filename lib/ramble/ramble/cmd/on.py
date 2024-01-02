# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import sys

import ramble.workspace
import ramble.expander
import ramble.pipeline
import ramble.filters

import ramble.cmd.common.arguments as arguments

if sys.version_info >= (3, 3):
    from collections.abc import Sequence  # novm noqa: F401
else:
    from collections import Sequence  # noqa: F401


description = "\"And now's the time, the time is now\" (execute workspace experiments)"
section = 'workspaces'
level = 'short'


def setup_parser(subparser):
    subparser.add_argument(
        '--executor', metavar='executor', dest='executor',
        help='execution template for each experiment',
             required=False)

    arguments.add_common_arguments(subparser, ['where', 'exclude_where'])


def ramble_on(args):
    current_pipeline = ramble.pipeline.pipelines.execute
    ws = ramble.cmd.require_active_workspace(cmd_name='on')

    executor = args.executor if args.executor else '{batch_submit}'

    filters = ramble.filters.Filters(
        phase_filters=[],
        include_where_filters=args.where,
        exclude_where_filters=args.exclude_where
    )

    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)
    pipeline = pipeline_cls(ws, filters, executor=executor)

    with ws.write_transaction():
        pipeline.run()


def on(parser, args):
    """Execute `ramble_on` command"""
    ramble_on(args)
