# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.workspace
import ramble.expander
import ramble.pipeline
import ramble.filters

import ramble.cmd.common.arguments as arguments


description = '"And now\'s the time, the time is now" (execute workspace experiments)'
section = "workspaces"
level = "short"


def setup_parser(subparser):
    subparser.add_argument(
        "--executor",
        metavar="executor",
        dest="executor",
        help="execution template for each experiment",
        required=False,
    )

    subparser.add_argument(
        "--enable-per-experiment-prints",
        action="store_true",
        dest="per_experiment_prints_on",
        help="Enable per experiment prints (phases and log paths).",
    )

    subparser.add_argument(
        "--suppress-run-header",
        action="store_true",
        dest="run_header_off",
        help="Disable the logger header.",
    )

    arguments.add_common_arguments(subparser, ["where", "exclude_where", "filter_tags"])


def ramble_on(args):
    current_pipeline = ramble.pipeline.pipelines.execute
    ws = ramble.cmd.require_active_workspace(cmd_name="on")

    executor = args.executor if args.executor else "{batch_submit}"

    filters = ramble.filters.Filters(
        phase_filters=["*"],
        include_where_filters=args.where,
        exclude_where_filters=args.exclude_where,
        tags=args.filter_tags,
    )

    suppress_per_experiment_prints = not args.per_experiment_prints_on
    suppress_run_header = args.run_header_off

    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)
    pipeline = pipeline_cls(
        ws,
        filters,
        executor=executor,
        suppress_per_experiment_prints=suppress_per_experiment_prints,
        suppress_run_header=suppress_run_header,
    )

    with ws.write_transaction():
        pipeline.run()


def on(parser, args):
    """Execute `ramble_on` command"""
    ramble_on(args)
