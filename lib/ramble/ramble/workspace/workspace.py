# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import contextlib
import copy
import re
import shutil
import stat
import datetime

import six

import llnl.util.filesystem as fs
import llnl.util.tty as tty

import ramble.config
import ramble.paths
import ramble.util.path
import ramble.error
import ramble.repository
import ramble.spack_runner
import ramble.expander
import ramble.util.web
import ramble.fetch_strategy

import spack.util.spack_yaml as syaml
import spack.util.spack_json as sjson
from spack.util.executable import CommandNotFoundError, which

import ramble.schema.workspace
import ramble.schema.applications

import ramble.util.lock as lk
from ramble.util.path import substitute_path_variables

ramble_namespace = 'ramble'
spack_namespace = 'spack'
application_dir_namespace = 'application_directories'
application_namespace = 'applications'
workload_namespace = 'workloads'
experiment_namespace = 'experiments'
variables_namespace = 'variables'
env_var_namespace = 'env-vars'
mpi_namespace = 'mpi'
batch_namespace = 'batch'
compiler_namespace = 'compilers'
mpi_lib_namespace = 'mpi_libraries'

#: Environment variable used to indicate the active workspace
ramble_workspace_var = 'RAMBLE_WORKSPACE'

#: Currently activated workspace
_active_workspace = None

#: Path where workspaces are stored
workspace_path = os.path.join(ramble.paths.var_path, 'workspaces')

#: Subdirectory where workspace configs are stored
workspace_config_path = 'configs'

#: Name of subdirectory within workspaces where logs are stored
workspace_log_path = 'logs'

#: Name of subdirectory within workspaces where experiments are stored
workspace_experiment_path = 'experiments'

#: Name of subdirectory within workspaces where input files are stored
workspace_input_path = 'inputs'

#: Name of subdirectory within workspaces where software environment
#: are stored
workspace_software_path = 'software'

#: Name of the subdirectory where workspace archives are stored
workspace_archive_path = 'archive'

#: regex for validating workspace names
valid_workspace_name_re = r'^\w[\w-]*$'

#: Config schema for application files
applications_schema = ramble.schema.applications.schema

#: Extension for template files
workspace_template_extension = '.tpl'

#: Config file information for workspaces.
#: Keys are filenames, values are dictionaries describing the config files.
config_schema = ramble.schema.workspace.schema
config_section = 'workspace'
config_file_name = 'ramble.yaml'


def default_config_yaml():
    """default ramble.yaml file to put in new workspaces"""
    return """\
# This is a ramble workspace config file.
#
# It describes the experiments, the software stack
# and all variables required for ramble to configure
# experiments.
# As an example, experiments can be defined as follows.
# applications:
#   variables:
#     processes_per_node: '30'
#   hostname:
#     variables:
#       iterations: '5'
#     workloads:
#       serial:
#         variables:
#           type: 'test'
#         experiments:
#           single_node:
#             variables:
#               n_ranks: '{processes_per_node}'

ramble:
  mpi:
    command: mpirun
    args: []
  batch:
    submit: '{execute_experiment}'
  env-vars:
    set:
      OMP_NUM_THREADS: '{n_threads}'
  variables:
    processes_per_node: -1
  applications: {}
spack:
  concretized: false
  compilers: {}
  mpi_libraries: {}
  applications: {}
    # app_name
    #   spec_name:
    #     base: ''
    #     version: ''
"""


workspace_all_experiments_file = 'all_experiments'

workspace_execution_template = 'execute_experiment' + \
    workspace_template_extension

template_execute_script = """\
# This is a template execution script for
# running the execute pipeline.
#
# Variables surrounded by curly braces will be expanded
# when generating a specific execution script.
# Some example variables are:
#   - experiment_run_dir (Will be replaced with the experiment directory)
#   - command (Will be replaced with the command to run the experiment)
#   - spack_setup (Will be replaced with the commands needed to setup
#                  and load a spack environment for a given experiment)
#   - log_dir (Will be replaced with the logs directory)
#   - experiment_name (Will be replaced with the name of the experiment)
#   - workload_run_dir (Will be replaced with the directory of the workload
#   - application_name (Will be repalced with the name of the application)
#   - n_nodes (Will be replaced with the required number of nodes)
#   Any experiment parameters will be available as variables as well.

cd "{experiment_run_dir}"

{spack_setup}

{command}
"""

#: Name of lockfile within a workspace
lockfile_name = 'ramble.lock'


def valid_workspace_name(name):
    return re.match(valid_workspace_name_re, name)


def validate_workspace_name(name):
    if not valid_workspace_name(name):
        tty.debug('Validation failed for %s' % name)
        raise ValueError((
            "'%s': names must start with a letter, and only contain "
            "letters, numbers, _, and -.") % name)
    return name


def activate(ws):
    """Activate a workspace.

    To activate a workspace, we add its configuration scope to the
    existing Ramble configuration, and we set active to the current
    workspace.

    Arguments:
        ws (Workspace): the workspace to activate
    """
    global _active_workspace

    # Fail early to avoid ending in an invalid state
    if not isinstance(ws, Workspace):
        raise TypeError("`ws` should be of type {0}".format(Workspace.__name__))

    # Check if we need to reinitialize the store due to pushing the configuration
    # below.
    prepare_config_scope(ws)

    tty.debug("Using workspace '%s'" % ws.root)

    # Do this last, because setting up the config must succeed first.
    _active_workspace = ws


def deactivate():
    """Undo any configuration settings modified by ``activate()``."""
    global _active_workspace

    if not _active_workspace:
        return

    tty.debug("Deactivated workspace '%s'" % _active_workspace.root)

    deactivate_config_scope(_active_workspace)

    _active_workspace = None


def prepare_config_scope(workspace):
    """Add workspace's scope to the global configuration search path."""
    for scope in workspace.config_scopes():
        ramble.config.config.push_scope(scope)


def deactivate_config_scope(workspace):
    """Remove any scopes from workspace from the global config path."""
    for scope in workspace.config_scopes():
        ramble.config.config.remove_scope(scope.name)


def all_workspace_names():
    """List the names of workspaces that currently exist."""
    # just return empty if the workspace path does not exist.  A read-only
    # operation like list should not try to create a directory.
    if not os.path.exists(workspace_path):
        return []

    candidates = sorted(os.listdir(workspace_path))
    names = []
    for candidate in candidates:
        configured = True
        yaml_path = os.path.join(_root(candidate),
                                 workspace_config_path,
                                 config_file_name)
        if not os.path.exists(yaml_path):
            configured = False
        if valid_workspace_name(candidate) and configured:
            names.append(candidate)
    return names


def all_workspaces():
    """Generator for all named workspaces."""
    for name in all_workspace_names():
        yield read(name)


def active_workspace():
    """Returns the active workspace when there is any"""
    return _active_workspace


def _root(name):
    """Non-validating version of root(), to be used internally."""
    return os.path.join(workspace_path, name)


def root(name):
    """Get the root directory for a workspace by name."""
    validate_workspace_name(name)
    return _root(name)


def exists(name):
    """Whether a workspace with this name exists or not."""
    if not valid_workspace_name(name):
        return False
    return os.path.isdir(root(name))


def active(name):
    """True if the named workspace is active."""
    return _active_workspace and name == _active_workspace.name


def config_file(path):
    """Returns the path to a workspace's ramble.yaml"""
    if is_workspace_dir(path):
        return os.path.join(path, workspace_config_path, config_file_name)
    return None


def template_path(ws_path, requested_template_name):
    """Returns the path to a workspace's template file"""
    config_path = os.path.join(ws_path, workspace_config_path)
    template_file = requested_template_name + workspace_template_extension
    template_path = os.path.join(config_path, template_file)
    return template_path


def is_workspace_dir(path):
    """Whether a directory contains a ramble workspace."""
    ret_val = os.path.isdir(path)
    if ret_val:
        ret_val = ret_val and os.path.exists(
            os.path.join(path, workspace_config_path, config_file_name))
    return ret_val


def create(name):
    """Create a named workspace in Ramble"""
    validate_workspace_name(name)
    if exists(name):
        raise RambleWorkspaceError("'%s': workspace already exists" % name)
    return Workspace(root(name))


def config_dict(yaml_data):
    """Get the configuration scope section out of a ramble.yaml"""
    key = ramble.config.first_existing(yaml_data, ramble.schema.workspace.keys)
    return yaml_data[key]


def get_workspace(args, cmd_name, required=False):
    """Used by commands to get the active workspace.

    This first checks for a ``workspace`` argument, then looks at the
    ``active`` workspace.  We check args first because Ramble's
    subcommand arguments are parsed *after* the ``-s`` and ``-D``
    arguments to ``ramble``.  So there may be a ``workspace``
    argument that is *not* the active workspace, and we give it
    precedence.

    This is used by a number of commands for determining whether there is
    an active workspace.

    If a workspace is not found *and* is required, print an error
    message that says the calling command *needs* an active
    workspace.

    Arguments:
        args (Namespace): argparse namespace wtih command arguments
        cmd_name (str): name of calling command
        required (bool): if ``True``, raise an exception when no workspace
            is found; if ``False``, just return ``None``

    Returns:
        (Workspace): if there is an arg or active workspace
    """

    tty.debug('In get_workspace()')

    workspace = getattr(args, 'workspace', None)
    if workspace:
        if exists(workspace):
            return read(workspace)
        elif is_workspace_dir(workspace):
            return Workspace(workspace)
        else:
            raise RambleWorkspaceError('no workspace in %s' % workspace)

    # try the active workspace. This is set by find_workspace (above)
    if _active_workspace:
        return _active_workspace
    # elif not required:
    else:
        tty.die(
            '`ramble %s` requires a workspace' % cmd_name,
            'activate a workspace first:',
            '    ramble workspace activate WRKSPC',
            'or use:',
            '    ramble -w WRKSPC %s ...' % cmd_name)


class Workspace(object):
    """Class representing a working directory for workload
    experiments

    Each workspace must have a config directory, that contains 2
    files by default.
       - ramble.yaml
       - execute_experiment.tpl

    The ramble.yaml file is the overall configuration file for
    this workspace. It defines all experiments, variables, and
    the entire software stack.

    The execute_experiment.tpl file is a template script that
    contants the blueprints for running each experiment.
    There are several ramble language features that can be used
    within the script, to help it render properly for all
    experiments.

    Each file with the suffix of .tpl will be expanded into the
    experiment directory, with the .tpl suffix removed.

    Directories will be created for each experiment, when the
    relevant phase of the application is executed. The workspace
    provides a self contained execution environment where experiments
    can be performed.
    """
    def __init__(self, root, dry_run=False):
        tty.debug('In workspace init. Root = {}'.format(root))
        self.root = ramble.util.path.canonicalize_path(root)
        self.txlock = lk.Lock(self._transaction_lock_path)
        self.dry_run = dry_run

        self.configs = ramble.config.ConfigScope('workspace', self.config_dir)
        self._templates = {}

        self.specs = []

        self.config_sections = {}

        self.results = None

        # Key for each application config should be it's filepath
        # Format for an application config should be:
        #  {
        #     'filename': <filename>,
        #     'path': <filepath>,
        #     'raw_yaml': <raw_yaml>,
        #     'yaml': <yaml>
        #  }
        self.application_configs = {}

        self._read()

    def _re_read(self):
        """Reinitialize the workspace object if it has been written (this
           may not be true if the workspace was just created in this running
           instance of ramble)."""
        for _, section in self.config_sections.items():
            if not os.path.exists(section['filename']):
                return

        self.clear()
        self._read()

    def _read(self):
        # Create the workspace config section
        self.config_sections['workspace'] = {
            'filename': self.config_file_path,
            'path': self.config_file_path,
            'schema': config_schema,
            'section_filename': self.config_file_path,
            'raw_yaml': None,
            'yaml': None
        }

        read_default = not os.path.exists(self.config_file_path)
        if read_default:
            self._read_config(config_section, default_config_yaml())
        else:
            with open(self.config_file_path) as f:
                self._read_config(config_section, f)

        read_default_script = True
        ext_len = len(workspace_template_extension)
        if os.path.exists(self.config_dir):
            for filename in os.listdir(self.config_dir):
                if filename.endswith(workspace_template_extension):
                    read_default_script = False
                    template_name = filename[0:-ext_len]
                    template_path = os.path.join(self.config_dir, filename)
                    with open(template_path, 'r') as f:
                        self._read_template(template_name, f.read())

        if read_default_script:
            template_name = workspace_execution_template[0:-ext_len]
            self._read_template(template_name, template_execute_script)

        self._read_all_application_configs()

    def _read_all_application_configs(self):
        path_replacements = {
            'workspace': self.root,
            'workspace_config': self.config_dir
        }
        ramble_dict = self._get_workspace_dict()[ramble_namespace]
        if application_dir_namespace in ramble_dict:
            app_dirs = ramble_dict[application_dir_namespace]
            for raw_dir in app_dirs:
                app_dir = substitute_path_variables(raw_dir,
                                                    path_replacements)
                if not os.path.exists(app_dir):
                    raise RambleMissingApplicationDirError(
                        'Application directory %s does not exist'
                        % app_dir)
                for (dirpath, _, filenames) in os.walk(app_dir):
                    for file in filenames:
                        if file.endswith('.yaml'):
                            full_path = '%s/%s' % (dirpath, file)
                            with open(full_path, 'r') as f:
                                self._read_application_config(
                                    full_path,
                                    f)

    def _read_application_config(self, path, f, raw_yaml=None):
        """Read an application configuration file"""
        if path not in self.application_configs:
            self.application_configs[path] = {
                'filename': os.path.basename(path),
                'path': path,
                'schema': applications_schema,
                'raw_yaml': None,
                'yaml': None
            }

        config = self.application_configs[path]
        self._read_yaml(config, f, raw_yaml)

    def _read_config(self, section, f, raw_yaml=None):
        """Read configuration file"""
        config = self.config_sections[section]
        self._read_yaml(config, f, raw_yaml)

    def _read_yaml(self, config, f, raw_yaml=None):
        if raw_yaml:
            _, config['yaml'] = _read_yaml(f, config['schema'])
            config['raw_yaml'], _ = _read_yaml(raw_yaml, config['schema'])
        else:
            config['raw_yaml'], config['yaml'] = _read_yaml(f,
                                                            config['schema'])

    def _read_template(self, name, f):
        """Read a tempalte file"""
        self._templates[name] = f

    def add(self, user_spec):
        """Add a single workload spec to the workspace

        Returns:
            (bool): True if the spec was added, False if it was
            already present and did not need to be added
        """

        spec = ramble.spec.Spec(user_spec)

        changed = False
        all_apps = self.get_applications()

        # Check that the application exists
        if not ramble.repository.path.exists(spec.name):
            msg = 'no such application: %s' % spec.name
            raise RambleWorkspaceError(msg)

        # Check if application is in the list of workloads already
        if spec.name not in all_apps:
            all_apps[spec.name] = syaml.syaml_dict()
            all_apps[spec.name][workload_namespace] = syaml.syaml_dict()
            changed = True

        app_file = ramble.repository.path.filename_for_application_name(
            spec.name)
        app_dir = ramble.repository.path.dirname_for_application_name(
            spec.name)
        app_filepath = '%s/%s' % (app_dir, app_file)
        app_inst = ramble.repository.path.get_app_class(spec.name)(
            app_filepath)

        app_workloads = all_apps[spec.name][workload_namespace]

        workload_dict = syaml.syaml_dict()
        workload_dict.update(app_workloads.keys())

        if hasattr(spec, 'workloads') and spec.workloads:
            # Try to add each workload name into the list within
            # the application
            for wlname in spec.workloads.keys():
                if wlname not in workload_dict.keys():
                    workload_dict[wlname] = syaml.syaml_dict()
                    workload_dict[wlname]['experiments'] = syaml.syaml_dict()
                    changed = True

        elif not workload_dict:
            # Add all of the workloads from the application
            # to the dict
            for wlname in app_inst.workloads.keys():
                workload_dict[wlname] = syaml.syaml_dict()
                workload_dict[wlname]['experiments'] = syaml.syaml_dict()
                changed = True

        if workload_dict:
            app_workloads.clear()
            app_workloads.update(workload_dict)
        else:
            del all_apps[spec.name]

        return changed

    def remove(self, user_spec):
        """Remove a single workload spec from the workspace

        Returns:
            (bool): True if the spec was removed, False if it was
            absent, and nothing was done
        """

        spec = ramble.spec.Spec(user_spec)

        changed = False
        all_apps = self.get_applications()

        # Check that the application exists
        if not ramble.repository.path.exists(spec.name):
            msg = 'no such application: %s' % spec.name
            raise RambleWorkspaceError(msg)

        # Check if application is missing from the list of workloads
        if spec.name not in all_apps:
            msg = 'application %s is not present in the workspace' % spec.name
            raise RambleWorkspaceError(msg)

        app_workloads = all_apps[spec.name][workload_namespace]

        workload_dict = syaml.syaml_dict()
        workload_dict.update(app_workloads)

        if hasattr(spec, 'workloads') and spec.workloads:
            # Try to remove each workload name from the list within
            # the application
            for wlname in spec.workloads.keys():
                if wlname in workload_dict.keys():
                    del workload_dict[wlname]
                    changed = True

        elif workload_dict:
            workload_dict.clear()
            changed = True

        if workload_dict:
            app_workloads.clear()
            app_workloads.update(workload_dict)
        else:
            del all_apps[spec.name]

        return changed

    def write(self):
        """Write an in-memory workspace to its location on disk."""

        # Ensure required directory structure exists
        fs.mkdirp(self.path)
        fs.mkdirp(self.config_dir)
        fs.mkdirp(self.log_dir)
        fs.mkdirp(self.experiment_dir)
        fs.mkdirp(self.input_dir)
        fs.mkdirp(self.software_dir)

        self._write_config(config_section)

        self._write_templates()

    def _write_config(self, section):
        """Update YAML config file for this workspace, based on
        changes and write it"""
        config = self.config_sections[section]

        changed = not yaml_equivalent(config['raw_yaml'], config['yaml'])
        written = os.path.exists(config['path'])
        if changed or not written:
            config['raw_yaml'] = copy.deepcopy(config['yaml'])
            with fs.write_tmp_and_move(config['path']) as f:
                _write_yaml(config['yaml'], f, config['schema'])

    def _write_templates(self):
        """Write all templates out to workspace"""

        for name, value in self._templates.items():
            template_path = self.template_path(name)
            with open(template_path, 'w+') as f:
                f.write(value)

    def clear(self):
        self.config_sections = {}
        self.application_configs = []
        self._previous_active = None      # previously active environment
        self.specs = []

    def all_applications(self):
        """Iterator over applications

        Returns application, variables
        where variables are the platform level variables that
        should be applied.
        """

        ws_dict = self._get_workspace_dict()
        tty.debug(' With ws dict: %s' % (ws_dict))

        # Iterate over applications in ramble.yaml first
        if application_namespace in ws_dict[ramble_namespace]:
            app_dict = ws_dict[ramble_namespace][application_namespace]
            for application, contents in app_dict.items():
                application_vars = None
                application_env_vars = None
                if variables_namespace in contents:
                    application_vars = contents[variables_namespace]
                if env_var_namespace in contents:
                    application_env_vars = contents[env_var_namespace]

                yield application, contents, application_vars, \
                    application_env_vars

        tty.debug('  Iterating over configs in directories...')
        # Iterate over applications defined in application directories
        # files after the ramble.yaml file is complete
        for app_conf in self.application_configs:
            config = self._get_application_dict_config(app_conf)
            if application_namespace not in config:
                tty.msg('No applications in config file %s'
                        % app_conf)
            app_dict = config[application_namespace]
            for application, contents in app_dict.items():
                application_vars = None
                application_env_vars = None
                if variables_namespace in contents:
                    application_vars = \
                        contents[variables_namespace]
                if env_var_namespace in contents:
                    application_env_vars = contents[env_var_namespace]
                yield application, contents, application_vars, application_env_vars

    def all_workloads(self, application):
        """Iterator over workloads in an application dict

        Returns workload, variables
        where variables are the application level variables that
        should be applied.
        """

        if workload_namespace not in application:
            tty.msg('No workloads in application')
            return

        workloads = application[workload_namespace]

        for workload, contents in workloads.items():
            workload_variables = None
            workload_env_vars = None
            if variables_namespace in contents:
                workload_variables = contents[variables_namespace]
            if env_var_namespace in contents:
                workload_env_vars = contents[env_var_namespace]

            yield workload, contents, workload_variables, workload_env_vars

    def all_experiments(self, workload):
        """Iterator over experiments in a workload dict

        Returns experiment, variables, and matrix/matrices
        Where variables are the workload level variables that
        should be applied.
        """

        if experiment_namespace not in workload:
            tty.msg('No experiments in workload')
            return

        experiments = workload[experiment_namespace]
        for experiment, contents in experiments.items():
            experiment_vars = None
            experiment_env_vars = None
            if variables_namespace in contents:
                experiment_vars = contents[variables_namespace]
            if env_var_namespace in contents:
                experiment_env_vars = contents[env_var_namespace]

            matrices = []
            if 'matrix' in contents:
                matrices.append(contents['matrix'])

            if 'matrices' in contents:
                for matrix in contents['matrices']:
                    # Extract named matrices
                    if isinstance(matrix, dict):
                        if len(matrix.keys()) != 1:
                            tty.die('In experiment %s' % experiment
                                    + ' each list element may only contain '
                                    + '1 matrix in a matrices definition.')

                        for name, val in matrix.items():
                            matrices.append(val)
                    elif isinstance(matrix, list):
                        matrices.append(matrix)

            yield experiment, contents, experiment_vars, \
                experiment_env_vars, matrices

    def _build_spec_dict(self, info_dict, app_name=None, for_config=False):
        spec = {}

        for name, val in info_dict.items():
            if val:
                spec[name] = val

        if app_name:
            spec['application_name'] = app_name

        if for_config:
            if 'application_name' in spec:
                del spec['application_name']
            if 'spec_type' in spec:
                del spec['spec_type']

        return spec

    def specs_equiv(self, spec1, spec2):
        all_keys = set(spec1.keys())
        all_keys.update(set(spec2.keys()))

        if len(all_keys) != len(spec1.keys()):
            return False

        if 'application_name' in all_keys:
            all_keys.remove('application_name')

        if 'spec_type' in all_keys:
            all_keys.remove('spec_type')

        for key in all_keys:
            if key not in spec1:
                return False
            if key not in spec2:
                return False
            if spec1[key] != spec2[key]:
                return False

        return True

    def get_named_spec(self, spec_name, spec_context='compiler'):
        spack_dict = self.get_spack_dict()

        if spec_context == 'compiler':
            if compiler_namespace not in spack_dict:
                raise RambleWorkspaceError('No compilers ' +
                                           'defined in workspace')
            spec_dict = spack_dict[compiler_namespace]
        elif spec_context == 'mpi_library':
            if mpi_lib_namespace not in spack_dict:
                raise RambleWorkspaceError('No MPI libraries ' +
                                           'defined in workspace')
            spec_dict = spack_dict[mpi_lib_namespace]
        else:
            if application_namespace not in spack_dict:
                raise RambleWorkspaceError('No applications ' +
                                           'defined in workspace')
            if spec_context not in spack_dict['applications']:
                raise RambleWorkspaceError('Invalid context ' +
                                           '%s' % spec_context)
            spec_dict = spack_dict[application_namespace][spec_context]
            return self._build_spec_dict(spec_dict[spec_name], app_name=spec_context)

        return self._build_spec_dict(spec_dict[spec_name])

    def spec_string(self, spec, as_dep=False, use_custom_specifier=False, deps_used=None):
        """Create a string for a spec

        Extract portions of the spec into a usable string.
        """

        if not deps_used:
            deps_used = set()

        spec_str = []

        if spec['base'] in deps_used:
            return ''
        else:
            deps_used.add(spec['base'])

        if use_custom_specifier and 'custom_specifier' in spec:
            return spec['custom_specifier']

        if 'base' in spec:
            spec_str.append(spec['base'])

        if 'version' in spec:
            spec_str.append('@%s' % spec['version'])

        if 'variants' in spec:
            spec_str.append(spec['variants'])

        if 'compiler' in spec:
            comp_spec = self.get_named_spec(spec['compiler'], 'compiler')

            if comp_spec['base'] not in deps_used:
                spec_str.append('%%%s' % self.spec_string(comp_spec,
                                                          as_dep=True,
                                                          use_custom_specifier=True,
                                                          deps_used=deps_used))

        if not as_dep:
            if 'arch' in spec:
                spec_str.append('arch=%s' % spec['arch'])

            if 'target' in spec:
                spec_str.append('target=%s' % spec['target'])

        if 'dependencies' in spec:
            for dep in spec['dependencies']:
                dep_spec = self.get_named_spec(dep, spec['application_name'])

                dep_str = self.spec_string(dep_spec, as_dep=True,
                                           use_custom_specifier=False,
                                           deps_used=deps_used)

                if dep_str:
                    spec_str.append(f'^{dep_str}')

        return ' '.join(spec_str)

    def all_application_specs(self, app_name):
        spack_dict = self.get_spack_dict()

        if application_namespace not in spack_dict:
            raise RambleWorkspaceError('No applications defined ' +
                                       'in spack config section')

        if app_name not in spack_dict[application_namespace]:
            raise RambleWorkspaceError('Application %s ' % app_name +
                                       'not defined in spack ' +
                                       'config section')

        app_specs = spack_dict[application_namespace][app_name]
        for name, info in app_specs.items():
            spec = self._build_spec_dict(info)
            yield name, spec

    def concretize(self):
        spack_dict = self.get_spack_dict()

        if 'concretized' in spack_dict and spack_dict['concretized']:
            raise RambleWorkspaceError('Cannot conretize an ' +
                                       'already concretized ' +
                                       'workspace')

        if compiler_namespace not in spack_dict or \
                not spack_dict[compiler_namespace]:
            spack_dict[compiler_namespace] = syaml.syaml_dict()
        if mpi_lib_namespace not in spack_dict or \
                not spack_dict[mpi_lib_namespace]:
            spack_dict[mpi_lib_namespace] = syaml.syaml_dict()
        if application_namespace not in spack_dict or \
                not spack_dict[application_namespace]:
            spack_dict[application_namespace] = syaml.syaml_dict()

        compilers_dict = spack_dict[compiler_namespace]
        mpi_dict = spack_dict[mpi_lib_namespace]
        applications_dict = spack_dict[application_namespace]

        for app_name, _, _, _ in self.all_applications():
            app_inst = ramble.repository.get(app_name)

            for comp, info in app_inst.default_compilers.items():
                spec = self._build_spec_dict(info, for_config=True)
                if comp not in compilers_dict:
                    compilers_dict[comp] = spec
                else:
                    comp_spec = self.get_named_spec(comp, 'compiler')
                    if not self.specs_equiv(comp_spec, spec):
                        err = 'Compiler %s defined multiple ' % comp + \
                              'conflicting ways'
                        raise RambleConflictingDefinitionError(err)

            for mpi, info in app_inst.mpi_libraries.items():
                spec = self._build_spec_dict(info, for_config=True)
                if mpi not in mpi_dict:
                    mpi_dict[mpi] = spec
                else:
                    mpi_spec = self.get_named_spec(mpi, 'mpi_library')
                    if not self.specs_equiv(mpi_spec, spec):
                        err = 'MPI Library %s defined multiple ' % mpi + \
                              'conflicting ways'
                        raise RambleConflictingDefinitionError(err)

            if app_name not in applications_dict:
                applications_dict[app_name] = syaml.syaml_dict()

            app_specs = applications_dict[app_name]
            for spec_name, info in app_inst.software_specs.items():
                spec = self._build_spec_dict(info, for_config=True)
                if spec_name not in app_specs:
                    app_specs[spec_name] = spec
                else:
                    app_spec = self.get_named_spec(spec_name, app_name)
                    if not self.specs_equiv(app_spec, spec):
                        err = 'Spec %s defined multiple ' % spec_name + \
                              'times in application %s' % app_name
                        raise RambleConflictingDefinitionError(err)

        workspace_dict = self._get_workspace_dict()
        workspace_dict[spack_namespace]['concretized'] = True
        self.write()
        return

    def append_result(self, result):
        if not self.results:
            self.results = {}

        self.results.update(result)

    def dump_results(self, output_formats=['text']):
        if not self.results:
            self.results = {}

        results_written = []

        dt = self._date_string()
        filename_base = 'results.' + dt

        if 'text' in output_formats:

            out_file = os.path.join(self.root, filename_base + '.txt')
            results_written.append(out_file)

            with open(out_file, 'w+') as f:
                for exp, results in self.results.items():
                    f.write('Experiment %s figures of merit:\n' %
                            exp)
                    f.write('  Status = %s\n' %
                            results['RAMBLE_STATUS'])
                    if results['RAMBLE_STATUS'] == 'SUCCESS':
                        for context, foms in \
                                results['CONTEXTS'].items():
                            f.write('  %s figures of merit:\n' %
                                    context)
                            for name, fom in foms.items():
                                output = '%s = %s %s' % (name,
                                                         fom['value'],
                                                         fom['units'])
                                f.write('    %s\n' % (output.strip()))
        if 'json' in output_formats:
            out_file = os.path.join(self.root, filename_base + '.json')
            results_written.append(out_file)
            with open(out_file, 'w+') as f:
                sjson.dump(self.results, f)

        if 'yaml' in output_formats:
            out_file = os.path.join(self.root, filename_base + '.yaml')
            results_written.append(out_file)
            with open(out_file, 'w+') as f:
                syaml.dump(self.results, stream=f)

        if not results_written:
            tty.die('Results were not written.')

        tty.msg('Results are written to:')
        for out_file in results_written:
            tty.msg('  %s' % out_file)

        return filename_base

    def run_experiments(self):

        try:
            experiment_script = which('%s/all_experiments' % self.root, required=True)
        except CommandNotFoundError:
            raise RambleWorkspaceError('Cannot find `all_experiments` in workspace root.')

        experiment_script()

    def run_pipeline(self, pipeline):
        all_experiments_file = None
        expander = ramble.expander.Expander(self)

        if not self.is_concretized():
            error_message = 'Cannot run %s in a ' % pipeline + \
                            'non-conretized workspace\n' + \
                            'Run `ramble workspace concretize` on this ' + \
                            'workspace first.\n' + \
                            'Then ensure its software_stack.yaml file is ' + \
                            'properly configured.'
            tty.die(error_message)

        if pipeline == 'setup':
            all_experiments_path = os.path.join(self.root,
                                                workspace_all_experiments_file)
            all_experiments_file = open(all_experiments_path, 'w+')
            all_experiments_file.write('#!/bin/sh\n')

            expander.set_var('experiments_file', all_experiments_file)

            runner = ramble.spack_runner.SpackRunner(dry_run=self.dry_run)
            spack_dict = self.get_spack_dict()
            if compiler_namespace in spack_dict:
                for comp_name, comp_spec in \
                        spack_dict[compiler_namespace].items():
                    comp_str = self.spec_string(comp_spec,
                                                as_dep=False,
                                                use_custom_specifier=False)
                    runner.install_compiler(comp_str)

        for app, workloads, app_vars, app_env_vars in self.all_applications():
            expander.set_application(app)
            expander.set_application_vars(app_vars)
            expander.set_application_env_vars(app_env_vars)
            tty.debug('Getting application: %s' % app)
            tty.debug('Getting application: %s' % expander.application_name)
            app_inst = ramble.repository.get(expander.application_name)

            tty.msg('  Working on ' + app_inst.application_class +
                    ' ' + app_inst.name)

            for workload, experiments, workload_vars, workload_env_vars in \
                    self.all_workloads(workloads):
                expander.set_workload(workload)
                expander.set_workload_vars(workload_vars)
                expander.set_workload_env_vars(workload_env_vars)

                for experiment, _, exp_vars, exp_env_vars, exp_matrices in \
                        self.all_experiments(experiments):
                    expander.set_experiment(experiment)
                    expander.set_experiment_vars(exp_vars)
                    expander.set_experiment_env_vars(exp_env_vars)
                    expander.set_experiment_matrices(exp_matrices)

                    for _ in expander.rendered_experiments():
                        app_inst = ramble.repository.get(expander.application_name)
                        for phase in app_inst.get_pipeline_phases(pipeline):
                            app_inst.run_phase(phase, self, expander)

        if pipeline == 'setup':
            all_experiments_file.close()

            all_experiments_path = os.path.join(self.root,
                                                workspace_all_experiments_file)
            os.chmod(all_experiments_path, stat.S_IRWXU | stat.S_IRWXG
                     | stat.S_IROTH | stat.S_IXOTH)

    @property
    def latest_archive_path(self):
        return os.path.join(self.archive_dir, self.latest_archive)

    @property
    def latest_archive(self):
        if hasattr(self, '_latest_archive') and self._latest_archive:
            return self._latest_archive

        if os.path.exists(self.archive_dir):
            archive_dirs = []

            for subdir in os.listdir(self.archive_dir):
                archive_path = os.path.join(self.archive_dir, subdir)
                if os.path.isdir(archive_path):
                    archive_dirs.append(archive_path)

            if archive_dirs:
                latest_path = max(archive_dirs, key=os.path.getmtime)
                self._latest_archive = os.path.basename(latest_path)
                return self._latest_archive

        return None

    def archive(self, create_tar=True, archive_url=None):
        """Archive current configuration, and experiment state.

        Create an archive of the current configuration of this workspace, and
        the state of the experiments.

        Experiment state includes any rendered templates, along with any
        results files that figures of merit would be extracted from.

        None of the input, or output files aside from these are archived.
        However, the archive should useful to perform the following actions:
         - Re-extract figures of merit based on previous experiments
         - Regenerate experiments, using the archived configuration.

        If an archive url is configured for ramble at config:archive_url this
        will automatically upload tar archives to that location.

        NOTE: If the current configuration differs from the one used to create
        the experiments that are being set up, it's possible that the
        configuration cannot regenerate the same experiments.
        """

        import py
        import glob

        date_str = self._date_string()

        # Use the basename from the path as the name of the workspace.
        # If we use `self.name` we get the path multiple times.
        archive_name = '%s-archive-%s' % (os.path.basename(self.path), date_str)

        archive_path = os.path.join(self.archive_dir, archive_name)
        fs.mkdirp(archive_path)

        # Copy current configs
        archive_configs = os.path.join(self.latest_archive_path, workspace_config_path)
        fs.mkdirp(archive_configs)
        for file in os.listdir(self.config_dir):
            src = os.path.join(self.config_dir, file)
            dest = src.replace(self.config_dir, archive_configs)
            shutil.copyfile(src, dest)

        # Copy current software spack.yamls
        archive_software = os.path.join(self.latest_archive_path, workspace_software_path)
        fs.mkdirp(archive_software)
        for file in glob.glob(os.path.join(self.software_dir, '*', 'spack.yaml')):
            dest = file.replace(self.software_dir, archive_software)
            fs.mkdirp(os.path.dirname(dest))
            shutil.copyfile(file, dest)

        self.run_pipeline('archive')

        if create_tar:
            tar = which('tar', required=True)
            with py.path.local(self.archive_dir).as_cwd():
                tar('-czf', archive_name + '.tar.gz', archive_name)

            archive_url = archive_url if archive_url else ramble.config.get('config:archive_url')
            archive_url = archive_url.rstrip('/') if archive_url else None

            tty.debug('Archive url: %s' % archive_url)

            if archive_url:
                tar_path = self.latest_archive_path + '.tar.gz'
                remote_tar_path = archive_url + '/' + self.latest_archive + '.tar.gz'
                fetcher = ramble.fetch_strategy.URLFetchStrategy(tar_path)
                fetcher.stage = ramble.stage.DIYStage(self.latest_archive_path)
                fetcher.stage.archive_file = tar_path
                fetcher.archive(remote_tar_path)

    def _date_string(self):
        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d_%H.%M.%S")

    @property
    def mpi_command(self):
        if not hasattr(self, 'mpi_template') or not self.mpi_template:
            mpi_config = \
                self._get_workspace_dict()[ramble_namespace][mpi_namespace]

            self.mpi_template = ''
            if 'pre_command' in mpi_config:
                self.mpi_template += " %s" % mpi_config['pre_command']
            if 'pre_command_args' in mpi_config:
                self.mpi_template += " %s" % \
                    ' '.join(mpi_config['pre_command_args'])
            if 'command' in mpi_config:
                self.mpi_template += " %s" % mpi_config['command']
            if 'args' in mpi_config:
                self.mpi_template += " %s" % ' '.join(mpi_config['args'])
            if 'post_command' in mpi_config:
                self.mpi_template += " %s" % mpi_config['post_command']
            if 'post_command_args' in mpi_config:
                self.mpi_template += " %s" % \
                    ' '.join(mpi_config['post_command_args'])

        return self.mpi_template

    @property
    def batch_submit(self):
        if not hasattr(self, 'batch_submit_command') or not \
                self.batch_submit_command:

            workspace_dict = self._get_workspace_dict()
            if batch_namespace in workspace_dict[ramble_namespace]:
                batch_section = \
                    workspace_dict[ramble_namespace][batch_namespace]
                batch_submit = batch_section['submit']
            else:
                batch_submit = ''

            self.batch_submit_command = batch_submit
        return self.batch_submit_command

    @property
    def internal(self):
        """Whether this workspace is managed by Ramble."""
        return self.path.startswith(workspace_path)

    @property
    def name(self):
        """Human-readable representation of the workspace.

        This is the path for directory workspaces and just the name
        for named workspaces.
        """
        if self.internal:
            return os.path.basename(self.path)
        else:
            return self.path

    @property
    def path(self):
        """Location of the workspace"""
        return self.root

    @property
    def active(self):
        """True if this workspace is currently active."""
        return _active_workspace and self.path == _active_workspace.path

    @property
    def _transaction_lock_path(self):
        """The location of the lock file used to synchronize multiple
        processes updating the same workspace.
        """
        return os.path.join(self.root, 'transaction_lock')

    @property
    def experiment_dir(self):
        """Path to the experiment directory"""
        return os.path.join(self.root, workspace_experiment_path)

    @property
    def input_dir(self):
        """Path to the input directory"""
        return os.path.join(self.root, workspace_input_path)

    @property
    def software_dir(self):
        """Path to the software directory"""
        return os.path.join(self.root, workspace_software_path)

    @property
    def log_dir(self):
        """Path to the logs directory"""
        return os.path.join(self.root, workspace_log_path)

    @property
    def config_dir(self):
        """Path to the configuration file directory"""
        return os.path.join(self.root, workspace_config_path)

    @property
    def config_file_path(self):
        """Path to the configuration file directory"""
        return os.path.join(self.config_dir, config_file_name)

    @property
    def archive_dir(self):
        """Path to the archive directory"""
        return os.path.join(self.root, workspace_archive_path)

    def template_path(self, name):
        if name in self._templates.keys():
            return os.path.join(self.config_dir, name +
                                workspace_template_extension)
        return None

    def all_templates(self):
        """Iterator over each template in the workspace"""
        for name, value in self._templates.items():
            yield name, value

    def included_config_scopes(self):
        """List of included configuration scopes from the environment.

        Scopes are listed in the YAML file in order from highest to
        lowest precedence, so configuration from earlier scope will take
        precedence over later ones.

        This routine returns them in the order they should be pushed onto
        the internal scope stack (so, in reverse, from lowest to highest).
        """
        scopes = []

        # load config scopes added via 'include:', in reverse so that
        # highest-precedence scopes are last.
        includes = config_dict(self.config_sections['workspace']['yaml']).get('include', [])
        missing = []
        for i, config_path in enumerate(reversed(includes)):
            # allow paths to contain ramble config/environment variables, etc.
            config_path = substitute_path_variables(config_path)

            # treat relative paths as relative to the environment
            if not os.path.isabs(config_path):
                config_path = os.path.join(self.path, config_path)
                config_path = os.path.normpath(os.path.realpath(config_path))

            if os.path.isdir(config_path):
                # directories are treated as regular ConfigScopes
                config_name = 'workspace:%s:%s' % (
                    self.name, os.path.basename(config_path))
                scope = ramble.config.ConfigScope(config_name, config_path)
            elif os.path.exists(config_path):
                # files are assumed to be SingleFileScopes
                config_name = 'workspace:%s:%s' % (self.name, config_path)
                scope = ramble.config.SingleFileScope(
                    config_name, config_path, ramble.schema.merged.schema)
            else:
                missing.append(config_path)
                continue

            scopes.append(scope)

        if missing:
            msg = 'Detected {0} missing include path(s):'.format(len(missing))
            msg += '\n   {0}'.format('\n   '.join(missing))
            tty.die('{0}\nPlease correct and try again.'.format(msg))

        return scopes

    def ws_file_config_scope_name(self):
        """Name of the config scope of this workspace's config file."""
        return 'workspace:%s:%s' % (self.name, self.config_dir)
        # return 'ws:%s' % self.name

    def ws_file_config_scope(self):
        """Get the configuration scope for the workspace's config file."""
        section = self.config_sections['workspace']
        config_name = self.ws_file_config_scope_name()
        return ramble.config.SingleFileScope(
            config_name,
            section['path'],
            ramble.schema.workspace.schema,
            [ramble.config.first_existing(section['raw_yaml'],
                                          ramble.schema.workspace.keys)])

    def config_scopes(self):
        """A list of all configuration scopes for this workspace."""
        return self.included_config_scopes() + \
            [self.ws_file_config_scope()] + \
            [self.configs]

    def destroy(self):
        """Remove this workspace from Ramble entirely."""
        shutil.rmtree(self.path)

    def _get_workspace_dict(self):
        return self.config_sections['workspace']['yaml'] if 'workspace' \
            in self.config_sections else None

    def _get_application_dict_config(self, key):
        return self.application_configs[key]['yaml'] if key \
            in self.application_configs else None

    def is_concretized(self):
        ws_dict = self._get_workspace_dict()
        if 'concretized' in ws_dict[spack_namespace]:
            return (True if ws_dict[spack_namespace]['concretized']
                    else False)
        return False

    def get_workspace_vars(self):
        """Return a dict of workspace variables"""
        workspace_dict = self._get_workspace_dict()

        return workspace_dict[ramble_namespace][variables_namespace] \
            if variables_namespace in \
            workspace_dict[ramble_namespace] else syaml.syaml_dict()

    def get_workspace_env_vars(self):
        """Return a dict of workspace environment variables"""
        workspace_dict = self._get_workspace_dict()

        return workspace_dict[ramble_namespace][env_var_namespace] \
            if env_var_namespace in \
            workspace_dict[ramble_namespace] else None

    def get_spack_dict(self):
        """Return the spack dictionary for this workspace"""
        ws_dict = self._get_workspace_dict()
        if spack_namespace in ws_dict:
            return ws_dict[spack_namespace]
        return syaml.syaml_dict()

    def get_applications(self):
        """Get the dictionary of applications"""
        tty.debug('Getting app dict.')
        tty.debug(' %s ' % self._get_workspace_dict())
        workspace_dict = self._get_workspace_dict()
        if application_namespace not in workspace_dict[ramble_namespace]:
            workspace_dict[ramble_namespace][application_namespace] = \
                syaml.syaml_dict()
        return workspace_dict[ramble_namespace][application_namespace]

    def write_transaction(self):
        """Get a write lock context manager for use in a `with` block."""
        return lk.WriteTransaction(self.txlock, acquire=self._re_read)

    def __enter__(self):
        self._previous_active = _active_workspace
        activate(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        deactivate()
        if self._previous_active:
            activate(self._previous_active)


def read(name):
    """Get a workspace with the supplied name."""
    validate_workspace_name(name)
    if not exists(name):
        raise RambleWorkspaceError("no such workspace '%s'" % name)
    return Workspace(root(name))


def yaml_equivalent(first, second):
    """Returns whether two ramble yaml items are equivalent, including overrides
    """
    if isinstance(first, dict):
        return isinstance(second, dict) and _equiv_dict(first, second)
    elif isinstance(first, list):
        return isinstance(second, list) and _equiv_list(first, second)
    else:  # it's a string
        return isinstance(second, six.string_types) and first == second


def _equiv_list(first, second):
    """Returns whether two ramble yaml lists are equivalent, including overrides
    """
    if len(first) != len(second):
        return False
    return all(yaml_equivalent(f, s) for f, s in zip(first, second))


def _equiv_dict(first, second):
    """Returns whether two ramble yaml dicts are equivalent, including overrides
    """
    if len(first) != len(second):
        return False
    same_values = all(yaml_equivalent(fv, sv)
                      for fv, sv in zip(first.values(), second.values()))
    same_keys_with_same_overrides = all(
        fk == sk and getattr(fk, 'override', False) == getattr(sk, 'override',
                                                               False)
        for fk, sk in zip(first.keys(), second.keys()))
    return same_values and same_keys_with_same_overrides


def _read_yaml(str_or_file, schema):
    """Read YAML from a file for round-trip parsing."""
    data = syaml.load_config(str_or_file)
    filename = getattr(str_or_file, 'name', None)
    default_data = ramble.config.validate(
        data, schema, filename)
    return (data, default_data)


def _write_yaml(data, str_or_file, schema):
    """Write YAML to a file preserving comments and dict order."""
    filename = getattr(str_or_file, 'name', None)
    ramble.config.validate(data, schema, filename)
    syaml.dump_config(data, str_or_file, default_flow_style=False)


@contextlib.contextmanager
def no_active_workspace():
    """Deactivate the active workspace for the duration of the context. Has no
       effect when there is no active workspace."""
    ws = active_workspace()
    try:
        deactivate()
        yield
    finally:
        if ws:
            activate(ws)


class RambleWorkspaceError(ramble.error.RambleError):
    """Superclass for all errors to do with Ramble Workspaces"""


class RambleConflictingDefinitionError(RambleWorkspaceError):
    """Error when conflicting software definitions are found"""


class RambleMissingApplicationError(RambleWorkspaceError):
    """Error when using an undefined application in an experiment
    specification"""


class RambleMissingWorkloadError(RambleWorkspaceError):
    """Error when using an undefined workload in an experiment
    specification"""


class RambleMissingExperimentError(RambleWorkspaceError):
    """Error when using an undefined experiment in an experiment
    specification"""


class RambleMissingApplicationDirError(RambleWorkspaceError):
    """Error when using a non-existent application directory"""
