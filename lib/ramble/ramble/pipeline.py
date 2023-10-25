# Copyright 2022-2023 Google LLC
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

import llnl.util.filesystem as fs
import llnl.util.tty as tty
from llnl.util.tty.color import cprint

import ramble.config
import ramble.experiment_set
import ramble.software_environments
import ramble.util.hashing
import ramble.util.logger
import ramble.fetch_strategy
import ramble.stage
import ramble.workspace

import ramble.experimental.uploader

from ramble.namespace import namespace

import spack.util.spack_json as sjson
from spack.util.executable import which

if not ramble.config.get('config:disable_progress_bar', False):
    try:
        import tqdm
    except ModuleNotFoundError:
        ramble.util.logger.logger.die(
            'Module `tqdm` is not found. Ensure requirements.txt are installed.'
        )


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
        self.simlink_log(self.log_dir, self.log_dir_latest)
        self.simlink_log(self.log_path, self.log_path_latest)

        self._experiment_set = workspace.build_experiment_set()
        self._software_environments = ramble.software_environments.SoftwareEnvironments(workspace)
        self.workspace.software_environments = self._software_environments

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
                if not app_inst.is_template:
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
            ramble.util.logger.logger.die(error_message)

    def _prepare(self):
        """Perform preparation for pipeline execution"""
        pass

    def _execute(self):
        """Hook for executing the pipeline"""
        num_exps = self._experiment_set.num_filtered_experiments(self.filters)
        count = 1
        for exp, app_inst, idx in self._experiment_set.filtered_experiments(self.filters):
            exp_log_path = app_inst.experiment_log_file(self.log_dir)

            ramble.util.logger.logger.all_msg(f'Experiment {idx} ({count}/{num_exps}):')
            ramble.util.logger.logger.all_msg(f'    name: {exp}')
            ramble.util.logger.logger.all_msg(
                f'    log file: {exp_log_path}'
            )

            ramble.util.logger.logger.add_log(exp_log_path)

            phase_list = app_inst.get_pipeline_phases(self.name, self.filters.phases)

            disable_progress = ramble.config.get('config:disable_progress_bar', False)
            if not disable_progress:
                progress = tqdm.tqdm(total=len(phase_list),
                                     leave=True,
                                     ascii=' >=',
                                     bar_format='{l_bar}{bar}| Elapsed (s): {elapsed_s}')
            for phase_idx, phase in enumerate(phase_list):
                if not disable_progress:
                    progress.set_description(
                        f'Processing phase {phase} ({phase_idx}/{len(phase_list)})'
                    )
                app_inst.run_phase(phase, self.workspace)
                if not disable_progress:
                    progress.update()
            if not disable_progress:
                progress.set_description('Experiment complete')
                progress.close()

            ramble.util.logger.logger.remove_log()
            ramble.util.logger.logger.all_msg(
                f'  Returning to log file: {ramble.util.logger.logger.active_log()}'
            )
            count += 1

    def _complete(self):
        """Hook for performing pipeline actions after execution is complete"""
        pass

    def run(self):
        """Run the full pipeline"""
        ramble.util.logger.logger.all_msg('Streaming details to log:')
        ramble.util.logger.logger.all_msg(f'  {self.log_path}')
        if self.workspace.dry_run:
            cprint('@*g{      -- DRY-RUN -- DRY-RUN -- DRY-RUN -- DRY-RUN -- DRY-RUN --}')

        experiment_count = self._experiment_set.num_filtered_experiments(self.filters)
        experiment_total = self._experiment_set.num_experiments()
        ramble.util.logger.logger.all_msg(
            f'  {self.action_string} {experiment_count} out of '
            f'{experiment_total} experiments:'
        )

        ramble.util.logger.logger.add_log(self.log_path)
        self._validate()
        self._prepare()
        self._execute()
        self._complete()
        ramble.util.logger.logger.remove_log()

    def simlink_log(self, base, link):
        """
        Create simlink of log file to give a known and predictable path
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
        super()._construct_hash()
        super()._prepare()

    def _complete(self):
        self.workspace.dump_results(output_formats=self.output_formats)

        if self.upload_results:
            ramble.experimental.uploader.upload_results(self.workspace.results)


class ArchivePipeline(Pipeline):
    """Class for the archive pipeline"""

    name = 'archive'

    def __init__(self, workspace, filters, create_tar=False, upload_url=None):
        super().__init__(workspace, filters)
        self.action_string = 'Archiving'
        self.create_tar = create_tar
        self.upload_url = upload_url
        self.archive_name = None

    def _prepare(self):
        import glob
        super()._construct_hash()
        super()._prepare()

        date_str = self.workspace.date_string()

        # Use the basename from the path as the name of the workspace.
        # If we use `self.workspace.name` we get the path multiple times.
        self.archive_name = '%s-archive-%s' % (os.path.basename(self.workspace.path), date_str)

        archive_path = os.path.join(self.workspace.archive_dir, self.archive_name)
        fs.mkdirp(archive_path)

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

        # Copy current software spack.yamls
        archive_software = os.path.join(self.workspace.latest_archive_path,
                                        ramble.workspace.workspace_software_path)
        fs.mkdirp(archive_software)
        for file in glob.glob(os.path.join(self.workspace.software_dir, '*', 'spack.yaml')):
            dest = file.replace(self.workspace.software_dir, archive_software)
            fs.mkdirp(os.path.dirname(dest))
            shutil.copyfile(file, dest)

    def _complete(self):
        if self.create_tar:
            tar = which('tar', required=True)
            with py.path.local(self.workspace.archive_dir).as_cwd():
                tar('-czf', self.archive_name + '.tar.gz', self.archive_name)

            archive_url = self.upload_url if self.upload_url else \
                ramble.config.get('config:archive_url')
            archive_url = archive_url.rstrip('/') if archive_url else None

            ramble.util.logger.logger.debug(f'Archive url: {archive_url}')

            if archive_url:
                tar_path = self.workspace.latest_archive_path + '.tar.gz'
                remote_tar_path = archive_url + '/' + self.workspace.latest_archive + '.tar.gz'
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
        ramble.util.logger.logger.msg(
            f"Successfully {verb} spack software in {self.workspace.mirror_path}",
            "Archive stats:",
            "  %-4d already present"  % len(self.workspace.software_mirror_stats.present),
            "  %-4d added"            % len(self.workspace.software_mirror_stats.new),
            "  %-4d failed to fetch." % len(self.workspace.software_mirror_stats.errors))

        ramble.util.logger.logger.msg(
            f"Successfully {verb} inputs in {self.workspace.mirror_path}",
            "Archive stats:",
            "  %-4d already present"  % len(self.workspace.input_mirror_stats.present),
            "  %-4d added"            % len(self.workspace.input_mirror_stats.new),
            "  %-4d failed to fetch." % len(self.workspace.input_mirror_stats.errors))

        if self.workspace.input_mirror_stats.errors:
            ramble.util.logger.logger.error("Failed downloads:")
            tty.colify((s.cformat("{name}") for s in
                       list(self.workspace.input_mirror_stats.errors)),
                       output=ramble.util.logger.logger.active_stream())
            ramble.util.logger.logger.die('Mirroring has errors.')


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
        experiment_file.write('#!/bin/sh\n')
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
        ramble.util.logger.logger.msg(f'Pushed envs to spack cache {self.spack_cache_path}')


pipelines = Enum('pipelines',
                 [AnalyzePipeline.name, ArchivePipeline.name, MirrorPipeline.name,
                  SetupPipeline.name, PushToCachePipeline.name]
                 )

_pipeline_map = {
    pipelines.analyze: AnalyzePipeline,
    pipelines.archive: ArchivePipeline,
    pipelines.mirror: MirrorPipeline,
    pipelines.setup: SetupPipeline,
    pipelines.pushtocache: PushToCachePipeline
}


def pipeline_class(name):
    """Factory for determining a pipeline class from its name"""

    if name not in _pipeline_map.keys():
        ramble.util.logger.logger.die(
            f'Pipeline {name} is not valid.\n'
            f'Valid pipelines are {_pipeline_map.keys()}'
        )

    return _pipeline_map[name]
