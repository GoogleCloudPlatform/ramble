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
import ramble.experiment_set
import ramble.util.web
import ramble.fetch_strategy
import ramble.util.install_cache
import ramble.success_criteria
import ramble.keywords
import ramble.software_environments
from ramble.mirror import MirrorStats
from ramble.config import ConfigError
import ramble.experimental.uploader

import spack.util.spack_yaml as syaml
import spack.util.spack_json as sjson
from spack.util.executable import CommandNotFoundError, which
import spack.util.url as url_util
import spack.util.web as web_util

import ramble.schema.workspace
import ramble.schema.applications
import ramble.schema.merged

import ramble.util.lock as lk
from ramble.util.path import substitute_path_variables
from ramble.util.spec_utils import specs_equiv
import ramble.util.hashing
from ramble.namespace import namespace


#: Environment variable used to indicate the active workspace
ramble_workspace_var = 'RAMBLE_WORKSPACE'

#: Currently activated workspace
_active_workspace = None

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

#: Directory name for auxiliary software files
auxiliary_software_dir_name = 'auxiliary_software_files'

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
  env_vars:
    set:
      OMP_NUM_THREADS: '{n_threads}'
  variables:
    mpi_command: mpirun -n {n_ranks}
    batch_submit: '{execute_experiment}'
    processes_per_node: -1
  applications: {}
  spack:
    concretized: false
    packages: {}
    environments: {}
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
#   - log_dir (Will be replaced with the logs directory)
#   - experiment_name (Will be replaced with the name of the experiment)
#   - workload_run_dir (Will be replaced with the directory of the workload
#   - application_name (Will be repalced with the name of the application)
#   - n_nodes (Will be replaced with the required number of nodes)
#   Any experiment parameters will be available as variables as well.

cd "{experiment_run_dir}"

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
    wspath = get_workspace_path()
    if not os.path.exists(wspath):
        return []

    candidates = sorted(os.listdir(wspath))
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


def get_workspace_path():
    """Returns current directory of ramble-managed workspaces"""
    path_in_config = ramble.config.get('config:workspace_dirs')
    if not path_in_config:
        # command above should have worked, so if it doesn't, error out:
        tty.die('No config:workspace_dirs setting found in configuration!')

    wspath = ramble.util.path.canonicalize_path(str(path_in_config))
    return wspath


def _root(name):
    """Non-validating version of root(), to be used internally."""
    wspath = get_workspace_path()
    return os.path.join(wspath, name)


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


def all_template_paths(path):
    """Returns (abs) path to available template files in the workspace"""
    templates = []

    config_path = os.path.join(path, workspace_config_path)
    for f in os.listdir(config_path):
        if f.endswith(workspace_template_extension):
            templates.append(os.path.join(config_path, f))

    return templates


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
        args (ramble.namespace): argparse namespace with command arguments
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
    constants the blueprints for running each experiment.
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

    _inventory_file_name = 'ramble_inventory.json'
    _hash_file_name = 'workspace_hash.sha256'

    def __init__(self, root, dry_run=False):
        tty.debug('In workspace init. Root = {}'.format(root))
        self.root = ramble.util.path.canonicalize_path(root)
        self.txlock = lk.Lock(self._transaction_lock_path)
        self.dry_run = dry_run
        self.always_print_foms = False

        self.configs = ramble.config.ConfigScope('workspace', self.config_dir)
        self._templates = {}
        self._auxiliary_software_files = {}
        self._software_mirror_path = None
        self._input_mirror_path = None
        self._mirror_existed = None
        self._software_mirror_stats = None
        self._input_mirror_stats = None
        self._input_mirror_cache = None
        self._software_mirror_cache = None
        self._software_environments = None
        self.hash_inventory = {
            'experiments': [],
            'versions': []
        }

        from ramble.main import get_version
        self.hash_inventory['versions'].append(
            {
                'name': 'ramble',
                'version': get_version(),
                'digest': ramble.util.hashing.hash_string(get_version()),
            }
        )

        from ramble.spack_runner import SpackRunner, RunnerError
        try:
            runner = SpackRunner()
            spack_version = runner.get_version()
            self.hash_inventory['versions'].append(
                {
                    'name': 'spack',
                    'version': spack_version,
                    'digest': ramble.util.hashing.hash_string(spack_version),
                }
            )
        except RunnerError:
            pass
        self.workspace_hash = None

        self.specs = []

        self.config_sections = {}

        self.install_cache = ramble.util.install_cache.SetCache()

        self.results = self.default_results()

        self.success_list = ramble.success_criteria.ScopedCriteriaList()

        # Key for each application config should be it's filepath
        # Format for an application config should be:
        #  {
        #     'filename': <filename>,
        #     'path': <filepath>,
        #     'raw_yaml': <raw_yaml>,
        #     'yaml': <yaml>
        #  }
        self.application_configs = {}

        self._experiment_script = None

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

        keywords = ramble.keywords.keywords

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
                    if keywords.is_reserved(template_name):
                        raise RambleInvalidTemplateNameError(
                            f'Template file {filename} results in a '
                            f'template name of {template_name}'
                            + ' which is reserved by ramble.'
                        )

                    with open(template_path, 'r') as f:
                        self._read_template(template_name, f.read())

            if os.path.exists(self.auxiliary_software_dir):
                for filename in os.listdir(self.auxiliary_software_dir):
                    aux_file_path = os.path.join(self.auxiliary_software_dir, filename)
                    with open(aux_file_path, 'r') as f:
                        self._read_auxiliary_software_file(filename, f.read())

        if read_default_script:
            template_name = workspace_execution_template[0:-ext_len]
            self._read_template(template_name, template_execute_script)

        self._read_all_application_configs()

    def _read_all_application_configs(self):
        path_replacements = {
            'workspace': self.root,
            'workspace_config': self.config_dir
        }
        ramble_dict = self._get_workspace_dict()[namespace.ramble]
        if namespace.application_dir in ramble_dict:
            app_dirs = ramble_dict[namespace.application_dir]
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
        self._check_deprecated(config['yaml'])

    def _check_deprecated(self, config):
        """
        Trap and warn (or error) on deprecated configuration settings
        in the workspace config.
        """

        error_sections = []
        deprecated_sections = []

        if len(deprecated_sections) > 0:
            tty.warn('Your workspace configuration contains deprecated sections:')
            for section in deprecated_sections:
                tty.warn(f'     {section}')
            tty.warn('Please see the current workspace documentation and update')
            tty.warn('to ensure your workspace continues to function properly')

        if len(error_sections) > 0:
            tty.warn('Your workspace configuration contains invalid sections:')
            for section in deprecated_sections:
                tty.warn(f'     {section}')
            tty.die('Please update to the latest format.')

    def _read_yaml(self, config, f, raw_yaml=None):
        if raw_yaml:
            _, config['yaml'] = _read_yaml(f, config['schema'])
            config['raw_yaml'], _ = _read_yaml(raw_yaml, config['schema'])
        else:
            config['raw_yaml'], config['yaml'] = _read_yaml(f,
                                                            config['schema'])

    def _read_template(self, name, f):
        """Read a template file"""
        self._templates[name] = {
            'contents': f,
            'digest': ramble.util.hashing.hash_string(f),
        }

    def _read_auxiliary_software_file(self, name, f):
        """Read an auxiliary software file for generated software directories"""
        self._auxiliary_software_files[name] = f

    def write(self):
        """Write an in-memory workspace to its location on disk."""

        # Ensure required directory structure exists
        fs.mkdirp(self.path)
        fs.mkdirp(self.config_dir)
        fs.mkdirp(self.auxiliary_software_dir)
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

        for name, conf in self._templates.items():
            template_path = self.template_path(name)
            with open(template_path, 'w+') as f:
                f.write(conf['contents'])

    def clear(self):
        self.config_sections = {}
        self.application_configs = []
        self._previous_active = None      # previously active environment
        self.specs = []

    def extract_success_criteria(self, scope, contents):
        """Extract success citeria, and inject it into the scoped list

        Extract success criteria from a contents dictionary, and inject it into
        the scoped success list within the right scope.
        """
        self.success_list.flush_scope(scope)

        if namespace.success in contents:
            tty.debug(' ---- Found success in %s' % scope)
            for conf in contents[namespace.success]:
                tty.debug(' ---- Adding criteria %s' % conf['name'])
                self.success_list.add_criteria(scope, **conf)

    def all_specs(self):
        import ramble.spec

        specs = []
        for app, workloads, *_ in self.all_applications():
            for workload, *_ in self.all_workloads(workloads):
                app_spec = ramble.spec.Spec(app)
                app_spec.workloads[workload] = True
                specs.append(app_spec)

        return specs

    @property
    def all_experiments_path(self):
        return os.path.join(self.root, workspace_all_experiments_file)

    def build_experiment_set(self):
        """Create an experiment set representing this workspace"""

        experiment_set = ramble.experiment_set.ExperimentSet(self)

        experiment_set.set_base_var('experiments_file', self.all_experiments_path)

        for app, workloads, app_vars, app_env_vars, app_ints, app_template, \
                app_chained_exps, app_mods in self.all_applications():
            experiment_set.set_application_context(app, app_vars, app_env_vars, app_ints,
                                                   app_template, app_chained_exps, app_mods)

            for workload, experiments, workload_vars, workload_env_vars, workload_ints, \
                    workload_template, workload_chained_exps, workload_mods \
                    in self.all_workloads(workloads):
                experiment_set.set_workload_context(workload, workload_vars,
                                                    workload_env_vars, workload_ints,
                                                    workload_template, workload_chained_exps,
                                                    workload_mods)

                for experiment, _, exp_vars, exp_env_vars, exp_matrices, exp_ints, \
                        exp_template, exp_chained_exps, exp_mods \
                        in self.all_experiments(experiments):
                    experiment_set.set_experiment_context(experiment,
                                                          exp_vars,
                                                          exp_env_vars,
                                                          exp_matrices,
                                                          exp_ints,
                                                          exp_template,
                                                          exp_chained_exps,
                                                          exp_mods)

        experiment_set.build_experiment_chains()

        return experiment_set

    def all_applications(self):
        """Iterator over applications

        Returns application, variables
        where variables are the platform level variables that
        should be applied.
        """

        ws_dict = self._get_workspace_dict()
        tty.debug(' With ws dict: %s' % (ws_dict))

        # Iterate over applications in ramble.yaml first
        app_dict = ramble.config.config.get_config('applications')

        for application, contents in app_dict.items():
            application_vars = None
            application_env_vars = None
            application_internals = None
            application_template = False
            application_chained_experiments = None
            application_modifiers = None

            if namespace.variables in contents:
                application_vars = contents[namespace.variables]

            if namespace.env_var in contents:
                application_env_vars = contents[namespace.env_var]

            if namespace.internals in contents:
                application_internals = contents[namespace.internals]

            if namespace.template in contents:
                application_template = contents[namespace.template]

            if namespace.chained_experiments in contents:
                application_chained_experiments = contents[namespace.chained_experiments]

            if namespace.modifiers in contents:
                application_modifiers = contents[namespace.modifiers]

            self.extract_success_criteria('application', contents)

            yield application, contents, application_vars, \
                application_env_vars, application_internals, \
                application_template, application_chained_experiments, \
                application_modifiers

        tty.debug('  Iterating over configs in directories...')
        # Iterate over applications defined in application directories
        # files after the ramble.yaml file is complete
        for app_conf in self.application_configs:
            config = self._get_application_dict_config(app_conf)
            if namespace.application not in config:
                tty.msg('No applications in config file %s'
                        % app_conf)
            app_dict = config[namespace.application]
            for application, contents in app_dict.items():
                application_vars = None
                application_env_vars = None
                application_internals = None
                application_template = False
                application_chained_experiments = None
                application_modifiers = None

                if namespace.variables in contents:
                    application_vars = \
                        contents[namespace.variables]

                if namespace.env_var in contents:
                    application_env_vars = contents[namespace.env_var]

                if namespace.internals in contents:
                    application_internals = contents[namespace.internals]

                if namespace.template in contents:
                    application_template = contents[namespace.template]

                if namespace.chained_experiments in contents:
                    application_chained_experiments = contents[namespace.chained_experiments]

                if namespace.modifiers in contents:
                    application_modifiers = contents[namespace.modifiers]

                self.extract_success_criteria('application', contents)
                yield application, contents, application_vars, \
                    application_env_vars, application_internals, \
                    application_template, application_chained_experiments, \
                    application_modifiers

    def all_workloads(self, application):
        """Iterator over workloads in an application dict

        Returns workload, variables
        where variables are the application level variables that
        should be applied.
        """

        if namespace.workload not in application:
            tty.msg('No workloads in application')
            return

        workloads = application[namespace.workload]

        for workload, contents in workloads.items():
            workload_variables = None
            workload_env_vars = None
            workload_internals = None
            workload_template = False
            workload_chained_experiments = None
            workload_modifiers = None
            if namespace.variables in contents:
                workload_variables = contents[namespace.variables]
            if namespace.env_var in contents:
                workload_env_vars = contents[namespace.env_var]
            if namespace.internals in contents:
                workload_internals = contents[namespace.internals]
            if namespace.template in contents:
                workload_template = contents[namespace.template]
            if namespace.chained_experiments in contents:
                workload_chained_experiments = contents[namespace.chained_experiments]
            if namespace.modifiers in contents:
                workload_modifiers = contents[namespace.modifiers]
            self.extract_success_criteria('workload', contents)

            yield workload, contents, workload_variables, \
                workload_env_vars, workload_internals, \
                workload_template, workload_chained_experiments, \
                workload_modifiers

    def all_experiments(self, workload):
        """Iterator over experiments in a workload dict

        Returns experiment, variables, and matrix/matrices
        Where variables are the workload level variables that
        should be applied.
        """

        if namespace.experiment not in workload:
            tty.msg('No experiments in workload')
            return

        experiments = workload[namespace.experiment]
        for experiment, contents in experiments.items():

            experiment_vars = syaml.syaml_dict()
            experiment_env_vars = None
            experiment_internals = None
            experiment_template = False
            experiment_chained_experiments = None
            experiment_modifiers = None

            if namespace.variables in contents:
                experiment_vars = contents[namespace.variables]

            if namespace.env_var in contents:
                experiment_env_vars = contents[namespace.env_var]

            if namespace.internals in contents:
                experiment_internals = contents[namespace.internals]

            if namespace.template in contents:
                experiment_template = contents[namespace.template]

            if namespace.chained_experiments in contents:
                experiment_chained_experiments = contents[namespace.chained_experiments]

            if namespace.modifiers in contents:
                experiment_modifiers = contents[namespace.modifiers]

            self.extract_success_criteria('experiment', contents)

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
                experiment_env_vars, matrices, experiment_internals, \
                experiment_template, experiment_chained_experiments, \
                experiment_modifiers

    def external_spack_env(self, env_name):
        env_context = self.software_environments.get_env(env_name)

        if namespace.external_env not in env_context:
            return None
        return env_context[namespace.external_env]

    def concretize(self):
        spack_dict = self.get_spack_dict()

        if 'concretized' in spack_dict and spack_dict['concretized']:
            raise RambleWorkspaceError('Cannot conretize an ' +
                                       'already concretized ' +
                                       'workspace')

        spack_dict = syaml.syaml_dict()
        spack_dict['concretized'] = False

        if namespace.packages not in spack_dict or \
                not spack_dict[namespace.packages]:
            spack_dict[namespace.packages] = syaml.syaml_dict()
        if namespace.environments not in spack_dict or \
                not spack_dict[namespace.environments]:
            spack_dict[namespace.environments] = syaml.syaml_dict()

        packages_dict = spack_dict[namespace.packages]
        environments_dict = spack_dict[namespace.environments]

        self.software_environments = \
            ramble.software_environments.SoftwareEnvironments(self)

        experiment_set = self.build_experiment_set()

        for exp, app_inst in experiment_set.all_experiments():
            app_inst.build_modifier_instances()
            env_name_str = app_inst.expander.expansion_str(ramble.keywords.Keywords.env_name)
            env_name = app_inst.expander.expand_var(env_name_str)

            compiler_dicts = [app_inst.default_compilers]
            for mod_inst in app_inst._modifier_instances:
                compiler_dicts.append(mod_inst.default_compilers)

            for compiler_dict in compiler_dicts:
                for comp, info in compiler_dict.items():
                    if comp not in packages_dict:
                        packages_dict[comp] = syaml.syaml_dict()
                        packages_dict[comp]['spack_spec'] = info['spack_spec']
                        ramble.config.add(f'spack:packages:{comp}:spack_spec:{info["spack_spec"]}',
                                          scope=self.ws_file_config_scope_name())
                        if 'compiler_spec' in info and info['compiler_spec']:
                            packages_dict[comp]['compiler_spec'] = info['compiler_spec']
                            config_path = f'spack:packages:{comp}:' + \
                                f'compiler_spec:{info["compiler_spec"]}'
                            ramble.config.add(config_path, scope=self.ws_file_config_scope_name())
                        if 'compiler' in info and info['compiler']:
                            packages_dict[comp]['compiler'] = info['compiler']
                            config_path = f'spack:packages:{comp}:' + \
                                f'compiler:{info["compiler"]}'
                            ramble.config.add(config_path, scope=self.ws_file_config_scope_name())
                    elif not specs_equiv(info, packages_dict[comp]):
                        tty.debug(f'  Spec 1: {str(info)}')
                        tty.debug(f'  Spec 2: {str(packages_dict[comp])}')
                        raise RambleConflictingDefinitionError(
                            f'Compiler {comp} defined in multiple conflicting ways'
                        )

            if env_name not in environments_dict:
                environments_dict[env_name] = syaml.syaml_dict()
                environments_dict[env_name][namespace.packages] = []

            tty.debug(f'Trying to define packages for {env_name}')
            app_packages = environments_dict[env_name][namespace.packages]

            software_dicts = [app_inst.software_specs]
            for mod_inst in app_inst._modifier_instances:
                software_dicts.append(mod_inst.software_specs)

            for software_dict in software_dicts:
                for spec_name, info in software_dict.items():
                    tty.debug(f'    Found spec: {spec_name}')
                    if spec_name not in packages_dict:
                        packages_dict[spec_name] = syaml.syaml_dict()
                        packages_dict[spec_name]['spack_spec'] = info['spack_spec']
                        if 'compiler_spec' in info and info['compiler_spec']:
                            packages_dict[spec_name]['compiler_spec'] = info['compiler_spec']
                        if 'compiler' in info and info['compiler']:
                            packages_dict[spec_name]['compiler'] = info['compiler']

                    elif not specs_equiv(info, packages_dict[spec_name]):
                        tty.debug(f'  Spec 1: {str(info)}')
                        tty.debug(f'  Spec 2: {str(packages_dict[spec_name])}')
                        raise RambleConflictingDefinitionError(
                            f'Package {spec_name} defined in multiple conflicting ways'
                        )

                    if spec_name not in app_packages:
                        app_packages.append(spec_name)

        spack_dict['concretized'] = True
        ramble.config.config.update_config('spack', spack_dict,
                                           scope=self.ws_file_config_scope_name())

        return

    def write_json_results(self):
        out_file = os.path.join(self.root, 'results.json')
        with open(out_file, 'w+') as f:
            sjson.dump(self.results, f)
        return out_file

    def upload_results(self):
        if ramble.config.get('config:upload'):
            # Read upload type and push it there
            if ramble.config.get('config:upload:type') == 'BigQuery':  # TODO: enum?
                formatted_data = ramble.experimental.uploader.format_data(self.results)

                # TODO: strategy object?
                uploader = ramble.experimental.uploader.BigQueryUploader()

                uri = ramble.config.get('config:upload:uri')
                if not uri:
                    tty.die('No upload URI (config:upload:uri) in config.')

                tty.msg('Uploading Results to ' + uri)
                uploader.perform_upload(uri, self.name, formatted_data)
            else:
                raise ConfigError("Unknown config:upload:type value")

        else:
            raise ConfigError("Missing correct conifg:upload parameters")

    def default_results(self):
        res = {}

        if self.workspace_hash:
            res['workspace_hash'] = self.workspace_hash
        else:
            try:
                with open(os.path.join(self.root, self._hash_file_name)) as f:
                    res['workspace_hash'] = f.readline().rstrip()
            except OSError:
                res['workspace_hash'] = "Unknown.."

        res['experiments'] = []

        return res

    def append_result(self, result):
        if not self.results:
            self.results = self.default_results()

        self.results['experiments'].append(result)

    def simlink_result(self, filename_base, latest_base, file_extension):
        """
        Create simlink of result file so that results.latest.txt always points
        to the most recent analysis. This clobbers the existing link
        """
        out_file = os.path.join(self.root, filename_base + file_extension)
        latest_file = os.path.join(self.root, latest_base + file_extension)

        if os.path.islink(latest_file):
            os.unlink(latest_file)

        os.symlink(out_file, latest_file)

    def dump_results(self, output_formats=['text']):
        """
        Write out result file in desired format

        This attempts to avoid the loss of previous results data by appending
        the datetime to the filename, but is willing to clobber the file
        results.latest.<extension>

        """
        if not self.results:
            self.results = {}

        results_written = []

        dt = self._date_string()
        inner_delim = '.'
        filename_base = 'results' + inner_delim + dt
        latest_base = 'results' + inner_delim + 'latest'

        if 'text' in output_formats:

            file_extension = '.txt'
            out_file = os.path.join(self.root, filename_base + file_extension)

            results_written.append(out_file)

            with open(out_file, 'w+') as f:
                f.write(f"From Workspace: {self.name} (hash: {self.results['workspace_hash']})\n")
                if 'experiments' in self.results:
                    for exp in self.results['experiments']:
                        f.write('Experiment %s figures of merit:\n' %
                                exp['name'])
                        f.write('  Status = %s\n' %
                                exp['RAMBLE_STATUS'])
                        if exp['RAMBLE_STATUS'] == 'SUCCESS' or self.always_print_foms:
                            for context in exp['CONTEXTS']:
                                f.write('  %s figures of merit:\n' %
                                        context['name'])
                                for fom in context['foms']:
                                    name = fom['name']
                                    if fom['origin_type'] == 'modifier':
                                        delim = '::'
                                        mod = fom['origin']
                                        name = f"{fom['origin_type']}{delim}{mod}{delim}{name}"

                                    output = '%s = %s %s' % (name,
                                                             fom['value'],
                                                             fom['units'])
                                    f.write('    %s\n' % (output.strip()))
                else:
                    tty.msg('No results to write')

            self.simlink_result(filename_base, latest_base, file_extension)

        if 'json' in output_formats:
            file_extension = '.json'
            out_file = os.path.join(self.root, filename_base + file_extension)
            results_written.append(out_file)
            with open(out_file, 'w+') as f:
                sjson.dump(self.results, f)
            self.simlink_result(filename_base, latest_base, file_extension)

        if 'yaml' in output_formats:
            file_extension = '.yaml'
            out_file = os.path.join(self.root, filename_base + file_extension)
            results_written.append(out_file)
            with open(out_file, 'w+') as f:
                syaml.dump(self.results, stream=f)
            self.simlink_result(filename_base, latest_base, file_extension)

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

    def create_mirror(self, mirror_root):
        parsed_url = url_util.parse(mirror_root)
        self._mirror_path = url_util.local_file_path(parsed_url)
        self._mirror_existed = web_util.url_exists(self._mirror_path)
        self._input_mirror_path = os.path.join(self._mirror_path, 'inputs')
        self._software_mirror_path = os.path.join(self._mirror_path, 'software')
        mirror_dirs = [self._mirror_path, self._input_mirror_path, self._software_mirror_path]
        for subdir in mirror_dirs:
            if not os.path.isdir(subdir):
                try:
                    fs.mkdirp(subdir)
                except OSError as e:
                    raise ramble.mirror.MirrorError(
                        "Cannot create directory '%s':" % subdir, str(e))

        self._software_mirror_stats = MirrorStats()
        self._input_mirror_stats = MirrorStats()
        self._input_mirror_cache = ramble.caches.MirrorCache(self._input_mirror_path)
        self._software_mirror_cache = ramble.caches.MirrorCache(self._software_mirror_path)

    def run_pipeline(self, pipeline):
        all_experiments_file = None
        experiment_set = ramble.experiment_set.ExperimentSet(self)
        self.software_environments = \
            ramble.software_environments.SoftwareEnvironments(self)

        if not self.is_concretized():
            error_message = 'Cannot run %s in a ' % pipeline + \
                            'non-conretized workspace\n' + \
                            'Run `ramble workspace concretize` on this ' + \
                            'workspace first.\n' + \
                            'Then ensure its spack configuration is ' + \
                            'properly configured.'
            tty.die(error_message)

        workspace_success = {
            namespace.success: ramble.config.config.get_config(namespace.success)
        }
        self.extract_success_criteria('workspace', workspace_success)

        if pipeline == 'setup':
            all_experiments_file = open(self.all_experiments_path, 'w+')
            all_experiments_file.write('#!/bin/sh\n')
            self._experiment_script = all_experiments_file

        experiment_set = self.build_experiment_set()

        for exp, app_inst in experiment_set.all_experiments():
            tty.debug('On experiment: %s' % exp)
            for phase in app_inst.get_pipeline_phases(pipeline):
                app_inst.run_phase(phase, self)

        if pipeline == 'setup':
            for exp, app_inst in sorted(experiment_set.all_experiments()):
                if not app_inst.is_template:
                    self.hash_inventory['experiments'].append(
                        {
                            'name': exp,
                            'digest': app_inst.experiment_hash,
                            'contents': app_inst.hash_inventory
                        }
                    )

            self.workspace_hash = ramble.util.hashing.hash_json(self.hash_inventory)

            with open(os.path.join(self.root, self._inventory_file_name), 'w+') as f:
                sjson.dump(self.hash_inventory, f)

            with open(os.path.join(self.root, self._hash_file_name), 'w+') as f:
                f.write(self.workspace_hash + '\n')

            all_experiments_file.close()

            all_experiments_path = os.path.join(self.root,
                                                workspace_all_experiments_file)
            os.chmod(all_experiments_path, stat.S_IRWXU | stat.S_IRWXG
                     | stat.S_IROTH | stat.S_IXOTH)
        elif pipeline == 'mirror':
            verb = "updated" if self._mirror_existed else "created"
            tty.msg(
                "Successfully %s spack software in %s" % (verb, self._mirror_path),
                "Archive stats:",
                "  %-4d already present"  % len(self._software_mirror_stats.present),
                "  %-4d added"            % len(self._software_mirror_stats.new),
                "  %-4d failed to fetch." % len(self._software_mirror_stats.errors))

            tty.msg(
                "Successfully %s inputs in %s" % (verb, self._mirror_path),
                "Archive stats:",
                "  %-4d already present"  % len(self._input_mirror_stats.present),
                "  %-4d added"            % len(self._input_mirror_stats.new),
                "  %-4d failed to fetch." % len(self._input_mirror_stats.errors))

            if self._input_mirror_stats.errors:
                tty.error("Failed downloads:")
                tty.colify(s.cformat("{name}") for s in list(self._input_mirror_stats.errors))
                tty.die('Mirroring has errors.')

    @property
    def experiments_script(self):
        return self._experiment_script

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
        for root, dirs, files in os.walk(self.config_dir):
            for name in files:
                src = os.path.join(self.config_dir, root, name)
                dest = src.replace(self.config_dir, archive_configs)
                fs.mkdirp(os.path.dirname(dest))
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
    def internal(self):
        """Whether this workspace is managed by Ramble."""
        wspath = get_workspace_path()
        return self.path.startswith(wspath)

    @property
    def name(self):
        """Human-readable representation of the workspace.

        The name of the workspace is the basename of its path
        """
        return os.path.basename(self.path)

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
    def auxiliary_software_dir(self):
        """Path to the auxiliary software files directory"""
        return os.path.join(self.config_dir, auxiliary_software_dir_name)

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
        for name, conf in self._templates.items():
            yield name, conf

    def all_auxiliary_software_files(self):
        """Iterator over each file in $workspace/configs/auxiliary_software_files"""
        for name, value in self._auxiliary_software_files.items():
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
        spack_dict = self.get_spack_dict()
        if 'concretized' in spack_dict:
            return (True if spack_dict['concretized']
                    else False)
        return False

    def _get_workspace_section(self, section):
        """Return a dict of a workspace section"""
        workspace_dict = self._get_workspace_dict()

        return workspace_dict[namespace.ramble][section] \
            if section in \
            workspace_dict[namespace.ramble] else syaml.syaml_dict()

    def get_workspace_vars(self):
        """Return a dict of workspace variables"""
        return ramble.config.config.get_config('variables')

    def get_workspace_env_vars(self):
        """Return a dict of workspace environment variables"""
        return ramble.config.config.get_config('env_vars')

    def get_workspace_internals(self):
        """Return a dict of workspace internals"""
        return ramble.config.config.get_config(namespace.internals)

    def get_workspace_modifiers(self):
        """Return a dict of workspace modifiers"""
        return ramble.config.config.get_config('modifiers')

    def get_spack_dict(self):
        """Return the spack dictionary for this workspace"""
        return ramble.config.config.get_config('spack')

    def get_applications(self):
        """Get the dictionary of applications"""
        tty.debug('Getting app dict.')
        tty.debug(' %s ' % self._get_workspace_dict())
        workspace_dict = self._get_workspace_dict()
        if namespace.application not in workspace_dict[namespace.ramble]:
            workspace_dict[namespace.ramble][namespace.application] = \
                syaml.syaml_dict()
        return workspace_dict[namespace.ramble][namespace.application]

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

    def check_cache(self, tupl):
        return self.install_cache.contains(tupl)

    def add_to_cache(self, tupl):
        self.install_cache.add(tupl)


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
    env_var = None
    if ramble_workspace_var in os.environ.keys():
        env_var = os.environ[ramble_workspace_var]
        del os.environ[ramble_workspace_var]

    try:
        deactivate()
        yield
    finally:
        if ws:
            os.environ[ramble_workspace_var] = env_var
            activate(ws)


class RambleWorkspaceError(ramble.error.RambleError):
    """Superclass for all errors to do with Ramble Workspaces"""


class RambleInvalidTemplateNameError(ramble.error.RambleError):
    """Error when an invalid template name is provided"""


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
