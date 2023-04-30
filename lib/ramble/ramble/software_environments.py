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


class sw_namespace:
    spack = 'spack'
    applications = 'applications'
    mpi_lib = 'mpi_libraries'
    compilers = 'compilers'
    spack_spec = 'spack_spec'
    compiler_spec = 'compiler_spec'
    packages = 'packages'
    environments = 'environments'
    variables = 'variables'
    matrices = 'matrices'
    matrix = 'matrix'
    external_env = 'external_spack_env'


class SoftwareEnvironments(object):
    """Class to represent a set of software environments

    This class contains logic to take the dictionary representations of
    software environments, and unify their format.
    """

    keywords = ramble.keywords.keywords

    supported_confs = ['v1', 'v2']

    def __init__(self, workspace):

        self._packages = {}
        self._environments = {}
        self._workspace = workspace
        self.spack_dict = self._workspace.get_spack_dict().copy()

        conf_type = self._detect_conf_type()

        if conf_type not in self.supported_confs:
            raise RambleSoftwareEnvironmentError(
                f'Configuration type {conf_type} is not one of ' +
                f'{str(self.supported_confs)}'
            )

        if conf_type == 'v1':
            self._v1_setup()
        elif conf_type == 'v2':
            self._v2_setup()

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

        conf_type = 'v2'

        if sw_namespace.applications in self.spack_dict or \
                sw_namespace.compilers in self.spack_dict or \
                sw_namespace.mpi_lib in self.spack_dict:
            conf_type = 'v1'
        if sw_namespace.packages in self.spack_dict and \
                sw_namespace.environments in self.spack_dict:
            conf_type = 'v2'

        tty.debug(f'Detected config type of: {conf_type}')

        return conf_type

    def _v1_setup(self):
        """Process a v1 `spack:` dictionary in the workspace configuration."""
        tty.debug('Performing v1 software setup.')
        tty.warn('Your workspace configuration uses the v1 format for the spack section')
        tty.warn('Please update to the latest format to ensure it keeps functioning properly.')
        tty.warn('v1 support will be removed in the future.')

        if sw_namespace.compilers in self.spack_dict:
            for compiler, conf in self.spack_dict[sw_namespace.compilers].items():
                self._packages[compiler] = {}

                spec_dict = self.get_named_spec(compiler)
                self._packages[compiler][sw_namespace.spack_spec] = self.spec_string(spec_dict)
                self._packages[compiler][sw_namespace.compiler_spec] = \
                    self.spec_string(spec_dict, use_custom_specifier=True)

        if sw_namespace.mpi_lib in self.spack_dict:
            for mpi, conf in self.spack_dict[sw_namespace.mpi_lib].items():
                self._packages[mpi] = {}

                spec_dict = self.get_named_spec(mpi, 'mpi_library')
                self._packages[mpi][sw_namespace.spack_spec] = self.spec_string(spec_dict)

        if sw_namespace.applications in self.spack_dict:
            for env, pkgs in self.spack_dict[sw_namespace.applications].items():
                self._environments[env] = {}
                self._environments[env][sw_namespace.packages] = []
                self._environments[env][sw_namespace.compilers] = []
                self._environments[env][sw_namespace.external_env] = None

                if sw_namespace.external_env in pkgs:
                    self._environments[env][sw_namespace.external_env] = \
                        pkgs[sw_namespace.external_env]

                for pkg, conf in pkgs.items():
                    if pkg != sw_namespace.external_env:
                        self._packages[pkg] = {}
                        spec_dict = self.get_named_spec(pkg, spec_context=env)
                        self._packages[pkg][sw_namespace.spack_spec] = self.spec_string(spec_dict)
                        self._environments[env][sw_namespace.packages].append(pkg)

                        if 'compiler' in conf:
                            self._environments[env][sw_namespace.compilers].append(
                                conf['compiler']
                            )

                        if 'mpi' in conf:
                            self._environments[env][sw_namespace.packages].append(
                                conf['mpi']
                            )

    def _v2_setup(self):
        """Process a v2 `spack:` dictionary in the workspace configuration."""
        tty.debug('Performing v2 software setup.')

        pkg_renderer = ramble.renderer.Renderer('package')
        env_renderer = ramble.renderer.Renderer('environment')

        expander = ramble.expander.Expander({}, None)

        if sw_namespace.packages in self.spack_dict:
            for pkg_template, pkg_info in self.spack_dict[sw_namespace.packages].items():
                pkg_vars = {}
                pkg_matrices = []

                if sw_namespace.variables in pkg_info:
                    pkg_vars = pkg_info[sw_namespace.variables].copy()

                if sw_namespace.matrices in pkg_info:
                    pkg_matrices = pkg_info[sw_namespace.matrices].copy()

                if sw_namespace.matrix in pkg_info:
                    pkg_matrices.append(pkg_info[sw_namespace.matrix].copy())

                pkg_vars['package_name'] = pkg_template

                for rendered_vars in pkg_renderer.render_objects(pkg_vars, pkg_matrices):
                    expansion_str = expander.expansion_str('package_name')
                    final_name = expander.expand_var(expansion_str,
                                                     extra_vars=rendered_vars)
                    self._packages[final_name] = {}

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

        if sw_namespace.environments in self.spack_dict:
            for env_template, env_info in self.spack_dict[sw_namespace.environments].items():
                env_vars = {}
                env_matrices = []

                if sw_namespace.variables in env_info:
                    env_vars = env_info[sw_namespace.variables].copy()

                if sw_namespace.matrices in env_info:
                    env_matrices = env_info[sw_namespace.matrices].copy()

                if sw_namespace.matrix in env_info:
                    env_matrices.append(env_info[sw_namespace.matrix].copy())

                env_vars['environment_name'] = env_template

                for rendered_vars in env_renderer.render_objects(env_vars, env_matrices):
                    expansion_str = expander.expansion_str('environment_name')
                    final_name = expander.expand_var(expansion_str,
                                                     extra_vars=rendered_vars)

                    self._environments[final_name] = {}

                    if sw_namespace.external_env in env_info:
                        external_env = expander.expand_var(env_info[sw_namespace.external_env],
                                                           extra_vars=rendered_vars)
                        self._environments[final_name][sw_namespace.external_env] = \
                            external_env

                    if sw_namespace.packages in env_info:
                        self._environments[final_name][sw_namespace.packages] = []
                        env_packages = self._environments[final_name][sw_namespace.packages]

                        for pkg_name in env_info[sw_namespace.packages]:
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
            compiler_str = f'%{comp_spec["spack_spec"]}'
            if 'compiler_spec' in comp_spec:
                compiler_str = f'%{comp_spec["compiler_spec"]}'
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

        namespace = sw_namespace.packages

        if namespace in self._environments[environment_name]:
            for name in self._environments[environment_name][namespace]:
                yield name

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
        """Extract a named spec from a v1 spack dictionary"""
        if spec_context == 'compiler':
            if sw_namespace.compilers not in self.spack_dict:
                raise RambleSoftwareEnvironmentError('No compilers ' +
                                                     'defined in workspace')
            spec_dict = self.spack_dict[sw_namespace.compilers]
        elif spec_context == 'mpi_library':
            if sw_namespace.mpi_lib not in self.spack_dict:
                raise RambleSoftwareEnvironmentError('No MPI libraries ' +
                                                     'defined in workspace')
            spec_dict = self.spack_dict[sw_namespace.mpi_lib]
        else:
            if sw_namespace.applications not in self.spack_dict:
                raise RambleSoftwareEnvironmentError('No applications ' +
                                                     'defined in workspace')
            if spec_context not in self.spack_dict['applications']:
                raise RambleSoftwareEnvironmentError('Invalid context ' +
                                                     '%s' % spec_context)
            spec_dict = self.spack_dict[sw_namespace.applications][spec_context]
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


class RambleSoftwareEnvironmentError(ramble.error.RambleError):
    """Super class for all software environment errors"""
