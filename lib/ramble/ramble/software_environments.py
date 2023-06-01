# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import llnl.util.tty as tty

import ramble.repository
import ramble.workspace
import ramble.keywords
import ramble.error
import ramble.renderer
import ramble.expander
from ramble.namespace import namespace


class SoftwareEnvironments(object):
    """Class to represent a set of software environments

    This class contains logic to take the dictionary representations of
    software environments, and unify their format.
    """

    keywords = ramble.keywords.keywords

    supported_confs = ['v1', 'v2']

    def __init__(self, workspace):

        self._raw_packages = {}
        self._packages = {}
        self._package_map = {}
        self._raw_environments = {}
        self._environments = {}
        self._environment_map = {}
        self._workspace = workspace
        self.spack_dict = self._workspace.get_spack_dict().copy()

        conf_type = self._detect_conf_type()

        if conf_type not in self.supported_confs:
            raise RambleSoftwareEnvironmentError(
                f'Software configuration type {conf_type} is not one of ' +
                f'{str(self.supported_confs)}'
            )

        setup_method = getattr(self, f'_{conf_type}_setup')
        setup_method()

    def _detect_conf_type(self):
        """Auto-detect the type of configuration provided.

        Default configuration type is v2.

        v1 configurations follow the format:

        spack:
          concretized: [true/false]
          applications: {}
          compilers: {}
          mpi_libraries: {}

        v2 configurations follow the format:

        spack:
          concretized: [true/false]
          packages: {}
          environments: {}
        """

        conf_type = 'invalid'

        if namespace.application in self.spack_dict or \
                namespace.compilers in self.spack_dict or \
                namespace.mpi_lib in self.spack_dict:
            conf_type = 'v1'
        if namespace.packages in self.spack_dict and \
                namespace.environments in self.spack_dict:
            conf_type = 'v2'

        tty.debug(f'Detected config type of: {conf_type}')

        return conf_type

    def _v1_setup(self):
        """Process a v1 `spack:` dictionary in the workspace configuration."""
        tty.debug('Performing v1 software setup.')
        tty.warn('Your workspace configuration uses the v1 format for the spack section')
        tty.warn('Please update to the latest format to ensure it keeps functioning properly.')
        tty.warn('v1 support will be removed in the future.')

        if namespace.compilers in self.spack_dict:
            for compiler, conf in self.spack_dict[namespace.compilers].items():
                self._packages[compiler] = {}
                self._package_map[compiler] = [compiler]

                spec_dict = self.get_named_spec(compiler)
                self._packages[compiler][namespace.spack_spec] = self.spec_string(spec_dict)
                self._packages[compiler][namespace.compiler_spec] = \
                    self.spec_string(spec_dict, use_custom_specifier=True)

        if namespace.mpi_lib in self.spack_dict:
            for mpi, conf in self.spack_dict[namespace.mpi_lib].items():
                self._packages[mpi] = {}
                self._package_map[mpi] = [mpi]

                spec_dict = self.get_named_spec(mpi, 'mpi_library')
                self._packages[mpi][namespace.spack_spec] = self.spec_string(spec_dict)

        if namespace.application in self.spack_dict:
            for env, pkgs in self.spack_dict[namespace.application].items():
                self._environment_map[env] = [env]
                self._environments[env] = {}
                self._environments[env][namespace.packages] = []
                self._environments[env][namespace.compilers] = []
                self._environments[env][namespace.external_env] = None

                if namespace.external_env in pkgs:
                    self._environments[env][namespace.external_env] = \
                        pkgs[namespace.external_env]

                for pkg, conf in pkgs.items():
                    if pkg != namespace.external_env:
                        self._packages[pkg] = {}
                        self._package_map[pkg] = [pkg]
                        spec_dict = self.get_named_spec(pkg, spec_context=env)
                        self._packages[pkg][namespace.spack_spec] = self.spec_string(spec_dict)
                        self._environments[env][namespace.packages].append(pkg)

                        if 'compiler' in conf:
                            self._environments[env][namespace.compilers].append(
                                conf['compiler']
                            )
                            self._packages[pkg]['compiler'] = conf['compiler']

                        if 'mpi' in conf:
                            self._environments[env][namespace.packages].append(
                                conf['mpi']
                            )
        self._raw_packages = self._packages
        self._raw_environments = self._environments

    def _v2_setup(self):
        """Process a v2 `spack:` dictionary in the workspace configuration."""
        tty.debug('Performing v2 software setup.')

        pkg_renderer = ramble.renderer.Renderer('package')
        env_renderer = ramble.renderer.Renderer('environment')

        expander = ramble.expander.Expander({}, None)

        if namespace.packages in self.spack_dict:
            for pkg_template, pkg_info in self.spack_dict[namespace.packages].items():
                self._raw_packages[pkg_template] = pkg_info
                self._package_map[pkg_template] = []
                pkg_vars = {}
                pkg_matrices = []

                if namespace.variables in pkg_info:
                    pkg_vars = pkg_info[namespace.variables].copy()

                if namespace.matrices in pkg_info:
                    pkg_matrices = pkg_info[namespace.matrices].copy()

                if namespace.matrix in pkg_info:
                    pkg_matrices.append(pkg_info[namespace.matrix].copy())

                pkg_vars['package_name'] = pkg_template

                for rendered_vars in pkg_renderer.render_objects(pkg_vars, pkg_matrices):
                    expansion_str = expander.expansion_str('package_name')
                    final_name = expander.expand_var(expansion_str,
                                                     extra_vars=rendered_vars)
                    self._packages[final_name] = {}
                    self._package_map[pkg_template].append(final_name)

                    spack_spec = expander.expand_var(pkg_info['spack_spec'],
                                                     extra_vars=rendered_vars)
                    self._packages[final_name]['spack_spec'] = spack_spec

                    if 'compiler_spec' in pkg_info:
                        comp_spec = expander.expand_var(pkg_info['compiler_spec'],
                                                        extra_vars=rendered_vars)
                        self._packages[final_name]['compiler_spec'] = comp_spec

                    if 'compiler' in pkg_info:
                        comp = expander.expand_var(pkg_info['compiler'],
                                                   extra_vars=rendered_vars)
                        self._packages[final_name]['compiler'] = comp

        if namespace.environments in self.spack_dict:
            for env_template, env_info in self.spack_dict[namespace.environments].items():
                env_vars = {}
                env_matrices = []
                self._raw_environments[env_template] = env_info
                self._environment_map[env_template] = []

                if namespace.variables in env_info:
                    env_vars = env_info[namespace.variables].copy()

                if namespace.matrices in env_info:
                    env_matrices = env_info[namespace.matrices].copy()

                if namespace.matrix in env_info:
                    env_matrices.append(env_info[namespace.matrix].copy())

                env_vars['environment_name'] = env_template

                for rendered_vars in env_renderer.render_objects(env_vars, env_matrices):
                    expansion_str = expander.expansion_str('environment_name')
                    final_name = expander.expand_var(expansion_str,
                                                     extra_vars=rendered_vars)
                    self._environment_map[env_template].append(final_name)

                    self._environments[final_name] = {}

                    if namespace.external_env in env_info:
                        external_env = expander.expand_var(env_info[namespace.external_env],
                                                           extra_vars=rendered_vars)
                        self._environments[final_name][namespace.external_env] = \
                            external_env

                    if namespace.packages in env_info:
                        self._environments[final_name][namespace.packages] = []
                        env_packages = self._environments[final_name][namespace.packages]

                        for pkg_name in env_info[namespace.packages]:
                            expanded_pkg = expander.expand_var(pkg_name,
                                                               extra_vars=rendered_vars)
                            env_packages.append(expanded_pkg)

    def get_env(self, environment_name):
        """Return a reference to the environment definition"""
        if environment_name not in self._environments:
            raise RambleSoftwareEnvironmentError(
                f'Environment {environment_name} is not defined.'
            )

        return self._environments[environment_name]

    def get_spec_string(self, package_name):
        """Return the full spec string given a package name"""
        if package_name not in self._packages:
            raise RambleSoftwareEnvironmentError(
                f'Package {package_name} is not defined.'
            )

        spec_string = self._packages[package_name]['spack_spec']
        compiler_str = ''
        if 'compiler' in self._packages[package_name]:
            comp_name = self._packages[package_name]['compiler']
            comp_spec = self.get_spec(comp_name)
            compiler_str = f' %{comp_spec["spack_spec"]}'
            if 'compiler_spec' in comp_spec:
                compiler_str = f' %{comp_spec["compiler_spec"]}'
        return spec_string + compiler_str

    def get_spec(self, package_name):
        """Return a single spec given its name"""
        if package_name not in self._packages:
            raise RambleSoftwareEnvironmentError(
                f'Package {package_name} is not defined.'
            )

        return self._packages[package_name]

    def get_env_packages(self, environment_name):
        """Return all of the packages used by an environment"""
        if environment_name not in self._environments:
            raise RambleSoftwareEnvironmentError(
                f'Environment {environment_name} is not defined.'
            )

        if namespace.packages in self._environments[environment_name]:
            for name in self._environments[environment_name][namespace.packages]:
                yield name

    def _require_raw_package(self, pkg):
        """Raise an error if the raw package is not defined"""
        if pkg not in self._raw_packages.keys():
            raise RambleSoftwareEnvironmentError(
                f'Package {pkg} is not defined.'
            )

    def _require_raw_environment(self, env):
        """Raise an error if the raw environment is not defined"""
        if env not in self._raw_environments.keys():
            raise RambleSoftwareEnvironmentError(
                f'Environment {env} is not defined.'
            )

    def all_packages(self):
        """Yield each package name"""
        for pkg in self._packages.keys():
            yield pkg

    def all_raw_packages(self):
        """Yield each raw package name"""
        for pkg in self._raw_packages.keys():
            yield pkg

    def raw_package_info(self, raw_pkg):
        """Return the information for a raw package"""
        self._require_raw_package(raw_pkg)

        return self._raw_packages[raw_pkg]

    def mapped_packages(self, raw_pkg):
        """Yield each package rendered from a raw package"""
        self._require_raw_package(raw_pkg)

        for pkg in self._package_map[raw_pkg]:
            yield pkg

    def all_environments(self):
        """Yield each environment name"""
        for env in self._environments.keys():
            yield env

    def all_raw_environments(self):
        """Yield raw environment names"""
        for env in self._raw_environments.keys():
            yield env

    def raw_environment_info(self, env):
        """Return the information for a raw environment"""
        if env not in self._raw_environments.keys():
            raise RambleSoftwareEnvironmentError(
                f'Environment {env} is not defined.'
            )

        return self._raw_environments[env]

    def mapped_environments(self, raw_env):
        """Yield each environment rendered from a raw environment"""
        self._require_raw_environment(raw_env)

        for env in self._environment_map[raw_env]:
            yield env

    def get_named_spec(self, spec_name, spec_context='compiler'):
        """Extract a named spec from a v1 spack dictionary"""
        if spec_context == 'compiler':
            if namespace.compilers not in self.spack_dict:
                raise RambleSoftwareEnvironmentError('No compilers ' +
                                                     'defined in workspace')
            spec_dict = self.spack_dict[namespace.compilers]
        elif spec_context == 'mpi_library':
            if namespace.mpi_lib not in self.spack_dict:
                raise RambleSoftwareEnvironmentError('No MPI libraries ' +
                                                     'defined in workspace')
            spec_dict = self.spack_dict[namespace.mpi_lib]
        else:
            if namespace.application not in self.spack_dict:
                raise RambleSoftwareEnvironmentError('No applications ' +
                                                     'defined in workspace')
            if spec_context not in self.spack_dict['applications']:
                raise RambleSoftwareEnvironmentError('Invalid context ' +
                                                     '%s' % spec_context)
            spec_dict = self.spack_dict[namespace.application][spec_context]
            return self._build_spec_dict(spec_dict[spec_name], app_name=spec_context)

        return self._build_spec_dict(spec_dict[spec_name])

    def _build_spec_dict(self, info_dict, app_name=None, for_config=False):
        """Build a spec dict from a v1 spack dictionary"""
        spec = {}

        for name, val in info_dict.items():
            if val:
                if name != 'required':
                    spec[name] = val

        if app_name:
            spec['application_name'] = app_name

        if for_config:
            if 'application_name' in spec:
                del spec['application_name']
            if 'spec_type' in spec:
                del spec['spec_type']

        return spec

    def spec_string(self, spec, as_dep=False, use_custom_specifier=False, deps_used=None):
        """Create a string for a v1 package spec

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


class RambleSoftwareEnvironmentError(ramble.error.RambleError):
    """Super class for all software environment errors"""
