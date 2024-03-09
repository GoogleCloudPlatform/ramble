# Copyright 2022-2024 Google LLC
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
import ramble.software_environments
import ramble.util.hashing
import ramble.fetch_strategy
import ramble.stage
import ramble.workspace

import ramble.experimental.uploader

from ramble.namespace import namespace
from ramble.util.logger import logger

import spack.util.spack_json as sjson
from spack.util.executable import which, Executable

if not ramble.config.get('config:disable_progress_bar', False):
    try:
        import tqdm
    except ModuleNotFoundError:
        logger.die('Module `tqdm` is not found. Ensure requirements.txt are installed.')


class Pipeline(object):
    """Base Class for all pipeline objects"""
    name = 'base'

    def __init__(self, workspace, filters):
        """Create a new pipeline instance"""
        self.filters = filters
        self.workspace = workspace
        self.force_inventory = False
        self.require_inventory = False
        self.action_string = 'Operating on'
        self.suppress_per_experiment_prints = False
        self.suppress_run_header = False

        dt = self.workspace.date_string()
        log_file = f'{self.name}.{dt}.out'
        self.log_dir = os.path.join(self.workspace.log_dir,
                                    f'{self.name}.{dt}')
        self.log_dir_latest = os.path.join(self.workspace.log_dir,
                                           f'{self.name}.latest')
        self.log_path = os.path.join(self.workspace.log_dir,
                                     log_file)
        self.log_path_latest = os.path.join(self.workspace.log_dir,
                                            f'{self.name}.latest.out')

        fs.mkdirp(self.log_dir)

        # Create simlinks to give known paths
        self.create_simlink(self.log_dir, self.log_dir_latest)
        self.create_simlink(self.log_path, self.log_path_latest)

        self._software_environments = ramble.software_environments.SoftwareEnvironments(workspace)
        self.workspace.software_environments = self._software_environments
        self._experiment_set = workspace.build_experiment_set()

    def _construct_hash(self):
        """Hash all of the experiments, construct workspace inventory"""
        for exp, app_inst, _ in self._experiment_set.all_experiments():
            app_inst.populate_inventory(self.workspace,
                                        force_compute=self.force_inventory,
                                        require_exist=self.require_inventory)

        workspace_inventory = os.path.join(self.workspace.root,
                                           self.workspace.inventory_file_name)
        workspace_hash_file = os.path.join(self.workspace.root,
                                           self.workspace.hash_file_name)

        files_exist = os.path.exists(workspace_inventory) and \
            os.path.exists(workspace_hash_file)

        if not self.force_inventory and files_exist:
            with open(workspace_inventory, 'r') as f:
                self.workspace.hash_inventory = sjson.load(f)

            self.workspace.workspace_hash = \
                ramble.util.hashing.hash_json(self.workspace.hash_inventory)
        else:
            for exp, app_inst, _ in sorted(self._experiment_set.all_experiments()):
                if not (app_inst.is_template or app_inst.repeats.is_repeat_base):
                    self.workspace.hash_inventory['experiments'].append(
                        {
                            'name': exp,
                            'digest': app_inst.experiment_hash,
                            'contents': app_inst.hash_inventory
                        }
                    )

            self.workspace.workspace_hash = \
                ramble.util.hashing.hash_json(self.workspace.hash_inventory)
            with open(os.path.join(self.workspace.root,
                                   self.workspace.inventory_file_name), 'w+') as f:
                sjson.dump(self.workspace.hash_inventory, f)

            with open(os.path.join(self.workspace.root,
                                   self.workspace.hash_file_name), 'w+') as f:
                f.write(self.workspace.workspace_hash + '\n')

    def _validate(self):
        """Perform validation that this pipeline can be executed"""
        if not self.workspace.is_concretized():
            error_message = 'Cannot run %s in a ' % self.name + \
                            'non-conretized workspace\n' + \
                            'Run `ramble workspace concretize` on this ' + \
                            'workspace first.\n' + \
                            'Then ensure its spack configuration is ' + \
                            'properly configured.'
            logger.die(error_message)

    def _prepare(self):
        """Perform preparation for pipeline execution"""
        pass

    def _execute(self):
        """Hook for executing the pipeline"""

        num_exps = self._experiment_set.num_filtered_experiments(self.filters)

        if self.suppress_per_experiment_prints and not self.suppress_run_header:
            logger.all_msg(f'  Log files for experiments are stored in: {self.log_dir}')

        count = 1
        for exp, app_inst, idx in self._experiment_set.filtered_experiments(self.filters):
            exp_log_path = app_inst.experiment_log_file(self.log_dir)

            experiment_index_value = \
                app_inst.expander.expand_var_name(app_inst.keywords.experiment_index)

            if not self.suppress_per_experiment_prints:
                logger.all_msg(f'Experiment #{idx} ({count}/{num_exps}):')
                logger.all_msg(f'    name: {exp}')
                logger.all_msg(f'    root experiment_index: {experiment_index_value}')
                logger.all_msg(f'    log file: {exp_log_path}')

            logger.add_log(exp_log_path)

            phase_list = app_inst.get_pipeline_phases(self.name, self.filters.phases)

            disable_progress = ramble.config.get('config:disable_progress_bar', False) \
                or self.suppress_per_experiment_prints
            if not disable_progress:
                progress = tqdm.tqdm(total=len(phase_list),
                                     leave=True,
                                     ascii=' >=',
                                     bar_format='{l_bar}{bar}| Elapsed (s): {elapsed_s:.2f}')
            for phase_idx, phase in enumerate(phase_list):
                if not disable_progress:
                    progress.set_description(
                        f'Processing phase {phase} ({phase_idx}/{len(phase_list)})'
                    )
                app_inst.run_phase(self.name, phase, self.workspace)
                if not disable_progress:
                    progress.update()
            app_inst.print_phase_times(self.name, self.filters.phases)
            if not disable_progress:
                progress.set_description('Experiment complete')
                progress.close()

            logger.remove_log()
            if not self.suppress_per_experiment_prints:
                logger.all_msg(f'  Returning to log file: {logger.active_log()}')
            count += 1

    def _complete(self):
        """Hook for performing pipeline actions after execution is complete"""
        pass

    def run(self):
        """Run the full pipeline"""
        if not self.suppress_run_header:
            logger.all_msg('Streaming details to log:')
            logger.all_msg(f'  {self.log_path}')
            if self.workspace.dry_run:
                cprint('@*g{      -- DRY-RUN -- DRY-RUN -- DRY-RUN -- DRY-RUN -- DRY-RUN --}')

            experiment_count = self._experiment_set.num_filtered_experiments(self.filters)
            experiment_total = self._experiment_set.num_experiments()
            logger.all_msg(
                f'  {self.action_string} {experiment_count} out of '
                f'{experiment_total} experiments:'
            )

        logger.add_log(self.log_path)
        self._validate()
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

    name = 'analyze'

    def __init__(self, workspace, filters, output_formats=['text'], upload=False):
        workspace_success = {
            namespace.success: ramble.config.config.get_config(namespace.success)
        }

        workspace.extract_success_criteria('workspace', workspace_success)

        super().__init__(workspace, filters)
        self.action_string = 'Analyzing'
        self.output_formats = output_formats
        self.require_inventory = True
        self.upload_results = upload

    def _prepare(self):
        for _, app_inst, _ in self._experiment_set.filtered_experiments(self.filters):
            if not (app_inst.is_template or app_inst.repeats.is_repeat_base):
                if app_inst.get_status() == ramble.application.experiment_status.UNKNOWN.name:
                    logger.die(
                        f'Workspace status is {app_inst.get_status()}\n'
                        'Make sure your workspace is fully setup with\n'
                        '    ramble workspace setup'
                    )
        super()._construct_hash()
        super()._prepare()

    def _complete(self):
        # Calculate statistics for repeats and inject into base experiment results
        for _, app_inst, _ in self._experiment_set.filtered_experiments(self.filters):

            if app_inst.repeats.n_repeats > 0:
                app_inst.calculate_statistics(self.workspace)

        self.workspace.dump_results(output_formats=self.output_formats)

        if self.upload_results:
            ramble.experimental.uploader.upload_results(self.workspace.results)


class ArchivePipeline(Pipeline):
    """Class for the archive pipeline"""

    name = 'archive'

    def __init__(self, workspace, filters, create_tar=False,
                 archive_prefix=None, upload_url=None,
                 include_secrets=False):
        super().__init__(workspace, filters)
        self.action_string = 'Archiving'
        self.create_tar = create_tar
        self.upload_url = upload_url
        self.include_secrets = include_secrets
        self.archive_prefix = archive_prefix
        self.archive_name = None

    def _prepare(self):
        import glob
        super()._construct_hash()
        super()._prepare()

        date_str = self.workspace.date_string()

        # Use the basename from the path as the name of the workspace.
        # If we use `self.workspace.name` we get the path multiple times.

        if not self.archive_prefix:
            self.archive_prefix = os.path.basename(self.workspace.path)

        self.archive_name = '%s-archive-%s' % (self.archive_prefix, date_str)

        archive_path = os.path.join(self.workspace.archive_dir, self.archive_name)
        fs.mkdirp(archive_path)

        for filename in [ramble.workspace.Workspace.inventory_file_name,
                         ramble.workspace.Workspace.hash_file_name]:
            src = os.path.join(self.workspace.root, filename)
            if os.path.exists(src):
                dest = src.replace(self.workspace.root, archive_path)
                shutil.copyfile(src, dest)

        # Copy current configs
        archive_configs = os.path.join(self.workspace.latest_archive_path,
                                       ramble.workspace.workspace_config_path)
        fs.mkdirp(archive_configs)
        for root, dirs, files in os.walk(self.workspace.config_dir):
            for name in files:
                src = os.path.join(self.workspace.config_dir, root, name)
                dest = src.replace(self.workspace.config_dir, archive_configs)
                fs.mkdirp(os.path.dirname(dest))
                shutil.copyfile(src, dest)

        # Copy current software spack files
        file_names = ['spack.yaml', 'spack.lock']
        archive_software = os.path.join(self.workspace.latest_archive_path,
                                        ramble.workspace.workspace_software_path)
        fs.mkdirp(archive_software)
        for file_name in file_names:
            for file in glob.glob(os.path.join(self.workspace.software_dir, '*', file_name)):
                dest = file.replace(self.workspace.software_dir, archive_software)
                fs.mkdirp(os.path.dirname(dest))
                shutil.copyfile(file, dest)

        # Copy shared files
        archive_shared = os.path.join(self.workspace.latest_archive_path,
                                      ramble.workspace.workspace_shared_path)

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
        archive_logs = os.path.join(self.workspace.latest_archive_path,
                                    ramble.workspace.workspace_log_path)
        fs.mkdirp(archive_logs)
        for root, dirs, files in os.walk(self.workspace.log_dir):
            for name in files:
                src_dir = os.path.join(self.workspace.log_dir, root)
                src = os.path.join(src_dir, name)
                if not (os.path.islink(src_dir) or os.path.islink(src)) \
                        and os.path.isfile(src):
                    dest = src.replace(self.workspace.log_dir, archive_logs)
                    fs.mkdirp(os.path.dirname(dest))
                    shutil.copyfile(src, dest)

        archive_path_latest = os.path.join(self.workspace.archive_dir, 'archive.latest')
        self.create_simlink(archive_path, archive_path_latest)

    def _complete(self):
        if self.create_tar:
            tar_extension = '.tar.gz'
            tar = which('tar', required=True)
            tar_path = self.archive_name + tar_extension
            with py.path.local(self.workspace.archive_dir).as_cwd():
                tar('-czf', tar_path, self.archive_name)

            archive_url = self.upload_url if self.upload_url else \
                ramble.config.get('config:archive_url')
            archive_url = archive_url.rstrip('/') if archive_url else None

            tar_path_latest = os.path.join(
                self.workspace.archive_dir,
                "archive.latest" + tar_extension)

            self.create_simlink(tar_path, tar_path_latest)

            logger.debug(f'Archive url: {archive_url}')

            if archive_url:
                tar_path = self.workspace.latest_archive_path + tar_extension
                remote_tar_path = archive_url + '/' + self.workspace.latest_archive + tar_extension
                fetcher = ramble.fetch_strategy.URLFetchStrategy(tar_path)
                fetcher.stage = ramble.stage.DIYStage(self.workspace.latest_archive_path)
                fetcher.stage.archive_file = tar_path
                fetcher.archive(remote_tar_path)


class MirrorPipeline(Pipeline):
    """Class for the mirror pipeline"""

    name = 'mirror'

    def __init__(self, workspace, filters, mirror_path=None):
        super().__init__(workspace, filters)
        self.action_string = 'Mirroring'
        self.mirror_path = mirror_path

    def _prepare(self):
        super()._prepare()
        self.workspace.create_mirror(self.mirror_path)

    def _complete(self):
        verb = 'updated' if self.workspace.mirror_existed else 'created'
        logger.msg(
            f"Successfully {verb} spack software in {self.workspace.mirror_path}",
            "Archive stats:",
            "  %-4d already present"  % len(self.workspace.software_mirror_stats.present),
            "  %-4d added"            % len(self.workspace.software_mirror_stats.new),
            "  %-4d failed to fetch." % len(self.workspace.software_mirror_stats.errors))

        logger.msg(
            f"Successfully {verb} inputs in {self.workspace.mirror_path}",
            "Archive stats:",
            "  %-4d already present"  % len(self.workspace.input_mirror_stats.present),
            "  %-4d added"            % len(self.workspace.input_mirror_stats.new),
            "  %-4d failed to fetch." % len(self.workspace.input_mirror_stats.errors))

        if self.workspace.input_mirror_stats.errors:
            logger.error("Failed downloads:")
            tty.colify((s.cformat("{name}") for s in
                       list(self.workspace.input_mirror_stats.errors)),
                       output=logger.active_stream())
            logger.die('Mirroring has errors.')


class SetupPipeline(Pipeline):
    """Class for the setup pipeline"""

    name = 'setup'

    def __init__(self, workspace, filters):
        super().__init__(workspace, filters)
        self.force_inventory = True
        self.require_inventory = False
        self.action_string = 'Setting up'

    def _prepare(self):
        super()._prepare()
        experiment_file = open(self.workspace.all_experiments_path, 'w+')
        shell = ramble.config.get('config:shell')
        shell_path = os.path.join('/bin/', shell)
        experiment_file.write(f'#!{shell_path}\n')
        self.workspace.experiments_script = experiment_file

    def _complete(self):
        # Check if the selected phases require the inventory is successful
        if "write_inventory" in self.filters.phases or \
           "*" in self.filters.phases:
            self.require_inventory = True

        try:
            super()._construct_hash()
        except FileNotFoundError as e:
            tty.warn("Unable to construct workspace hash due to missing file")
            tty.warn(e)

        self.workspace.experiments_script.close()
        experiment_file_path = os.path.join(self.workspace.root,
                                            self.workspace.all_experiments_path)
        os.chmod(experiment_file_path, stat.S_IRWXU | stat.S_IRWXG
                 | stat.S_IROTH | stat.S_IXOTH)


class PushToCachePipeline(Pipeline):
    """Class for the pushtocache pipeline"""

    name = 'pushtocache'

    def __init__(self, workspace, filters, spack_cache_path=None):
        super().__init__(workspace, filters)
        self.action_string = 'Pushing to Spack Cache'
        self.spack_cache_path = spack_cache_path

    def _prepare(self):
        super()._prepare()
        self.workspace.spack_cache_path = self.spack_cache_path

    def _complete(self):
        logger.msg(f'Pushed envs to spack cache {self.spack_cache_path}')


class ExecutePipeline(Pipeline):
    """class for the `execute` (`on`) pipeline"""

    name = 'execute'

    def __init__(self, workspace, filters, executor='{batch_submit}',
                 suppress_per_experiment_prints=True, suppress_run_header=False):
        super().__init__(workspace, filters)
        self.action_string = 'Executing'
        self.require_inventory = True
        self.executor = executor
        self.suppress_per_experiment_prints = suppress_per_experiment_prints
        self.suppress_run_header = suppress_run_header

    def _execute(self):
        super()._execute()

        if not self.suppress_run_header:
            logger.all_msg('Running executors...')

        for exp, app_inst, idx in self._experiment_set.filtered_experiments(self.filters):
            if app_inst.is_template:
                logger.debug(f'{app_inst.name} is a template. Skipping execution.')
                continue
            if app_inst.repeats.is_repeat_base:
                logger.debug(f'{app_inst.name} is a repeat base. Skipping execution.')
                continue

            app_inst.add_expand_vars(self.workspace)
            exec_str = app_inst.expander.expand_var(self.executor)
            exec_parts = shlex.split(exec_str)
            exec_name = exec_parts[0]
            exec_args = exec_parts[1:]

            executor = Executable(exec_name)
            executor(*exec_args)


pipelines = Enum('pipelines',
                 [AnalyzePipeline.name, ArchivePipeline.name, MirrorPipeline.name,
                  SetupPipeline.name, PushToCachePipeline.name, ExecutePipeline.name]
                 )

_pipeline_map = {
    pipelines.analyze: AnalyzePipeline,
    pipelines.archive: ArchivePipeline,
    pipelines.mirror: MirrorPipeline,
    pipelines.setup: SetupPipeline,
    pipelines.pushtocache: PushToCachePipeline,
    pipelines.execute: ExecutePipeline
}


def pipeline_class(name):
    """Factory for determining a pipeline class from its name"""

    if name not in _pipeline_map.keys():
        logger.die(
            f'Pipeline {name} is not valid.\n'
            f'Valid pipelines are {_pipeline_map.keys()}'
        )

    return _pipeline_map[name]
