# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum
import stat
import os
import shutil
import py.path
import shlex

import llnl.util.filesystem as fs
import llnl.util.tty as tty
from llnl.util.tty.color import cprint

import ramble.application
import ramble.config
import ramble.experiment_set
import ramble.repository
import ramble.software_environments
import ramble.util.hashing
import ramble.fetch_strategy
import ramble.stage
import ramble.workspace
import ramble.expander

import ramble.experimental.uploader

import ramble.util.path

from ramble.namespace import namespace
from ramble.util.logger import logger

import spack.util.spack_json as sjson
from spack.util.executable import which, Executable

if not ramble.config.get("config:disable_progress_bar", False):
    try:
        import tqdm
    except ModuleNotFoundError:
        logger.die("Module `tqdm` is not found. Ensure requirements.txt are installed.")


class Pipeline:
    """Base Class for all pipeline objects"""

    name = "base"

    def __init__(self, workspace, filters):
        """Create a new pipeline instance"""
        self.filters = filters
        self.workspace = workspace
        self.force_inventory = False
        self.require_inventory = False
        self.action_string = "Operating on"
        self.suppress_per_experiment_prints = False
        self.suppress_run_header = False

        dt = self.workspace.date_string()
        log_file = f"{self.name}.{dt}.out"
        self.log_dir = os.path.join(self.workspace.log_dir, f"{self.name}.{dt}")
        self.log_dir_latest = os.path.join(self.workspace.log_dir, f"{self.name}.latest")
        self.log_path = os.path.join(self.workspace.log_dir, log_file)
        self.log_path_latest = os.path.join(self.workspace.log_dir, f"{self.name}.latest.out")

        self._software_environments = ramble.software_environments.SoftwareEnvironments(workspace)
        self.workspace.software_environments = self._software_environments
        self._experiment_set = workspace.build_experiment_set()

    def _construct_experiment_hashes(self):
        """Hash all of the experiments.

        Populate the workspace inventory information with experiment hash data.
        """
        for exp, app_inst, _ in self._experiment_set.all_experiments():
            app_inst.populate_inventory(
                self.workspace,
                force_compute=self.force_inventory,
                require_exist=self.require_inventory,
            )

    def _construct_workspace_hash(self):
        """Construct workspace inventory

        Assumes experiment hashes are already constructed and populated into
        the workspace.
        """
        workspace_inventory = os.path.join(self.workspace.root, self.workspace.inventory_file_name)
        workspace_hash_file = os.path.join(self.workspace.root, self.workspace.hash_file_name)

        files_exist = os.path.exists(workspace_inventory) and os.path.exists(workspace_hash_file)

        if not self.force_inventory and files_exist:
            with open(workspace_inventory) as f:
                self.workspace.hash_inventory = sjson.load(f)

            self.workspace.workspace_hash = ramble.util.hashing.hash_json(
                self.workspace.hash_inventory
            )
        else:
            for exp, app_inst, _ in sorted(self._experiment_set.all_experiments()):
                if not (app_inst.is_template or app_inst.repeats.is_repeat_base):
                    self.workspace.hash_inventory["experiments"].append(
                        {
                            "name": exp,
                            "digest": app_inst.experiment_hash,
                            "contents": app_inst.hash_inventory,
                        }
                    )

            self.workspace.workspace_hash = ramble.util.hashing.hash_json(
                self.workspace.hash_inventory
            )
            with open(
                os.path.join(self.workspace.root, self.workspace.inventory_file_name), "w+"
            ) as f:
                sjson.dump(self.workspace.hash_inventory, f)

            with open(os.path.join(self.workspace.root, self.workspace.hash_file_name), "w+") as f:
                f.write(self.workspace.workspace_hash + "\n")

            self.workspace.update_metadata("workspace_digest", self.workspace.workspace_hash)
            self.workspace._write_metadata()

    def _prepare(self):
        """Perform preparation for pipeline execution"""
        pass

    def _execute(self):
        """Hook for executing the pipeline"""

        num_exps = self._experiment_set.num_filtered_experiments(self.filters)

        if logger.enabled:
            fs.mkdirp(self.log_dir)
            # Also create simlink to give known paths
            self.create_simlink(self.log_dir, self.log_dir_latest)

        if self.suppress_per_experiment_prints and not self.suppress_run_header:
            logger.all_msg(f"  Log files for experiments are stored in: {self.log_dir}")

        count = 1
        phase_total = 0

        for exp, app_inst, idx in self._experiment_set.filtered_experiments(self.filters):
            exp_log_path = app_inst.experiment_log_file(self.log_dir)

            experiment_index_value = app_inst.expander.expand_var_name(
                app_inst.keywords.experiment_index
            )

            if not self.suppress_per_experiment_prints:
                logger.all_msg(f"Experiment #{idx} ({count}/{num_exps}):")
                logger.all_msg(f"    name: {exp}")
                logger.all_msg(f"    root experiment_index: {experiment_index_value}")
                logger.all_msg(f"    log file: {exp_log_path}")

            logger.add_log(exp_log_path)

            phase_list = app_inst.get_pipeline_phases(self.name, self.filters.phases)

            disable_progress = (
                ramble.config.get("config:disable_progress_bar", False)
                or self.suppress_per_experiment_prints
            )
            if not disable_progress:
                try:
                    progress = tqdm.tqdm(
                        total=len(phase_list),
                        leave=True,
                        ascii=" >=",
                        bar_format="{l_bar}{bar}| Elapsed (s): {elapsed_s:.2f}",
                    )
                except AttributeError:
                    logger.die("tdqm.tdqm is not found. Ensure requirements.txt are installed.")
            for phase_idx, phase in enumerate(phase_list):
                if not disable_progress:
                    progress.set_description(
                        f"Processing phase {phase} ({phase_idx}/{len(phase_list)})"
                    )
                app_inst.run_phase(self.name, phase, self.workspace)
                phase_total += 1
                if not disable_progress:
                    progress.update()
            app_inst.print_phase_times(self.name, self.filters.phases)
            if not disable_progress:
                progress.set_description("Experiment complete")
                progress.close()

            logger.remove_log()
            if not self.suppress_per_experiment_prints:
                logger.all_msg(f"  Returning to log file: {logger.active_log()}")

            count += 1

        if phase_total == 0 and self.filters.phases != ramble.filters.ALL_PHASES:
            logger.warn("No valid phases were selected, please verify requested phases")

    def _complete(self):
        """Hook for performing pipeline actions after execution is complete"""
        pass

    def run(self):
        """Run the full pipeline"""
        if not self.suppress_run_header:
            logger.all_msg("Streaming details to log:")
            logger.all_msg(f"  {self.log_path}")
            if self.workspace.dry_run:
                cprint("@*g{      -- DRY-RUN -- DRY-RUN -- DRY-RUN -- DRY-RUN -- DRY-RUN --}")

            experiment_count = self._experiment_set.num_filtered_experiments(self.filters)
            experiment_total = self._experiment_set.num_experiments()
            logger.all_msg(
                f"  {self.action_string} {experiment_count} out of "
                f"{experiment_total} experiments:"
            )

        logger.add_log(self.log_path)
        if logger.enabled:
            self.create_simlink(self.log_path, self.log_path_latest)

        self._prepare()
        self._execute()
        self._complete()
        logger.remove_log()

    def create_simlink(self, base, link):
        """
        Create simlink of a file to give a known and predictable path
        """
        if os.path.islink(link):
            os.unlink(link)

        os.symlink(base, link)


class AnalyzePipeline(Pipeline):
    """Class for the analyze pipeline"""

    name = "analyze"

    def __init__(
        self,
        workspace,
        filters,
        output_formats=["text"],
        upload=False,
        print_results=False,
        summary_only=False,
    ):
        workspace_success = {namespace.success: ramble.config.config.get_config(namespace.success)}

        workspace.extract_success_criteria("workspace", workspace_success)

        super().__init__(workspace, filters)
        self.action_string = "Analyzing"
        self.output_formats = output_formats
        self.require_inventory = True
        self.upload_results = upload
        self.print_results = print_results
        self.summary_only = summary_only

    def _prepare(self):

        # We only want to let the user run analyze if one of the following is true:
        # - At least one expeirment is set up
        # - `--dry-run` is enabled
        found_valid_experiment = False
        # Record how many non-analyzable experiments are encountered
        no_analyze_cnt = 0
        for _, app_inst, _ in self._experiment_set.filtered_experiments(self.filters):
            if not (app_inst.is_template or app_inst.repeats.is_repeat_base):
                if app_inst.get_status() != ramble.application.experiment_status.UNKNOWN.name:
                    found_valid_experiment = True
            else:
                no_analyze_cnt += 1

        num_total_exps = self._experiment_set.num_experiments()
        num_filtered_exps = self._experiment_set.num_filtered_experiments(self.filters)
        if not found_valid_experiment and num_total_exps:
            if not num_filtered_exps:
                logger.die("No experiment left for analysis after filtering.")
            if num_filtered_exps == no_analyze_cnt:
                logger.die(
                    "No analyzeable experiment detected."
                    " All selected ones are either templates or the base of"
                    " repeated experiments."
                )
            logger.die(
                "No analyzeable experiment detected."
                " Make sure your workspace is setup with\n"
                "    ramble workspace setup"
            )
        super()._construct_experiment_hashes()
        super()._construct_workspace_hash()
        super()._prepare()

    def _complete(self):
        # Calculate statistics for repeats and inject into base experiment results
        for _, app_inst, _ in self._experiment_set.filtered_experiments(self.filters):

            if app_inst.repeats.n_repeats > 0:
                app_inst.calculate_statistics(self.workspace)
        self.workspace.dump_results(
            output_formats=self.output_formats,
            print_results=self.print_results,
            summary_only=self.summary_only,
        )

        if self.upload_results:
            ramble.experimental.uploader.upload_results(self.workspace.results)


class ArchivePipeline(Pipeline):
    """Class for the archive pipeline"""

    name = "archive"

    def __init__(
        self,
        workspace,
        filters,
        create_tar=False,
        archive_prefix=None,
        upload_url=None,
        include_secrets=False,
    ):
        super().__init__(workspace, filters)
        self.action_string = "Archiving"
        self.create_tar = create_tar
        self.upload_url = upload_url
        self.include_secrets = include_secrets
        self.archive_prefix = archive_prefix
        self.archive_name = None

        if self.upload_url and not self.create_tar:
            logger.warn("Upload URL is currently only supported when using tar format (-t)")
            logger.warn("Forcing `-t` on to enable archive upload.\n")
            self.create_tar = True

    def _prepare(self):
        super()._construct_experiment_hashes()
        super()._construct_workspace_hash()
        super()._prepare()

        date_str = self.workspace.date_string()

        # Use the basename from the path as the name of the workspace.
        # If we use `self.workspace.name` we get the path multiple times.

        if not self.archive_prefix:
            self.archive_prefix = os.path.basename(self.workspace.path)

        self.archive_name = f"{self.archive_prefix}-archive-{date_str}"

        archive_path = os.path.join(self.workspace.archive_dir, self.archive_name)
        fs.mkdirp(archive_path)

        for filename in [
            ramble.workspace.Workspace.inventory_file_name,
            ramble.workspace.Workspace.hash_file_name,
        ]:
            src = os.path.join(self.workspace.root, filename)
            if os.path.exists(src):
                dest = src.replace(self.workspace.root, archive_path)
                shutil.copyfile(src, dest)

        # Copy current configs
        archive_configs = os.path.join(
            self.workspace.latest_archive_path, ramble.workspace.workspace_config_path
        )
        _copy_tree(self.workspace.config_dir, archive_configs)

        # Copy shared files
        archive_shared = os.path.join(
            self.workspace.latest_archive_path, ramble.workspace.workspace_shared_path
        )

        excluded_secrets = set()
        if not self.include_secrets:
            excluded_secrets.add(ramble.application.ApplicationBase.license_inc_name)

        fs.mkdirp(archive_shared)
        for root, dirs, files in os.walk(self.workspace.shared_dir):
            for name in files:
                if name not in excluded_secrets:
                    src_dir = os.path.join(self.workspace.shared_dir, root)
                    src = os.path.join(src_dir, name)
                    dest = src.replace(self.workspace.shared_dir, archive_shared)
                    fs.mkdirp(os.path.dirname(dest))
                    shutil.copy(src, dest)

        # Copy logs, but omit all symlinks (i.e. "latest")
        archive_logs = os.path.join(
            self.workspace.latest_archive_path, ramble.workspace.workspace_log_path
        )
        fs.mkdirp(archive_logs)
        for root, dirs, files in os.walk(self.workspace.log_dir):
            for name in files:
                src_dir = os.path.join(self.workspace.log_dir, root)
                src = os.path.join(src_dir, name)
                if not (os.path.islink(src_dir) or os.path.islink(src)) and os.path.isfile(src):
                    dest = src.replace(self.workspace.log_dir, archive_logs)
                    fs.mkdirp(os.path.dirname(dest))
                    shutil.copyfile(src, dest)

        archive_path_latest = os.path.join(self.workspace.archive_dir, "archive.latest")
        self.create_simlink(archive_path, archive_path_latest)

    def _complete(self):
        if self.create_tar:
            tar_extension = ".tar.gz"
            tar = which("tar", required=True)
            tar_path = self.archive_name + tar_extension
            with py.path.local(self.workspace.archive_dir).as_cwd():
                tar("-czf", tar_path, self.archive_name)

            archive_url = (
                self.upload_url if self.upload_url else ramble.config.get("config:archive_url")
            )
            archive_url = archive_url.rstrip("/") if archive_url else None

            tar_path_latest = os.path.join(
                self.workspace.archive_dir, "archive.latest" + tar_extension
            )

            self.create_simlink(tar_path, tar_path_latest)

            logger.debug(f"Archive url: {archive_url}")

            if archive_url:
                # Perform Upload
                tar_path = self.workspace.latest_archive_path + tar_extension
                remote_tar_path = archive_url + "/" + self.workspace.latest_archive + tar_extension
                _upload_file(tar_path, remote_tar_path)
                logger.all_msg(f"Archive Uploaded to {remote_tar_path}")

                # Record upload URL to workspace metadata
                self.workspace.update_metadata("archive_url", remote_tar_path)
                self.workspace._write_metadata()


class MirrorPipeline(Pipeline):
    """Class for the mirror pipeline"""

    name = "mirror"

    def __init__(self, workspace, filters, mirror_path=None):
        super().__init__(workspace, filters)
        self.action_string = "Mirroring"
        self.mirror_path = mirror_path

    def _prepare(self):
        super()._prepare()
        self.workspace.create_mirror(self.mirror_path)

    def _complete(self):
        verb = "updated" if self.workspace.mirror_existed else "created"
        logger.msg(
            f"Successfully {verb} spack software in {self.workspace.mirror_path}",
            "Archive stats:",
            "  %-4d already present" % len(self.workspace.software_mirror_stats.present),
            "  %-4d added" % len(self.workspace.software_mirror_stats.new),
            "  %-4d failed to fetch." % len(self.workspace.software_mirror_stats.errors),
        )

        logger.msg(
            f"Successfully {verb} inputs in {self.workspace.mirror_path}",
            "Archive stats:",
            "  %-4d already present" % len(self.workspace.input_mirror_stats.present),
            "  %-4d added" % len(self.workspace.input_mirror_stats.new),
            "  %-4d failed to fetch." % len(self.workspace.input_mirror_stats.errors),
        )

        if self.workspace.input_mirror_stats.errors:
            logger.error("Failed downloads:")
            tty.colify(
                (s.cformat("{name}") for s in list(self.workspace.input_mirror_stats.errors)),
                output=logger.active_stream(),
            )
            logger.die("Mirroring has errors.")


class SetupPipeline(Pipeline):
    """Class for the setup pipeline"""

    name = "setup"

    def __init__(self, workspace, filters):
        super().__init__(workspace, filters)
        self.force_inventory = True
        self.require_inventory = False
        self.action_string = "Setting up"

    def _prepare(self):
        # Check if the selected phases require the inventory is successful
        if "write_inventory" in self.filters.phases or "*" in self.filters.phases:
            self.require_inventory = True

        super()._prepare()
        experiment_file = open(self.workspace.all_experiments_path, "w+")
        shell = ramble.config.get("config:shell")
        shell_path = os.path.join("/bin/", shell)
        experiment_file.write(f"#!{shell_path}\n")
        self.workspace.experiments_script = experiment_file

        super()._construct_experiment_hashes()

    def _complete(self):
        try:
            super()._construct_workspace_hash()
        except FileNotFoundError as e:
            tty.warn("Unable to construct workspace hash due to missing file")
            tty.warn(e)

        self.workspace.experiments_script.close()
        experiment_file_path = os.path.join(
            self.workspace.root, self.workspace.all_experiments_path
        )
        os.chmod(experiment_file_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)


class PushToCachePipeline(Pipeline):
    """Class for the pushtocache pipeline"""

    name = "pushtocache"

    def __init__(self, workspace, filters, spack_cache_path=None):
        super().__init__(workspace, filters)
        self.action_string = "Pushing to Spack Cache"
        self.spack_cache_path = spack_cache_path

    def _prepare(self):
        super()._prepare()
        self.workspace.spack_cache_path = self.spack_cache_path

    def _complete(self):
        logger.msg(f"Pushed envs to spack cache {self.spack_cache_path}")


class ExecutePipeline(Pipeline):
    """class for the `execute` (`on`) pipeline"""

    name = "execute"

    def __init__(
        self,
        workspace,
        filters,
        executor="{batch_submit}",
        suppress_per_experiment_prints=True,
        suppress_run_header=False,
    ):
        super().__init__(workspace, filters)
        self.action_string = "Executing"
        self.require_inventory = True
        self.executor = executor
        self.suppress_per_experiment_prints = suppress_per_experiment_prints
        self.suppress_run_header = suppress_run_header

    def _execute(self):
        super()._execute()

        if not self.suppress_run_header:
            logger.all_msg("Running executors...")

        for exp, app_inst, idx in self._experiment_set.filtered_experiments(self.filters):
            if app_inst.is_template:
                logger.debug(f"{app_inst.name} is a template. Skipping execution.")
                continue
            if app_inst.repeats.is_repeat_base:
                logger.debug(f"{app_inst.name} is a repeat base. Skipping execution.")
                continue

            app_inst.add_expand_vars(self.workspace)
            exec_str = app_inst.expander.expand_var(self.executor)
            exec_parts = shlex.split(exec_str)
            exec_name = exec_parts[0]
            exec_args = exec_parts[1:]

            executor = Executable(exec_name)
            executor(*exec_args)


class PushDeploymentPipeline(Pipeline):
    """class for the `prepare-deployment` pipeline"""

    name = "pushdeployment"
    index_filename = "index.json"
    index_namespace = "deployment_files"
    tar_extension = ".tar.gz"
    object_repo_name = "object_repo"

    def __init__(
        self, workspace, filters, create_tar=False, upload_url=None, deployment_name=None
    ):
        super().__init__(workspace, filters)

        workspace_expander = ramble.expander.Expander(workspace.get_workspace_vars(), None)

        self.action_string = "Pushing deployment of"
        self.require_inventory = True
        self.create_tar = create_tar
        expanded_url = workspace_expander.expand_var(upload_url)
        self.upload_url = ramble.util.path.normalize_path_or_url(expanded_url)

        if deployment_name:
            expanded_name = workspace_expander.expand_var(deployment_name)
            workspace.deployment_name = expanded_name
            self.deployment_name = expanded_name
        else:
            self.deployment_name = workspace.name

    def _execute(self):
        configs_dir = os.path.join(
            self.workspace.named_deployment, ramble.workspace.workspace_config_path
        )
        fs.mkdirp(configs_dir)

        _copy_tree(self.workspace.config_dir, configs_dir)

        aux_software_dir = os.path.join(configs_dir, ramble.workspace.auxiliary_software_dir_name)
        fs.mkdirp(aux_software_dir)

        repo_path = os.path.join(self.workspace.named_deployment, self.object_repo_name)
        for object_type_def in ramble.repository.type_definitions.values():
            fs.mkdirp(os.path.join(repo_path, object_type_def["dir_name"]))

        # Write out only to the unified repo.yaml
        with open(os.path.join(repo_path, ramble.repository.unified_config), "w+") as f:
            f.write("repo:\n")
            f.write(f"  namespace: deployment_{self.deployment_name}\n")

        super()._execute()

    def _deployment_files(self):
        """Yield the full path to each file in a deployment"""
        for root, dirs, files in os.walk(self.workspace.named_deployment):
            for name in files:
                yield os.path.join(self.workspace.named_deployment, root, name)

    def _complete(self):
        # Create an index.json of the deployment
        deployment_index = {self.index_namespace: []}
        for file in self._deployment_files():
            deployment_index[self.index_namespace].append(
                file.replace(self.workspace.named_deployment + os.path.sep, "")
            )
        index_file = os.path.join(self.workspace.named_deployment, self.index_filename)
        with open(index_file, "w+") as f:
            f.write(sjson.dump(deployment_index))

        tar_path = os.path.join(
            self.workspace.deployments_dir, self.deployment_name + self.tar_extension
        )
        if self.create_tar:
            tar = which("tar", required=True)
            with py.path.local(self.workspace.deployments_dir).as_cwd():
                tar("-czf", tar_path, self.deployment_name)

        if self.upload_url:
            remote_base = self.upload_url + "/" + self.deployment_name

            for file in self._deployment_files():
                dest = file.replace(self.workspace.named_deployment, remote_base)
                _upload_file(file, dest)

            if self.create_tar:
                stage_dir = self.workspace.deployments_dir
                tar_path = os.path.join(stage_dir, self.deployment_name + self.tar_extension)
                remote_tar_path = self.upload_url + "/" + self.deployment_name + self.tar_extension
                _upload_file(tar_path, remote_tar_path)

        logger.all_msg(f"Deployment created in: {self.workspace.named_deployment}")
        if self.create_tar:
            logger.all_msg(f"  Tar of deployment created in: {tar_path}")
        if self.upload_url:
            remote_base = self.upload_url + "/" + self.deployment_name
            logger.all_msg(f"  Deployment uploaded to: {remote_base}")


def _copy_tree(src_dir, dest_dir):
    """Copy all files in src_dir to dest_dir"""
    for root, dirs, files in os.walk(src_dir):
        for name in files:
            src = os.path.join(src_dir, root, name)
            dest = src.replace(src_dir, dest_dir)
            fs.mkdirp(os.path.dirname(dest))
            shutil.copyfile(src, dest)


def _upload_file(src_file, dest_file):
    stage_dir = os.path.dirname(src_file)
    fetcher = ramble.fetch_strategy.URLFetchStrategy(src_file)
    fetcher.stage = ramble.stage.DIYStage(stage_dir)
    fetcher.stage.archive_file = src_file
    fetcher.archive(dest_file)


pipelines = Enum(
    "pipelines",
    [
        AnalyzePipeline.name,
        ArchivePipeline.name,
        MirrorPipeline.name,
        SetupPipeline.name,
        PushToCachePipeline.name,
        ExecutePipeline.name,
        PushDeploymentPipeline.name,
    ],
)

_pipeline_map = {
    pipelines.analyze: AnalyzePipeline,
    pipelines.archive: ArchivePipeline,
    pipelines.mirror: MirrorPipeline,
    pipelines.setup: SetupPipeline,
    pipelines.pushtocache: PushToCachePipeline,
    pipelines.execute: ExecutePipeline,
    pipelines.pushdeployment: PushDeploymentPipeline,
}


def pipeline_class(name):
    """Factory for determining a pipeline class from its name"""

    if name not in _pipeline_map.keys():
        logger.die(
            f"Pipeline {name} is not valid.\n" f"Valid pipelines are {_pipeline_map.keys()}"
        )

    return _pipeline_map[name]
