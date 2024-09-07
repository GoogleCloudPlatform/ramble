# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import llnl.util.filesystem as fs

import spack.util.spack_json as sjson
import spack.util.url as surl

import ramble.cmd
import ramble.cmd.common.arguments
import ramble.cmd.common.arguments as arguments

import ramble.fetch_strategy
import ramble.config
import ramble.stage
import ramble.workspace
import ramble.workspace.shell
import ramble.pipeline
import ramble.filters
from ramble.main import RambleCommand


description = "(experimental) manage workspace deployments"
section = "workspaces"
level = "short"

subcommands = [
    "push",
    "pull",
]


def deployment_push_setup_parser(subparser):
    """Push a workspace deployment"""
    subparser.add_argument(
        "--tar-archive",
        "-t",
        action="store_true",
        dest="tar_archive",
        help="create a tar.gz of the deployment directory.",
    )

    subparser.add_argument(
        "--deployment-name",
        "-d",
        dest="deployment_name",
        default=None,
        help="Name for deployment. Uses workspace name if not set.",
    )

    subparser.add_argument(
        "--upload-url",
        "-u",
        dest="upload_url",
        default=None,
        help="URL to upload deployment into. Upload tar if `-t` is specified..",
    )

    arguments.add_common_arguments(
        subparser,
        ["phases", "include_phase_dependencies", "where", "exclude_where", "filter_tags"],
    )


def deployment_push(args):
    current_pipeline = ramble.pipeline.pipelines.pushdeployment
    ws = ramble.cmd.require_active_workspace(cmd_name="deployment push")

    filters = ramble.filters.Filters(
        phase_filters=args.phases,
        include_where_filters=args.where,
        exclude_where_filters=args.exclude_where,
        tags=args.filter_tags,
    )

    pipeline_cls = ramble.pipeline.pipeline_class(current_pipeline)

    pipeline = pipeline_cls(
        ws,
        filters,
        create_tar=args.tar_archive,
        upload_url=args.upload_url,
        deployment_name=args.deployment_name,
    )

    with ws.write_transaction():
        deployment_run_pipeline(args, pipeline)


def deployment_pull_setup_parser(subparser):
    """Pull a workspace deployment into current workspace"""
    subparser.add_argument(
        "--deployment-path",
        "-p",
        dest="deployment_path",
        help="Path to deployment that should be pulled",
    )


def deployment_pull(args):
    def pull_file(src, dest):
        fetcher = ramble.fetch_strategy.URLFetchStrategy(url=src)
        stage_dir = os.path.dirname(dest)
        fs.mkdirp(stage_dir)
        with ramble.stage.InputStage(fetcher, path=stage_dir, name=os.path.basename(src)) as stage:
            stage.fetch()

    ws = ramble.cmd.require_active_workspace(cmd_name="deployment pull")

    with ws.write_transaction():
        # Fetch deployment index first:
        push_cls = ramble.pipeline.PushDeploymentPipeline

        remote_index_path = surl.join(
            args.deployment_path, ramble.pipeline.PushDeploymentPipeline.index_filename
        )
        local_index_path = os.path.join(ws.root, push_cls.index_filename)

        pull_file(remote_index_path, local_index_path)

        with open(local_index_path) as f:
            index_data = sjson.load(f)

        for file in index_data[push_cls.index_namespace]:
            src = surl.join(args.deployment_path, file)
            dest = os.path.join(ws.root, file)
            if os.path.exists(dest):
                fs.force_remove(dest)

            pull_file(src, dest)

        obj_repo_path = os.path.join(
            ws.root, ramble.pipeline.PushDeploymentPipeline.object_repo_name
        )
        if os.path.exists(obj_repo_path):
            repo_cmd = RambleCommand("repo")
            repo_cmd("add", obj_repo_path, global_args=["-D", ws.root])


def deployment_run_pipeline(args, pipeline):
    include_phase_dependencies = getattr(args, "include_phase_dependencies", None)
    if include_phase_dependencies:
        with ramble.config.override("config:include_phase_dependencies", True):
            pipeline.run()
    else:
        pipeline.run()


#: Dictionary mapping subcommand names and aliases to functions
subcommand_functions = {}


def sanitize_arg_name(base_name):
    """Allow function names to be remapped (eg `-` to `_`)"""
    formatted_name = base_name.replace("-", "_")
    return formatted_name


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="deployment_command")

    for name in subcommands:
        if isinstance(name, (list, tuple)):
            name, aliases = name[0], name[1:]
        else:
            aliases = []

        # add commands to subcommands dict
        function_name = sanitize_arg_name("deployment_%s" % name)

        function = globals()[function_name]
        for alias in [name] + aliases:
            subcommand_functions[alias] = function

        # make a subparser and run the command's setup function on it
        setup_parser_cmd_name = sanitize_arg_name("deployment_%s_setup_parser" % name)
        setup_parser_cmd = globals()[setup_parser_cmd_name]

        subsubparser = sp.add_parser(
            name,
            aliases=aliases,
            help=setup_parser_cmd.__doc__,
            description=setup_parser_cmd.__doc__,
        )
        setup_parser_cmd(subsubparser)


def deployment(parser, args):
    """Look for a function called deployment_<name> and call it."""
    action = subcommand_functions[args.deployment_command]
    action(args)
