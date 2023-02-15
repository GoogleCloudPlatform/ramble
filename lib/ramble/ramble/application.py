# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for application definitions"""

import os
import stat
import re
import six
import textwrap
import string
import shutil

import llnl.util.filesystem as fs
import llnl.util.tty as tty
from llnl.util.tty.colify import colified

import spack.util.executable
import spack.util.spack_json
import spack.util.environment
import spack.util.compression

import ramble.config
import ramble.stage
import ramble.mirror
import ramble.fetch_strategy

from ramble.language.application_language import ApplicationMeta
from ramble.error import RambleError


header_color = '@*b'
level1_color = '@*g'
plain_format = '@.'


def section_title(s):
    return header_color + s + plain_format


def subsection_title(s):
    return level1_color + s + plain_format


class ApplicationBase(object, metaclass=ApplicationMeta):
    name = None
    uses_spack = False

    def __init__(self, file_path):
        super().__init__()

        self._setup_phases = []
        self._analyze_phases = []
        self._archive_phases = ['archive_experiments']
        self._mirror_phases = ['mirror_inputs']

        self._file_path = file_path

        self.application_class = 'ApplicationBase'

        self._verbosity = 'short'

    def _long_print(self):
        out_str = []
        out_str.append('%s\n' % section_title('Application: '))
        out_str.append('%s\n' % self.name)
        out_str.append('\n')

        out_str.append('%s\n' % section_title('Description:'))
        if self.__doc__:
            out_str.append('\t%s\n' % self.__doc__)
        else:
            out_str.append('\tNone\n')

        if hasattr(self, 'tags'):
            out_str.append('\n')
            out_str.append('%s\n' % section_title('Tags:'))
            out_str.append(colified(self.tags, tty=True))
            out_str.append('\n')

        if hasattr(self, '_setup_phases'):
            out_str.append('\n')
            out_str.append('%s\n' % section_title('Setup Pipeline Phases:'))
            out_str.append(colified(self._setup_phases, tty=True))

        if hasattr(self, '_analyze_phases'):
            out_str.append('\n')
            out_str.append('%s\n' % section_title('Analyze Pipeline Phases:'))
            out_str.append(colified(self._analyze_phases, tty=True))

        if hasattr(self, 'workloads'):
            out_str.append('\n')
            out_str.append(section_title('Workloads:\n'))
            out_str.append(colified(self.workloads.keys(), tty=True))
            out_str.append('\n')

            for workload in self.workloads.keys():
                if workload in self.workload_variables:
                    title = '%s variables:\n' % workload
                    out_str.append(section_title(title))
                    workload_vars = self.workload_variables[workload]
                    for var in workload_vars:
                        var_str = '\t%s\n' % var
                        out_str.append(subsection_title(var_str))

                        var_str = '\t\tDescription: ' + \
                            workload_vars[var]['description'] + '\n'
                        out_str.append(var_str)

                        var_str = '\t\tDefault: ' + \
                            workload_vars[var]['default'] + '\n'
                        out_str.append(var_str)

                        if 'values' in workload_vars[var].keys():
                            var_str = '\t\tSuggested Values: ' + \
                                str(workload_vars[var]['values']) + '\n'
                            out_str.append(var_str)

                    out_str.append('\n')

        return out_str

    def get_pipeline_phases(self, pipeline):
        phases = []
        if hasattr(self, '_%s_phases' % pipeline):
            phases = getattr(self, '_%s_phases' % pipeline).copy()
        return phases

    def _short_print(self):
        return [self.name]

    def __str__(self):
        if self._verbosity == 'long':
            return ''.join(self._long_print())
        elif self._verbosity == 'short':
            return ''.join(self._short_print())
        return self.name

    def format_doc(self, **kwargs):
        """Wrap doc string at 72 characters and format nicely"""
        indent = kwargs.get('indent', 0)

        if not self.__doc__:
            return ""

        doc = re.sub(r'\s+', ' ', self.__doc__)
        lines = textwrap.wrap(doc, 72)
        results = six.StringIO()
        for line in lines:
            results.write((" " * indent) + line + "\n")
        return results.getvalue()

    # Phase execution helpers
    def run_phase(self, phase, workspace, expander):
        """Run a phase, by getting it's function pointer"""
        if hasattr(self, '_%s' % phase):
            tty.msg('    Executing phase ' + phase)
            self._add_expand_vars(expander)
            phase_func = getattr(self, '_%s' % phase)
            phase_func(workspace, expander)

    def _get_env_set_commands(self, var_conf, var_set, shell='sh'):
        env_mods = spack.util.environment.EnvironmentModifications()
        for var, val in var_conf.items():
            var_set.add(var)
            env_mods.set(var, val)

        env_cmds_arr = env_mods.shell_modifications(shell=shell, explicit=True)

        return (env_cmds_arr.split('\n'), var_set)

    def _get_env_unset_commands(self, var_conf, var_set, shell='sh'):
        env_mods = spack.util.environment.EnvironmentModifications()
        for var in var_conf:
            if var in var_set:
                var_set.remove(var)
            env_mods.unset(var)

        env_cmds_arr = env_mods.shell_modifications(shell=shell, explicit=True)

        return (env_cmds_arr.split('\n'), var_set)

    def _get_env_append_commands(self, var_conf, var_set, shell='sh'):
        env_mods = spack.util.environment.EnvironmentModifications()

        append_funcs = {
            'vars': env_mods.append_flags,
            'paths': env_mods.append_path,
        }

        var_set_orig = var_set.copy()

        for append_group in var_conf:
            sep = ' '
            if 'var-separator' in append_group:
                sep = append_group['var-separator']

            for group in append_funcs.keys():
                if group in append_group.keys():
                    for var, val in append_group[group].items():
                        if var not in var_set:
                            env_mods.set(var, '${%s}' % var)
                            var_set.add(var)
                        append_funcs[group](var, val, sep=sep)

        env_cmds_arr = env_mods.shell_modifications(shell=shell, explicit=True)

        return (env_cmds_arr.split('\n'), var_set_orig)

    def _get_env_prepend_commands(self, var_conf, var_set, shell='sh'):
        env_mods = spack.util.environment.EnvironmentModifications()

        prepend_funcs = {
            'paths': env_mods.prepend_path,
        }

        var_set_orig = var_set.copy()

        for prepend_group in var_conf:
            for group in prepend_group.keys():
                for var, val in prepend_group[group].items():
                    if var not in var_set:
                        env_mods.set(var, '${%s}' % var)
                        var_set.add(var)
                    prepend_funcs[group](var, val)

        env_cmds_arr = env_mods.shell_modifications(shell=shell, explicit=True)

        return (env_cmds_arr.split('\n'), var_set_orig)

    def _add_expand_vars(self, expander):
        executables = self.workloads[expander.workload_name]['executables']
        inputs = self.workloads[expander.workload_name]['inputs']

        for input_file in inputs:
            input_conf = self.inputs[input_file]
            input_path = \
                os.path.join(expander.get_var('application_input_dir'),
                             input_conf['target_dir'])
            expander.set_var(input_file, input_path, 'experiment')

        # Set default experiment variables, if they haven't been set already
        if expander.workload_name in self.workload_variables:
            current_expansions = expander.get_expansion_dict()
            wl_vars = self.workload_variables[expander.workload_name]

            for var, conf in wl_vars.items():
                if var not in current_expansions:
                    expander.set_var(var, conf['default'], 'experiment')

        command = []

        # ensure license variables are set / modified
        # Process one scope at a time, to ensure
        # highest-precendence scopes are processed last
        config_scopes = ramble.config.scopes()
        shell = ramble.config.get('config:shell')
        var_set = set()

        action_funcs = {
            'set': self._get_env_set_commands,
            'unset': self._get_env_unset_commands,
            'append': self._get_env_append_commands,
            'prepend': self._get_env_prepend_commands
        }

        for scope in config_scopes:
            license_conf = ramble.config.config.get_config('licenses',
                                                           scope=scope)
            if license_conf:
                app_licenses = license_conf[self.name] if self.name \
                    in license_conf else {}

                for action, conf in app_licenses.items():
                    (env_cmds, var_set) = action_funcs[action](conf,
                                                               var_set,
                                                               shell=shell)

                    for cmd in env_cmds:
                        if cmd:
                            command.append(cmd)

        # Process environment variable actions
        for env_var_set in expander.all_env_var_sets():
            for action, conf in env_var_set.items():
                (env_cmds, _) = action_funcs[action](conf,
                                                     set(),
                                                     shell=shell)

                for cmd in env_cmds:
                    if cmd:
                        command.append(cmd)

        # ensure all log files are purged and set up
        logs = set()
        for executable in executables:
            command_config = self.executables[executable]
            if command_config['redirect']:
                logs.add(expander.expand_var(command_config['redirect']))

        for log in logs:
            command.append('rm -f "%s"' % log)
            command.append('touch "%s"' % log)

        for executable in executables:
            expander.set_var('executable_name', executable)
            exec_vars = {}
            command_config = self.executables[executable]

            if command_config['mpi']:
                exec_vars['mpi_command'] = \
                    expander.expand_var('{mpi_command} ')
            else:
                exec_vars['mpi_command'] = ''

            if command_config['redirect']:
                out_log = expander.expand_var(command_config['redirect'])
                exec_vars['redirect'] = ' >> "%s"' % out_log
            else:
                exec_vars['redirect'] = ''

            if isinstance(command_config['template'], list):
                for part in command_config['template']:
                    command_part = '{mpi_command}%s{redirect}' % \
                        part
                    command.append(expander.expand_var(command_part,
                                                       exec_vars))
            elif isinstance(command_config['template'],
                            six.string_types):
                command_part = '{mpi_command}%s{redirect}' % \
                    command_config['template']
                command.append(expander.expand_var(command_part,
                                                   exec_vars))
            else:
                app_err = 'Unsupported template type in executable '
                app_err += '%s' % executable
                raise ApplicationError(app_err)

            expander.remove_var('executable_name')

        expander.set_var('command', '\n'.join(command), 'experiment')

        expander.set_var('spack_setup', '', 'experiment')

    def _inputs_and_fetchers(self, workload=None):
        """Extract all inputs for a given workload

        Take a workload name and extract all inputs for the workload.
        If the workload is set to None, extract all inputs for all workloads.
        """

        workload_names = [workload] if workload else self.workloads.keys()

        inputs = {}
        for workload_name in workload_names:
            workload = self.workloads[workload_name]

            for input_file in workload['inputs']:
                input_conf = self.inputs[input_file]

                fetcher = ramble.fetch_strategy.URLFetchStrategy(**input_conf)

                file_name = os.path.basename(input_conf['url'])
                if not fetcher.extension:
                    fetcher.extension = spack.util.compression.extension(file_name)

                file_name = file_name.replace(f'.{fetcher.extension}', '')

                namespace = f'{self.name}.{workload_name}'

                inputs[file_name] = {'fetcher': fetcher,
                                     'namespace': namespace,
                                     'target_dir': input_conf['target_dir'],
                                     'extension': fetcher.extension,
                                     'input_name': input_file}
        return inputs

    def _mirror_inputs(self, workspace, expander):
        for input_file, input_conf in self._inputs_and_fetchers(expander.workload_name).items():
            mirror_paths = ramble.mirror.mirror_archive_paths(
                input_conf['fetcher'], os.path.join(self.name, input_file))
            fetch_dir = os.path.join(workspace._input_mirror_path, self.name)
            fs.mkdirp(fetch_dir)
            stage = ramble.stage.InputStage(input_conf['fetcher'], name=input_conf['namespace'],
                                            path=fetch_dir, mirror_paths=mirror_paths, lock=False)

            stage.cache_mirror(workspace._input_mirror_cache, workspace._input_mirror_stats)

    def _get_inputs(self, workspace, expander):
        workload_namespace = '%s.%s' % (expander.application_name,
                                        expander.workload_name)

        for input_file, input_conf in self._inputs_and_fetchers(expander.workload_name).items():
            if not workspace.dry_run:
                mirror_paths = ramble.mirror.mirror_archive_paths(
                    input_conf['fetcher'], os.path.join(self.name, input_file))

                with ramble.stage.InputStage(input_conf['fetcher'], name=workload_namespace,
                                             path=expander.application_input_dir,
                                             mirror_paths=mirror_paths) \
                        as stage:
                    stage.set_subdir(expander.expand_var(input_conf['target_dir']))
                    stage.fetch()
                    if input_conf['fetcher'].digest:
                        stage.check()
                    stage.cache_local()
                    if input_conf['expand']:
                        try:
                            stage.expand_archive()
                        except spack.util.executable.ProcessError:
                            pass
            else:
                tty.msg('DRY-RUN: Would download %s' % input_conf['fetcher'].url)

    def _make_experiments(self, workspace, expander):
        experiment_run_dir = expander.experiment_run_dir
        fs.mkdirp(experiment_run_dir)

        for template_name, template_val in workspace.all_templates():
            expand_path = os.path.join(experiment_run_dir, template_name)
            expander.set_var(template_name, expand_path, 'experiment')

        for template_name, template_val in workspace.all_templates():
            expand_path = os.path.join(experiment_run_dir, template_name)

            with open(expand_path, 'w+') as f:
                f.write(expander.expand_var(template_val))
            os.chmod(expand_path, stat.S_IRWXU | stat.S_IRWXG
                     | stat.S_IROTH | stat.S_IXOTH)

        experiment_script = expander.get_var('experiments_file')
        experiment_script.write(expander.expand_var('{batch_submit}\n'))

        for template_name, template_val in workspace.all_templates():
            expander.remove_var(template_name)

    def _archive_experiments(self, workspace, expander):
        import glob
        experiment_run_dir = expander.experiment_run_dir
        ws_archive_dir = workspace.latest_archive_path

        archive_experiment_dir = experiment_run_dir.replace(workspace.root,
                                                            ws_archive_dir)

        fs.mkdirp(archive_experiment_dir)

        # Copy all of the templates to the archive directory
        for template_name, _ in workspace.all_templates():
            src = os.path.join(experiment_run_dir, template_name)
            if os.path.exists(src):
                shutil.copy(src, archive_experiment_dir)

        # Copy all figure of merit files
        criteria_list = workspace.success_list
        analysis_files, _, _ = self._analysis_dicts(expander, criteria_list)
        for file, file_conf in analysis_files.items():
            if os.path.exists(file):
                shutil.copy(file, archive_experiment_dir)

        # Copy all archive patterns
        for pattern in self.archive_patterns.keys():
            exp_pattern = expander.expand_var(pattern)
            for file in glob.glob(exp_pattern):
                shutil.copy(file, archive_experiment_dir)

    def _analyze_experiments(self, workspace, expander):
        """Perform experiment analysis.

        This method will build up the fom_values dictionary. Its structure is:

        fom_values[context][fom]

        A fom can show up in any number of explicit contexts (including zero).
        If the number of explicit contexts is zero, the fom is associated with
        the default '(null)' context.

        Success is determined at analysis time as well. This happens by checking if:
         - At least one FOM is extracted
         AND
         - Any defined success criteria pass

        Success criteria are defined within the application.py, but can also be
        injected in a workspace config.
        """

        def format_context(context_match, context_format):

            keywords = {}
            if isinstance(context_format, six.string_types):
                for group in string.Formatter().parse(context_format):
                    if group[1]:
                        keywords[group[1]] = context_match[group[1]]

            context_string = context_format.replace('{', '').replace('}', '') \
                + ' = ' + context_format.format(**keywords)
            return context_string

        fom_values = {}

        criteria_list = workspace.success_list

        files, contexts, foms = self._analysis_dicts(expander, criteria_list)

        # Iterate over files. We already know they exist
        for file, file_conf in files.items():

            # Start with no active contexts in a file.
            active_contexts = {}
            tty.debug('Reading log file: %s' % file)

            with open(file, 'r') as f:
                for line in f.readlines():

                    for criteria in file_conf['success_criteria']:
                        tty.debug('Looking for criteria %s' % criteria)
                        criteria_obj = criteria_list.find_criteria(criteria)
                        if criteria_obj.matches(line):
                            criteria_obj.mark_found()

                    for context in file_conf['contexts']:
                        context_conf = contexts[context]
                        context_match = context_conf['regex'].match(line)

                        if context_match:
                            context_name = \
                                format_context(context_match,
                                               context_conf['format'])
                            tty.debug('Line was: %s' % line)
                            tty.debug(' Context match %s -- %s' %
                                      (context, context_name))

                            active_contexts[context] = context_name
                            fom_values[context_name] = {}

                    for fom in file_conf['foms']:
                        fom_conf = foms[fom]
                        fom_match = fom_conf['regex'].match(line)

                        if fom_match and \
                                (fom_conf['group'] in
                                 fom_conf['regex'].groupindex):
                            tty.debug(' --- Matched fom %s' % fom)
                            fom_contexts = []
                            if fom_conf['contexts']:
                                for context in fom_conf['contexts']:
                                    context_name = active_contexts[context] \
                                        if context in active_contexts \
                                        else 'null'
                                    fom_contexts.append(context_name)
                            else:
                                fom_contexts.append('null')

                            for context in fom_contexts:
                                if context not in fom_values:
                                    fom_values[context] = {}
                                fom_val = fom_match.group(fom_conf['group'])
                                fom_values[context][fom] = {
                                    'value': fom_val,
                                    'units': fom_conf['units']
                                }

        results = {}
        exp_ns = expander.experiment_namespace
        results[exp_ns] = {}

        success = True if fom_values else False
        success = success and criteria_list.passed()

        tty.debug('fom_vals = %s' % fom_values)
        if success:
            results[exp_ns]['RAMBLE_STATUS'] = 'SUCCESS'
            results[exp_ns]['RAMBLE_VARIABLES'] = expander.all_vars()
            results[exp_ns]['CONTEXTS'] = {}

            for context, foms in fom_values.items():
                results[exp_ns]['CONTEXTS'][context] = foms.copy()

        else:
            results[exp_ns]['RAMBLE_STATUS'] = 'FAILED'

        workspace.append_result(results)

    def _new_file_dict(self):
        return {
            'success_criteria': [],
            'contexts': [],
            'foms': []
        }

    def _analysis_dicts(self, expander, criteria_list):
        """Extract files that need to be analyzed.

        Process figures_of_merit, and return the manipulated dictionaries
        to allow them to be extracted.

        Additionally, ensure the success criteria list is complete.

        Returns:
           - files (dict): All files that need to be processed
           - contexts (dict): Any contexts that have been defined
           - foms (dict): All figures of merit that need to be extracted
        """

        files = {}
        contexts = {}
        foms = {}

        # Add the application defined criteria
        criteria_list.flush_scope('application_definition')
        for criteria, conf in self.success_criteria.items():
            if conf['mode'] == 'string':
                criteria_list.add_criteria('application_definition', criteria,
                                           conf['mode'], re.compile(conf['match']),
                                           conf['file'])

        # Extract file paths for all criteria
        for criteria in criteria_list.all_criteria():
            log_path = expander.expand_var(criteria.file)
            if log_path not in files and os.path.exists(log_path):
                files[log_path] = self._new_file_dict()

            if log_path in files:
                files[log_path]['success_criteria'].append(criteria.name)

        # Remap fom / context / file data
        # Could push this into the language features in the future
        for fom, conf in self.figures_of_merit.items():
            log_path = expander.expand_var(conf['log_file'])
            if log_path not in files and os.path.exists(log_path):
                files[log_path] = self._new_file_dict()

            if log_path in files:
                tty.debug('Log = %s' % log_path)
                tty.debug('Conf = %s' % conf)
                if conf['contexts']:
                    files[log_path]['contexts'].extend(conf['contexts'])
                files[log_path]['foms'].append(fom)

            foms[fom] = {
                'regex': re.compile(r'%s' % conf['regex']),
                'contexts': [],
                'group': conf['group_name'],
                'units': conf['units']
            }
            if conf['contexts']:
                foms[fom]['contexts'].extend(conf['contexts'])

            if conf['contexts']:
                for context in conf['contexts']:
                    regex_str = \
                        self.figure_of_merit_contexts[context]['regex']
                    format_str = \
                        self.figure_of_merit_contexts[context]['output_format']
                    contexts[context] = {
                        'regex': re.compile(r'%s' % regex_str),
                        'format': format_str
                    }
        return files, contexts, foms


class ApplicationError(RambleError):
    """
    Exception that is raised by applications
    """
