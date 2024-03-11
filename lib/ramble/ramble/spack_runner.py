# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""
Spack environments house software stacks.

This module contains classes and methods that will help manage a spack
environment by calling an externally available spack.
"""

import os
import re
import shutil
import shlex

import llnl.util.filesystem as fs
from spack.util.executable import CommandNotFoundError, ProcessError
from ramble.util.executable import which
import spack.util.spack_yaml as syaml

import ramble.config
import ramble.error
import ramble.util.hashing
from ramble.util.logger import logger

spack_namespace = 'spack'

package_name_regex = re.compile(r"\s*(?P<package_name>[\w][\w-]+).*")


class SpackRunner(object):
    """Runner for executing several spack commands

    The SpackRunner class is primarily used to manage spack environments
    for executing experiments under.

    This class provides methods for creating and manaving spack environments,
    and for ensuring required compilers are installed. It also provides a
    method for generating variables that can be used to ensure a spack env
    is loaded within an execution script.
    """
    env_key = 'SPACK_ENV'

    global_config_name = 'config:spack:global'
    install_config_name = 'config:spack:install'
    compiler_find_config_name = 'config:spack:compiler_find'
    buildcache_config_name = 'config:spack:buildcache'
    concretize_config_name = 'config:spack:concretize'
    env_create_config_name = 'config:spack:env_create'

    env_create_args = [
        'env',
        'create',
        '-d',
        '.'
    ]

    compiler_find_args = ['compiler', 'find']

    _allowed_config_files = ['compilers.yaml', 'concretizer.yaml',
                             'mirrors.yaml', 'repos.yaml',
                             'packages.yaml', 'modules.yaml',
                             'config.yaml', 'upstreams.yaml',
                             'bootstrap.yaml', 'spack.yaml',
                             'spack_includes.yaml']

    def __init__(self, shell='bash', dry_run=False):
        """
        Ensure spack is found in the path, and setup some default variables.
        """
        try:
            self.spack = which('spack', required=True)
        except CommandNotFoundError:
            raise RunnerError("Spack command is not found in path")

        # Add default arguments to spack command.
        # This allows us to inject custom config scope dirs
        # primarily for unit testing.
        global_args = ramble.config.get(f'{self.global_config_name}:flags')
        if global_args is not None:
            for arg in shlex.split(global_args):
                self.spack.add_default_arg(arg)

        self.spack_dir = os.path.dirname(os.path.dirname(self.spack.exe[0]))
        self.shell = shell

        if self.shell == 'bash':
            script = 'setup-env.sh'
        elif self.shell == 'csh':
            script = 'setup-env.csh'
        elif self.shell == 'fish':
            script = 'setup-env.fish'
        self.source_script = os.path.join(self.spack_dir,
                                          'share', 'spack', script)

        self.concretized = False
        self.hash = None
        self.env_path = None
        self.active = False
        self.compilers = []
        self.includes = []
        self.dry_run = dry_run
        self.compiler_config_dir = None
        self.configs = []
        self.configs_applied = False

        self.installer = self.spack.copy()
        self.installer.add_default_prefix(ramble.config.get(f'{self.install_config_name}:prefix'))
        self.installer.add_default_arg('install')

        self.concretizer = self.spack.copy()
        self.concretizer.add_default_prefix(
            ramble.config.get(f'{self.concretize_config_name}:prefix')
        )
        self.concretizer.add_default_arg('concretize')

    def get_version(self):
        """Get spack's version"""
        from ramble.main import get_git_hash
        import importlib.util

        version_spec = importlib.util.spec_from_file_location(
            'spack_version',
            os.path.join(self.spack_dir,
                         'lib', 'spack',
                         'spack', '__init__.py')
        )
        version_mod = importlib.util.module_from_spec(version_spec)
        version_spec.loader.exec_module(version_mod)

        spack_version = version_mod.spack_version
        spack_hash = get_git_hash(path=self.spack_dir)

        if spack_hash:
            spack_version += f' ({spack_hash})'

        return spack_version

    def set_dry_run(self, dry_run=False):
        """
        Set the dry_run state of this spack runner
        """
        self.dry_run = dry_run

    def set_compiler_config_dir(self, path=None):
        """
        Set the config path to use when installing compilers
        """
        self.compiler_config_dir = path

    def set_env(self, env_path, require_exists=True):
        if require_exists:
            if not os.path.isdir(env_path) or \
                    not os.path.exists(os.path.join(env_path, 'spack.yaml')):
                logger.die(f'Path {env_path} is not a spack environment')

        self.env_path = env_path

    def generate_source_command(self, shell='bash'):
        """
        Generate a string to source spack into an environment
        """

        commands = ['. %s' % self.source_script]

        return commands

    def generate_activate_command(self, shell='bash'):
        """
        Generate a string to activate a spack environment
        """

        commands = []
        if self.active:
            commands.append('spack env activate %s' % self.env_path)

        return commands

    def generate_deactivate_command(self, shell='bash'):
        """
        Generate a string to deactivate a spack environment
        """

        commands = []

        if self.active:
            commands.append('spack env deactivate')

        return commands

    def configure_env(self, path):
        """
        Configured the spack environment path for subsequent spack commands
        """

        # Ensure subsequent commands use the created env now.
        self.env_path = path

    def add_config(self, config):
        """
        Add a config option to this spack environment.
        """
        self.configs.append(config)

    def create_env(self, path, output=None, error=None):
        """
        Ensure a spack environment is created, and set the path to it within
        this runner.
        """
        if os.path.exists(path) and not os.path.isdir(path):
            raise RunnerError('Unable to create environment %s' % path)

        if not os.path.exists(path):
            fs.mkdirp(path)

        # Create a spack env
        if not self.dry_run:
            if not os.path.exists(os.path.join(path, 'spack.yaml')):
                env_create_flags = ramble.config.get(f'{self.env_create_config_name}:flags')
                env_create_args = self.env_create_args.copy()
                if env_create_flags:
                    for flag in shlex.split(env_create_flags):
                        env_create_args.append(flag)
                with fs.working_dir(path):
                    self._run_command(self.spack, env_create_args)

        # Ensure subsequent commands use the created env now.
        self.env_path = path

    def load_compiler(self, spec):
        """
        Add commands to load a package to the executable
        """
        if self.shell == 'bash':
            regex = \
                re.compile('\A.*export ' +  # noqa: W605
                           '(?P<var>[\S^=]+)=' +  # noqa: W605
                           '(?P<val>[\S]+);\Z')  # noqa: W605

            shell_flag = '--sh'
        elif self.shell == 'csh':
            regex = \
                re.compile('\A.*setenv ' +  # noqa: W605
                           '(?P<var>[\S^=]+) ' +  # noqa: W605
                           '(?P<val>[\S]+);\Z')  # noqa: W605
            shell_flag = '--csh'
        elif self.shell == 'fish':
            regex = \
                re.compile('\A.*set -gx ' +  # noqa: W605
                           '(?P<var>[\S^=]+) ' +  # noqa: W605
                           '(?P<val>[\S]+);\Z')  # noqa: W605
            shell_flag = '--fish'
        else:
            raise RunnerError('Shell %s not supported' % self.shell)

        self._load_compiler_shell(spec, shell_flag, regex)

    def _load_compiler_shell(self, spec, shell_flag, regex):
        args = [
            'load',
            shell_flag,
            spec
        ]

        if not self.dry_run:
            load_cmds = self._run_command(self.spack,
                                          args,
                                          return_output=True).split('\n')

            for cmd in load_cmds:
                env_var = regex.match(cmd)
                if env_var:
                    self.spack.add_default_env(env_var.group('var'),
                                               env_var.group('val'))
                    self.installer.add_default_env(env_var.group('var'),
                                                   env_var.group('val'))
                    self.concretizer.add_default_env(env_var.group('var'),
                                                     env_var.group('val'))
        else:
            self._dry_run_print(self.spack, args)

    def install_compiler(self, spec):
        """
        Ensure a compiler is installed, before using it to install packages
        within an environment.

        This command always executes outside of an environment.

        If it is executed within an environment, then it adds the compiler to
        the list of environment specs. This can cause conflicts if an
        incompatible package is explicitly added to the environment later.

        Also, if it is added to an environment, sometimes it will cause a
        compiler to be installed multiple times with different base compilers.
        """
        active_env = None
        if self.active:
            active_env = self.spack.default_env[self.env_key]
            if self.env_key in self.spack.default_env:
                del self.spack.default_env[self.env_key]
                del self.installer.default_env[self.env_key]
                del self.concretizer.default_env[self.env_key]

        comp_info_args = []
        if self.compiler_config_dir:
            comp_info_args.extend(['-C', self.env_path])
        comp_info_args.extend(['compiler', 'info', spec])

        compiler_find_flags = ramble.config.get(f'{self.compiler_find_config_name}:flags')
        compiler_find_args = self.compiler_find_args.copy()
        if compiler_find_flags:
            for flag in shlex.split(compiler_find_flags):
                compiler_find_args.append(flag)
        if not self.dry_run:
            self._run_command(self.spack, compiler_find_args)

        try:
            self._cmd_start(self.spack, comp_info_args)
            self.spack(*comp_info_args, output=os.devnull, error=os.devnull)
            self._cmd_end(self.spack, comp_info_args)
            logger.msg(f'{spec} is already an available compiler')
            return
        except ProcessError:

            args = []

            install_flags = ramble.config.get(f'{self.install_config_name}:flags')
            if install_flags is not None:
                for flag in shlex.split(install_flags):
                    args.append(flag)

            args.append(spec)

            if not self.dry_run:
                self._run_command(self.installer, args)
            else:
                self._dry_run_print(self.installer, args)

            self.load_compiler(spec)

            if not self.dry_run:
                self._run_command(self.spack, compiler_find_args)

                self.compilers.append(spec)

                if self.active:
                    self.spack.add_default_env(self.env_key, active_env)
                    self.installer.add_default_env(self.env_key, active_env)
                    self.concretizer.add_default_env(self.env_key, active_env)
            else:
                self._dry_run_print(self.spack, compiler_find_args)

    def activate(self):
        """
        Ensure the spack environment is active in subsequent commands.
        """
        if not self.env_path:
            raise NoPathRunnerError('Environment runner has no ' +
                                    'path congfigured')

        self.spack.add_default_env(self.env_key, self.env_path)
        self.installer.add_default_env(self.env_key, self.env_path)
        self.concretizer.add_default_env(self.env_key, self.env_path)

        self.env_contents = []

        self.active = True

    def deactivate(self):
        """
        Ensure the spack environment is not active in subsequent commands.
        """
        if not self.env_path:
            raise NoPathRunnerError('Environment runner has no ' +
                                    'path congfigured')

        if self.active and self.env_key in self.spack.default_env.keys():
            del self.spack.default_env[self.env_key]
            del self.installer.default_env[self.env_key]
            del self.concretizer.default_env[self.env_key]
            self.active = False

    def _check_active(self):
        if not self.env_path:
            raise NoPathRunnerError('Environment runner has no ' +
                                    'path congfigured')

        if not self.active:
            raise NoActiveEnvironmentError('Runner has no active ' +
                                           'environment to work with.')

    def add_spec(self, spec):
        """
        Add a spec to the spack environment.

        This command requires an active spack environment.
        """
        self._check_active()

        if spec not in self.env_contents:
            self.env_contents.append(spec)

    def added_packages(self):
        """
        Return a list of base package names that are added to an environment
        """
        self._check_active()

        args = [
            'find'
        ]

        pkg_names = []

        all_packages = self._run_command(self.spack,
                                         args,
                                         return_output=True).split('\n')
        for pkg in all_packages:
            match = package_name_regex.match(pkg)
            if match:
                pkg_names.append(match.group('package_name'))

        return pkg_names

    def add_include_file(self, include_file):
        """
        Add an include file to this spack environment.

        This file needs to be a config section supported by spack, otherwise
        spack will error. So, we validate against a list of supported sections.
        """

        file_name = os.path.basename(include_file)
        if file_name in self._allowed_config_files:
            self.includes.append(include_file)

    def apply_configs(self):
        """
        Add all defined configs to the environment
        """

        if self.configs_applied:
            return

        self._check_active()

        config_args = [
            'config',
            'add'
        ]

        for config in self.configs:
            args = config_args.copy()
            args.append(config)

            self._run_command(self.spack, args)
            if self.dry_run:
                self._dry_run_print(self.spack, args)

        self.configs_applied = True

    def copy_from_external_env(self, env_name_or_path):
        """
        Copy an external spack environment file into the generated environment.

        env_name_or_path can be either:
         - Name of a named spack environment
         - Path to an external spack environment

         Sets self.concretized if a spack.lock file is found in the env

         Args:
         - env_name_or_path: Name or path to existing spack environment
        """

        self._check_active()

        named_location_args = [
            'location',
            '-e',
            env_name_or_path
        ]

        # If the path doesn't exist, check if it's a named environment
        path = env_name_or_path
        if not os.path.exists(path):
            try:
                path = self._run_command(self.spack, named_location_args, return_output=True)
            # If a named environment fails, copy directly from the path
            except ProcessError:
                raise InvalidExternalEnvironment(f'{path} is not a spack environment.')

        found_lock = False

        lock_file = os.path.join(path, 'spack.lock')
        if os.path.exists(lock_file):
            found_lock = True
            shutil.copyfile(lock_file, os.path.join(self.env_path, 'spack.lock'))

        conf_file = os.path.join(path, 'spack.yaml')
        if not os.path.exists(conf_file):
            raise InvalidExternalEnvironment(f'{path} is not a spack environment.')

        shutil.copyfile(conf_file, os.path.join(self.env_path, 'spack.yaml'))

        if self.configs:
            self.apply_configs()

        self.concretized = found_lock

    def _env_file_dict(self):
        """Construct a dictionary with the env file contents in it"""
        env_file = syaml.syaml_dict()
        env_file[spack_namespace] = syaml.syaml_dict()
        env_file[spack_namespace]['concretizer'] = syaml.syaml_dict()
        env_file[spack_namespace]['concretizer']['unify'] = True

        env_file[spack_namespace]['specs'] = syaml.syaml_list()
        env_file[spack_namespace]['specs'].extend(self.env_contents)

        env_file[spack_namespace]['include'] = self.includes

        return env_file

    def generate_env_file(self):
        """
        Generate a spack environment file
        """
        self._check_active()

        env_file = self._env_file_dict()

        spack_env_file = os.path.join(self.env_path, 'spack.yaml')
        spack_lock_file = os.path.join(self.env_path, 'spack.lock')

        # Check that a spack.yaml and spack.lock file exist already
        if os.path.exists(spack_env_file) and os.path.exists(spack_lock_file):
            existing_env_mtime = os.path.getmtime(spack_env_file)
            existing_lock_mtime = os.path.getmtime(spack_lock_file)

            # If the lock file was last modified after the yaml file...
            if existing_lock_mtime > existing_env_mtime:
                env_data = syaml.load_config(syaml.dump_config(env_file, default_flow_style=False))
                with open(spack_env_file, 'r') as f:
                    existing_data = syaml.load_config(f)
                gen_env_hash = ramble.util.hashing.hash_json(env_data)
                existing_env_hash = ramble.util.hashing.hash_json(existing_data)

                # If the yaml hash matches the new generated data hash...
                if gen_env_hash == existing_env_hash:
                    self.concretized = True
                    logger.msg(f'Environment {self.env_path} will not be regenerated.')
                    return

            if not self.concretized:
                logger.verbose(f'Removing invalid spack lock file {spack_lock_file}')
                fs.force_remove(spack_lock_file)

        spack_hash = self.inventory_hash()

        # Write spack.yaml to environment before concretizing, and its hash
        with open(os.path.join(self.env_path, 'spack.yaml'), 'w+') as f:
            syaml.dump_config(env_file, f, default_flow_style=False)

        with open(os.path.join(self.env_path, 'ramble.hash'), 'w+') as f:
            f.write(spack_hash)

        if self.configs:
            self.apply_configs()

    def concretize(self):
        """
        Concretize a spack environment.

        This command requires an active spack environment.
        """
        self._check_active()

        if self.concretized:
            logger.msg(
                f'Environment {self.env_path} is already concretized. Skipping concretize...'
            )
            return

        concretize_flags = ramble.config.get(f'{self.concretize_config_name}:flags')

        args = []
        if concretize_flags is not None:
            args.extend(shlex.split(concretize_flags))

        if not self.dry_run:
            self._run_command(self.concretizer, args)
        else:
            self._dry_run_print(self.concretizer, args)

        self.concretized = True

    def inventory_hash(self):
        """
        Create a hash of the spack.lock file for ramble inventory purposes

        This command requires an active spack environment.
        """
        self._check_active()

        env_data = syaml.load_config(syaml.dump_config(self._env_file_dict(),
                                                       default_flow_style=False))
        self.hash = ramble.util.hashing.hash_json(env_data)

        return self.hash

    def install(self):
        """
        Install spack packages that have been added to an environment.

        This command requires an active spack environment.
        """
        self._check_active()

        install_flags = ramble.config.get(f'{self.install_config_name}:flags')

        args = []

        if install_flags is not None:
            args.extend(shlex.split(install_flags))

        if not self.dry_run:
            self._run_command(self.installer, args)
        else:
            self._dry_run_print(self.installer, args)

    def get_package_path(self, package_spec):
        """Return the installation directory for a package"""
        loc_args = ['location', '-i']
        loc_args.extend(shlex.split(package_spec))

        name_args = ['find', '--format={name}']
        name_args.extend(shlex.split(package_spec))

        if not self.dry_run:
            name = self._run_command(self.spack, name_args, return_output=True).strip()
            location = self._run_command(self.spack, loc_args, return_output=True).strip()
            return (name, location)
        else:
            self._dry_run_print(self.spack, name_args)
            self._dry_run_print(self.spack, loc_args)

            name = os.path.join(shlex.split(package_spec)[0])
            location = os.path.join('dry-run', 'path', 'to', shlex.split(package_spec)[0])
            return (name, location)

    def mirror_environment(self, mirror_path):
        """Create a spack mirror from the activated environment"""
        self._check_active()

        args = [
            "mirror",
            "create",
            "--all",  # All packages in the environment
            "-D",  # Include dependencies
            "-d",
            mirror_path
        ]

        if not self.dry_run:
            out_str = self._run_command(self.spack, args, return_output=True).strip()
            return out_str
        else:
            self._dry_run_print(self.spack, args)
            return """
  %-4d already present
  %-4d added
  %-4d failed to fetch.""" % (0, 0, 0)

    def get_env_hash_list(self):
        self._check_active()
        args = [
            'find',
            '--format',
            '/{hash}'
        ]
        output = self._run_command(self.spack, args, return_output=True).strip().replace('\n', ' ')
        return output

    def push_to_spack_cache(self, spack_cache_path):
        """Push packages for a given env to the spack cache"""
        self._check_active()

        hash_list = self.get_env_hash_list()

        args = [
            "buildcache",
            "push"
        ]
        user_flags = ramble.config.get(f'{self.buildcache_config_name}:flags')

        logger.debug(f"Running with user flags: {user_flags}")

        if user_flags is not None:
            args.extend(shlex.split(user_flags))

        args.extend([spack_cache_path, hash_list])

        if not self.dry_run:
            out_str = self._run_command(self.spack, args, return_output=True).strip()
            return out_str
        else:
            self._dry_run_print(self.spack, args)
            return

    def validate_command(self, command='', validation_type='not_empty', regex=None):
        regex_validations = ['contains_regex', 'does_not_contain_regex']

        args = command.split()

        compiled_regex = None
        if validation_type in regex_validations and regex:
            compiled_regex = re.compile(regex)

        if not self.dry_run:
            output = self._run_command(self.spack, args,
                                       return_output=True)

            logger.debug(' Validation output:')
            logger.debug(output)
            if validation_type == 'empty':
                if output != '':
                    self._raise_validation_error(command, validation_type)
            elif validation_type == 'not_empty':
                if output == '':
                    self._raise_validation_error(command, validation_type)
            elif validation_type == 'contains_regex':
                found = False
                for line in output.split('\n'):
                    if compiled_regex.match(line):
                        found = True
                if not found:
                    self._raise_validation_error(command, validation_type)
            elif validation_type == 'does_not_contain_regex':
                for line in output.split('\n'):
                    if compiled_regex.match(line):
                        self._raise_validation_error(command, validation_type)
        else:
            self._dry_run_print(self.spack, args)

    def _raise_validation_error(self, command, validation_type):
        raise ValidationFailedError(
            f'Validation of: "spack {command}" failed '
            f' with a validation_type of "{validation_type}"'
        )

    def _dry_run_print(self, executable, args):
        logger.msg(f'DRY-RUN: would run {executable}')
        logger.msg(f'         with args: {args}')

    def _cmd_start(self, executable, args):
        logger.msg('')
        logger.msg('*******************************************')
        logger.msg('********** Running Spack Command **********')
        logger.msg(f'**     command: {executable}')
        if args:
            logger.msg(f'**     with args: {args}')
        logger.msg('*******************************************')
        logger.msg('')

    def _cmd_end(self, executable, args):
        logger.msg('')
        logger.msg('*******************************************')
        logger.msg('***** Finished Running Spack Command ******')
        logger.msg('*******************************************')
        logger.msg('')

    def _run_command(self, executable, args, return_output=False):
        active_stream = logger.active_stream()
        active_log = logger.active_log()
        error = False

        self._cmd_start(executable, args)
        try:
            if active_stream is None:
                if return_output:
                    out_str = executable(*args, output=str)
                else:
                    executable(*args)
            else:
                if return_output:
                    out_str = executable(*args, output=str, error=active_stream)
                else:
                    executable(*args, output=active_stream, error=active_stream)
        except ProcessError as e:
            logger.error(e)
            error = True
            pass

        if error:
            err = f'Error running spack command: {executable} ' + ' '.join(args)
            if active_stream is None:
                logger.die(err)
            else:
                logger.error(err)
                logger.die(f'For more details, see the log file: {active_log}')

        self._cmd_end(executable, args)

        if return_output:
            return out_str
        return


class RunnerError(ramble.error.RambleError):
    """Raised when a problem occurs with a spack environment"""


class NoPathRunnerError(ramble.error.RambleError):
    """Raised when a runner is used that does not have a path set"""


class NoActiveEnvironmentError(RunnerError):
    """Raised when an environment command is executed without an active
    environment."""


class InvalidExternalEnvironment(RunnerError):
    """Raised when an invalid external spack environment is passed in"""


class ValidationFailedError(RunnerError):
    """Raised when a package manager requirement was not met"""
