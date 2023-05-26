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

    supported_confs = ['v2']

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

        Default configuration type is 'invalid'.

        v2 configurations follow the format:

        spack:
          concretized: [true/false]
          packages: {}
          environments: {}
        """

        conf_type = 'invalid'

        if namespace.packages in self.spack_dict and \
                namespace.environments in self.spack_dict:
            conf_type = 'v2'

        tty.debug(f'Detected config type of: {conf_type}')

        return conf_type

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


class RambleSoftwareEnvironmentError(ramble.error.RambleError):
    """Super class for all software environment errors"""
