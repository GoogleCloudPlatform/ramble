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


class sw_namespace:
    spack = 'spack'
    applications = 'applications'
    mpi_lib = 'mpi_libraries'
    compilers = 'compilers'
    spack_spec = 'spack_spec'
    compiler_spec = 'compiler_spec'
    packages = 'packages'
    external_env = 'external_spack_env'


class SoftwareEnvironments(object):
    """Class to represent a set of software environments

    This class contains logic to take the dictionary representations of
    software environments, and unify their format.
    """

    keywords = ramble.keywords.keywords

    supported_confs = ['v1']

    def __init__(self, workspace):

        self._compilers = {}
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

    def _detect_conf_type(self):
        """Auto-detect the type of configuration provided.

        Default configuration type is v1.

        v1 configurations follow the format:

        spack:
          concretized: [true/false]
          applications: {}
          compilers: {}
          mpi_libraries: {}
        """

        tty.debug(f'Spack dict: {str(self.spack_dict)}')

        conf_type = 'v1'

        if sw_namespace.applications in self.spack_dict and \
                sw_namespace.compilers in self.spack_dict and \
                sw_namespace.mpi_lib in self.spack_dict:
            conf_type = 'v1'

        return conf_type

    def _v1_setup(self):
        """Process a v1 `spack:` dictionary in the workspace configuration."""
        tty.debug('Performing v1 software setup.')

        if sw_namespace.compilers in self.spack_dict:
            for compiler, conf in self.spack_dict[sw_namespace.compilers].items():
                self._compilers[compiler] = {}

                spec_dict = self.get_named_spec(compiler)
                self._compilers[compiler][sw_namespace.spack_spec] = self.spec_string(spec_dict)
                self._compilers[compiler][sw_namespace.compiler_spec] = \
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

    def get_specs(self, environment_name, spec_type='package'):
        """Return all of the specs of a given type used by an environment"""
        if environment_name not in self._environments:
            raise RambleSoftwareEnvironmentError(
                f'Environment {environment_name} is not defined.'
            )

        namespace = None
        spec_dict = None
        if spec_type == 'compiler':
            namespace = sw_namespace.compilers
            spec_dict = self._compilers
        elif spec_type == 'package':
            namespace = sw_namespace.packages
            spec_dict = self._packages

        if namespace in self._environments[environment_name]:
            for name in self._environments[environment_name][namespace]:
                yield name, spec_dict[name][sw_namespace.spack_spec]

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
