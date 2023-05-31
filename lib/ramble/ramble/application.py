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
import ramble.expander

from ramble.keywords import keywords
from ramble.workspace import namespace

from ramble.schema.types import OUTPUT_CAPTURE
from ramble.language.application_language import ApplicationMeta, register_builtin
from ramble.error import RambleError


header_color = '@*b'
level1_color = '@*g'
level2_color = '@*r'
plain_format = '@.'


def section_title(s):
    return header_color + s + plain_format


def subsection_title(s):
    return level1_color + s + plain_format


def nested_2_color(s):
    return level2_color + s + plain_format


class ApplicationBase(object, metaclass=ApplicationMeta):
    name = None
    uses_spack = False
    _exec_prefix_builtin = 'builtin::'
    _builtin_required_key = 'required'
    _workload_exec_key = 'executables'

    def __init__(self, file_path):
        super().__init__()

        self._setup_phases = []
        self._analyze_phases = []
        self._archive_phases = ['archive_experiments']
        self._mirror_phases = ['mirror_inputs']

        self._vars_are_expanded = False
        self.expander = None
        self.variables = None
        self.experiment_set = None
        self.internals = None
        self.is_template = False
        self.chained_experiments = None
        self.chain_order = []
        self.chain_prepend = []
        self.chain_append = []
        self.chain_commands = {}
        self._env_variable_sets = None

        self._file_path = file_path

        self.application_class = 'ApplicationBase'

        self._verbosity = 'short'
        self._inject_required_builtins()

    def copy(self):
        """Deep copy an application instance"""
        new_copy = type(self)(self._file_path)

        new_copy.set_env_variable_sets(self._env_variable_sets.copy())
        new_copy.set_variables(self.variables.copy(), self.experiment_set)
        new_copy.set_internals(self.internals.copy())
        new_copy.set_template(False)
        new_copy.set_chained_experiments(None)

        return new_copy

    def _inject_required_builtins(self):
        required_builtins = []
        for builtin, blt_conf in self.builtins.items():
            if blt_conf[self._builtin_required_key]:
                required_builtins.append(builtin)

        for workload, wl_conf in self.workloads.items():
            if self._workload_exec_key in wl_conf:
                # Insert in reverse order, to make sure they are correctly ordered.
                for builtin in reversed(required_builtins):
                    if builtin not in wl_conf[self._workload_exec_key]:
                        wl_conf[self._workload_exec_key].insert(0, builtin)

    def _long_print(self):
        out_str = []
        out_str.append(section_title('Application: ') + f'{self.name}\n')
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
            for wl_name, wl_conf in self.workloads.items():
                out_str.append(section_title('Workload:') + f' {wl_name}\n')
                out_str.append('\t' + subsection_title('Executables: ') +
                               f'{wl_conf["executables"]}\n')
                out_str.append('\t' + subsection_title('Inputs: ') +
                               f'{wl_conf["inputs"]}\n')

                if wl_name in self.workload_variables:
                    out_str.append('\t' + subsection_title('Variables:') + '\n')
                    for var, conf in self.workload_variables[wl_name].items():
                        indent = '\t\t'

                        out_str.append(nested_2_color(f'{indent}{var}:\n'))
                        out_str.append(f'{indent}\tDescription: {conf["description"]}\n')
                        out_str.append(f'{indent}\tDefault: {conf["default"]}\n')
                        if 'values' in conf:
                            out_str.append(f'{indent}\tSuggested Values: {conf["values"]}\n')

            out_str.append('\n')

        if hasattr(self, 'builtins'):
            out_str.append(section_title('Builtin Executables:\n'))
            out_str.append('\t' + colified(self.builtins.keys(), tty=True) + '\n')
        return out_str

    def set_env_variable_sets(self, env_variable_sets):
        """Set internal reference to environment variable sets"""

        self._env_variable_sets = env_variable_sets.copy()

    def set_variables(self, variables, experiment_set):
        """Set internal reference to variables

        Also, create an application specific expander class.
        """

        self.variables = variables
        self.experiment_set = experiment_set
        self.expander = ramble.expander.Expander(self.variables, self.experiment_set)

    def set_internals(self, internals):
        """Set internal refernece to application internals
        """

        self.internals = internals

    def set_template(self, is_template):
        """Set if this instance is a template or not"""
        self.is_template = is_template

    def set_chained_experiments(self, chained_experiments):
        """Set chained experiments for this instance"""
        self.chained_experiments = None
        if chained_experiments:
            self.chained_experiments = chained_experiments.copy()

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
    def run_phase(self, phase, workspace):
        """Run a phase, by getting its function pointer"""
        self.add_expand_vars(workspace)
        if self.is_template:
            tty.debug(f'{self.name} is a template. Skipping phases')
            return

        if hasattr(self, '_%s' % phase):
            tty.msg('    Executing phase ' + phase)
            phase_func = getattr(self, '_%s' % phase)
            phase_func(workspace)

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

    def create_experiment_chain(self, workspace):
        """Create the necessary chained experiments for this instance

        This method determines which experiments need to be chained, grabs the
        base instance from the experiment set, creates a copy of it (with a
        unique name), injects the copy back into the experiment set,
        and builds an internal mapping from unique name to the chaining definition.
        """

        if not self.chained_experiments or self.is_template:
            return

        # Build initial stack. Uses a reversal of the current instance's
        # chained experiments
        parent_namespace = self.expander.experiment_namespace
        classes_in_stack = set([self])
        chain_idx = 0
        chain_stack = []
        for exp in reversed(self.chained_experiments):
            for exp_name in self.experiment_set.search_primary_experiments(exp['name']):
                child_inst = self.experiment_set.get_experiment(exp_name)

                if child_inst in classes_in_stack:
                    raise ChainCycleDetectedError('Cycle detected in experiment chain:\n' +
                                                  f'    Primary experiment {parent_namespace}\n' +
                                                  f'    Chained expeirment name: {exp_name}\n' +
                                                  f'    Chain definition: {str(exp)}')
                chain_stack.append((exp_name, exp))

        parent_run_dir = self.expander.expand_var(
            self.expander.expansion_str(keywords.experiment_run_dir)
        )

        # Continue until the stack is empty
        while len(chain_stack) > 0:
            cur_exp_name = chain_stack[-1][0]
            cur_exp_def = chain_stack[-1][1]

            # Perform basic validation on the chained experiment definition
            if 'name' not in cur_exp_def:
                raise InvalidChainError('Invalid experiment chain defined:\n' +
                                        f'    Primary experiment {parent_namespace}\n' +
                                        f'    Chain definition: {str(exp)}\n' +
                                        '    "name" keyword must be defined')

            if 'order' in cur_exp_def:
                possible_orders = ['after_chain', 'after_root', 'before_chain', 'before_root']
                if cur_exp_def['order'] not in possible_orders:
                    raise InvalidChainError('Invalid experiment chain defined:\n' +
                                            f'    Primary experiment {parent_namespace}\n' +
                                            f'    Chain definition: {str(exp)}\n' +
                                            '    Optional keyword "order" must ' +
                                            f'be one of {str(possible_orders)}\n')

            if 'command' not in cur_exp_def.keys():
                raise InvalidChainError('Invalid experiment chain defined:\n' +
                                        f'    Primary experiment {parent_namespace}\n' +
                                        f'    Chain definition: {str(exp)}\n' +
                                        '    "command" keyword must be defined')

            if 'variables' in cur_exp_def:
                if not isinstance(cur_exp_def['variables'], dict):
                    raise InvalidChainError('Invalid experiment chain defined:\n' +
                                            f'    Primary experiment {parent_namespace}\n' +
                                            f'    Chain definition: {str(exp)}\n' +
                                            '    Optional keyword "variables" ' +
                                            'must be a dictionary')

            base_inst = self.experiment_set.get_experiment(cur_exp_name)
            if base_inst in classes_in_stack:
                chain_stack.pop()
                classes_in_stack.remove(base_inst)

                order = 'after_root'
                if 'order' in cur_exp_def:
                    order = cur_exp_def['order']

                chained_name = f'{chain_idx}.{cur_exp_name}'
                new_name = f'{parent_namespace}.chain.{chained_name}'

                new_run_dir = os.path.join(parent_run_dir,
                                           namespace.chained_experiments, chained_name)

                if order == 'before_chain':
                    self.chain_prepend.insert(0, new_name)
                elif order == 'before_root':
                    self.chain_prepend.append(new_name)
                elif order == 'after_root':
                    self.chain_append.insert(0, new_name)
                elif order == 'after_chain':
                    self.chain_append.append(new_name)
                self.chain_commands[new_name] = cur_exp_def[keywords.command]

                # Skip editing the new instance if the base_inst doesn't work
                # This happens if the originating command is `workspace info`
                # The printing experiment set doesn't have access to all
                # of the experiment, so the base_inst command above
                # doesn't get an application instance.
                if base_inst:
                    new_inst = base_inst.copy()

                    if namespace.variables in cur_exp_def:
                        for var, val in cur_exp_def[namespace.variables].items():
                            new_inst.variables[var] = val

                    new_inst.expander._experiment_namespace = new_name
                    new_inst.variables[keywords.experiment_run_dir] = new_run_dir
                    new_inst.variables[keywords.experiment_name] = new_name

                    # Expand the chained experiment vars, so we can build the execution command
                    new_inst.add_expand_vars(workspace)
                    chain_cmd = new_inst.expander.expand_var(cur_exp_def[keywords.command])
                    self.chain_commands[new_name] = chain_cmd
                    cur_exp_def[keywords.command] = chain_cmd
                    self.experiment_set.add_chained_experiment(new_name, new_inst)

                chain_idx += 1
            else:
                # Avoid cycles, from children
                if base_inst in classes_in_stack:
                    chain_stack.pop()
                else:
                    if base_inst.chained_experiments:
                        for exp in reversed(base_inst.chained_experiments):
                            for exp_name in \
                                    self.experiment_set.search_primary_experiments(exp['name']):
                                child_inst = self.experiment_set.get_experiment(exp_name)
                                if child_inst in classes_in_stack:
                                    raise ChainCycleDetectedError('Cycle detected in ' +
                                                                  'experiment chain:\n' +
                                                                  '    Primary experiment ' +
                                                                  f'{parent_namespace}\n' +
                                                                  '    Chained expeirment name: ' +
                                                                  f'{cur_exp_name}\n' +
                                                                  '    Chain definition: ' +
                                                                  f'{str(cur_exp_def)}')

                                chain_stack.append((exp_name, exp))
                    classes_in_stack.add(base_inst)

        # Create the final chain order
        for exp in self.chain_prepend:
            self.chain_order.append(exp)
        self.chain_order.append(self.expander.experiment_namespace)
        for exp in self.chain_append:
            self.chain_order.append(exp)

        # Inject the chain order into the children experiments
        for exp in self.chain_prepend:
            exp_inst = self.experiment_set.get_experiment(exp)
            if exp_inst:
                exp_inst.chain_order = self.chain_order.copy()

        for exp in self.chain_append:
            exp_inst = self.experiment_set.get_experiment(exp)
            if exp_inst:
                exp_inst.chain_order = self.chain_order.copy()

    def add_expand_vars(self, workspace):
        """Add application specific expansion variables

        Applications require several variables to be defined to function properly.
        This method defines these variables, including:
        - command: set to the commands needed to execute the experiment
        - spack_setup: set to an empty string, so spack applications can override this
        """
        if self._vars_are_expanded:
            return

        executables = self.workloads[self.expander.workload_name]['executables']
        inputs = self.workloads[self.expander.workload_name]['inputs']

        # Use yaml defined executable order, if defined
        if namespace.executables in self.internals:
            executables = self.internals[namespace.executables]

        # Define custom executables
        if namespace.custom_executables in self.internals.keys():
            for name, conf in self.internals[namespace.custom_executables].items():

                output_capture = OUTPUT_CAPTURE.DEFAULT
                if 'output_capture' in conf:
                    output_capture = conf['output_capture']

                self.executables[name] = {
                    'template': conf['template'],
                    'mpi': conf['mpi'] if 'mpi' in conf else False,
                    'redirect': conf['redirect'] if 'redirect' in conf else '{log_file}',
                    'output_capture': output_capture
                }

        for input_file in inputs:
            input_conf = self.inputs[input_file]
            input_path = \
                os.path.join(self.expander.application_input_dir,
                             input_conf['target_dir'])
            self.variables[input_file] = input_path

        # Set default experiment variables, if they haven't been set already
        if self.expander.workload_name in self.workload_variables:
            wl_vars = self.workload_variables[self.expander.workload_name]

            for var, conf in wl_vars.items():
                if var not in self.variables.keys():
                    self.variables[var] = conf['default']

        command = []

        # Inject all prepended chained experiments
        for chained_exp in self.chain_prepend:
            command.append(self.chain_commands[chained_exp])

        # ensure all log files are purged and set up
        logs = set()
        builtin_regex = re.compile(r'%s(?P<func>.*)' % self._exec_prefix_builtin)
        for executable in executables:
            if not builtin_regex.match(executable):
                command_config = self.executables[executable]
                if command_config['redirect']:
                    logs.add(command_config['redirect'])

        for log in logs:
            command.append('rm -f "%s"' % log)
            command.append('touch "%s"' % log)

        for executable in executables:
            builtin_match = builtin_regex.match(executable)
            if builtin_match:
                # Process builtin executables

                # Get internal method:
                func_name = f'{builtin_match.group("func")}'
                func = getattr(self, func_name)
                command.extend(func())
            else:
                # Process directive defined executables
                self.variables['executable_name'] = executable
                exec_vars = {}
                command_config = self.executables[executable]

                if command_config['mpi']:
                    exec_vars['mpi_command'] = \
                        self.expander.expand_var('{mpi_command} ')
                else:
                    exec_vars['mpi_command'] = ''

                if command_config['redirect']:
                    out_log = self.expander.expand_var(command_config['redirect'])
                    output_operator = command_config['output_capture']
                    exec_vars['redirect'] = f' {output_operator} "{out_log}"'
                else:
                    exec_vars['redirect'] = ''

                if isinstance(command_config['template'], list):
                    for part in command_config['template']:
                        command_part = '{mpi_command}%s{redirect}' % \
                            part
                        command.append(self.expander.expand_var(command_part,
                                                                exec_vars))
                elif isinstance(command_config['template'],
                                six.string_types):
                    command_part = '{mpi_command}%s{redirect}' % \
                        command_config['template']
                    command.append(self.expander.expand_var(command_part,
                                                            exec_vars))
                else:
                    app_err = 'Unsupported template type in executable '
                    app_err += '%s' % executable
                    raise ApplicationError(app_err)

                del self.variables['executable_name']

        # Inject all appended chained experiments
        for chained_exp in self.chain_append:
            command.append(self.chain_commands[chained_exp])

        self.variables['command'] = '\n'.join(command)

        # TODO (dwj): Remove this after we validate that 'spack_setup' is not in templates.
        #             this is no longer needed, as spack was converted to builtins.
        self.variables['spack_setup'] = ''

        # Define variables for template paths
        for template_name, template_val in workspace.all_templates():
            expand_path = os.path.join(
                self.expander.expand_var(f'{{experiment_run_dir}}'),  # noqa: F541
                template_name)
            self.variables[template_name] = expand_path

        self._vars_are_expanded = True

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
                                     'input_name': input_file,
                                     'expand': input_conf['expand']
                                     }
        return inputs

    def _mirror_inputs(self, workspace):
        """Mirror application inputs

        Perform mirroring of inputs within this application class.
        """
        for input_file, input_conf in \
                self._inputs_and_fetchers(self.expander.workload_name).items():
            mirror_paths = ramble.mirror.mirror_archive_paths(
                input_conf['fetcher'], os.path.join(self.name, input_file))
            fetch_dir = os.path.join(workspace._input_mirror_path, self.name)
            fs.mkdirp(fetch_dir)
            stage = ramble.stage.InputStage(input_conf['fetcher'], name=input_conf['namespace'],
                                            path=fetch_dir, mirror_paths=mirror_paths, lock=False)

            stage.cache_mirror(workspace._input_mirror_cache, workspace._input_mirror_stats)

    def _get_inputs(self, workspace):
        """Download application inputs

        Download application inputs into the proper directory within the workspace.
        """
        workload_namespace = self.expander.workload_namespace

        for input_file, input_conf in \
                self._inputs_and_fetchers(self.expander.workload_name).items():
            if not workspace.dry_run:
                mirror_paths = ramble.mirror.mirror_archive_paths(
                    input_conf['fetcher'], os.path.join(self.name, input_file))

                with ramble.stage.InputStage(input_conf['fetcher'], name=workload_namespace,
                                             path=self.expander.application_input_dir,
                                             mirror_paths=mirror_paths) \
                        as stage:
                    stage.set_subdir(self.expander.expand_var(input_conf['target_dir']))
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

    def _make_experiments(self, workspace):
        """Create experiment directories

        Create the experiment this application encapsulates. This includes
        creating the experiment run directory, rendering the necessary
        templates, and injecting the experiment into the workspace all
        experiments file.
        """
        experiment_run_dir = self.expander.experiment_run_dir
        fs.mkdirp(experiment_run_dir)

        for template_name, template_val in workspace.all_templates():
            expand_path = os.path.join(experiment_run_dir, template_name)

            with open(expand_path, 'w+') as f:
                f.write(self.expander.expand_var(template_val))
            os.chmod(expand_path, stat.S_IRWXU | stat.S_IRWXG
                     | stat.S_IROTH | stat.S_IXOTH)

        experiment_script = workspace.experiments_script
        experiment_script.write(self.expander.expand_var('{batch_submit}\n'))

    def _archive_experiments(self, workspace):
        """Archive an experiment directory

        Perform the archiving action on an experiment.
        This includes capturing:
        - Rendered templates within the experiment directory
        - All files that contain a figure of merit or success criteria
        - Any files that match an archive pattern
        """
        import glob
        experiment_run_dir = self.expander.experiment_run_dir
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
        analysis_files, _, _ = self._analysis_dicts(criteria_list)
        for file, file_conf in analysis_files.items():
            if os.path.exists(file):
                shutil.copy(file, archive_experiment_dir)

        # Copy all archive patterns
        for pattern in self.archive_patterns.keys():
            exp_pattern = self.expander.expand_var(pattern)
            for file in glob.glob(exp_pattern):
                shutil.copy(file, archive_experiment_dir)

    def _analyze_experiments(self, workspace):
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

        files, contexts, foms = self._analysis_dicts(criteria_list)

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

        exp_ns = self.expander.experiment_namespace
        results = {'name': exp_ns}

        success = True if fom_values else False
        success = success and criteria_list.passed()

        tty.debug('fom_vals = %s' % fom_values)
        results['EXPERIMENT_CHAIN'] = self.chain_order.copy()
        if success:
            results['RAMBLE_STATUS'] = 'SUCCESS'
            results['RAMBLE_VARIABLES'] = {}
            results['RAMBLE_RAW_VARIABLES'] = {}
            for var, val in self.variables.items():
                results['RAMBLE_RAW_VARIABLES'][var] = val
                results['RAMBLE_VARIABLES'][var] = self.expander.expand_var(val)
            results['CONTEXTS'] = []

            for context, fom_map in fom_values.items():
                context_map = {'name': context, 'foms': []}

                for fom_name, fom in fom_map.items():
                    fom_copy = fom.copy()
                    fom_copy['name'] = fom_name
                    context_map['foms'].append(fom_copy)

                results['CONTEXTS'].append(context_map)

        else:
            results['RAMBLE_STATUS'] = 'FAILED'

        workspace.append_result(results)

    def _new_file_dict(self):
        """Create a dictonary to represent a new log file"""
        return {
            'success_criteria': [],
            'contexts': [],
            'foms': []
        }

    def _analysis_dicts(self, criteria_list):
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
            log_path = self.expander.expand_var(criteria.file)
            if log_path not in files and os.path.exists(log_path):
                files[log_path] = self._new_file_dict()

            if log_path in files:
                files[log_path]['success_criteria'].append(criteria.name)

        # Remap fom / context / file data
        # Could push this into the language features in the future
        for fom, conf in self.figures_of_merit.items():
            log_path = self.expander.expand_var(conf['log_file'])
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

    register_builtin('env_vars', required=True)

    def env_vars(self):
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
        for env_var_set in self._env_variable_sets:
            for action, conf in env_var_set.items():
                (env_cmds, _) = action_funcs[action](conf,
                                                     set(),
                                                     shell=shell)

                for cmd in env_cmds:
                    if cmd:
                        command.append(cmd)

        return command


class ApplicationError(RambleError):
    """
    Exception that is raised by applications
    """


class ChainCycleDetectedError(ApplicationError):
    """
    Exception raised when a cycle is detected in a defined experiment chain
    """


class InvalidChainError(ApplicationError):
    """
    Exception raised when a invalid chained experiment is defined
    """
