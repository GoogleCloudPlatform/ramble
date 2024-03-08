# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum

import ramble.repository
import ramble.workspace
import ramble.keywords
import ramble.error
import ramble.renderer
import ramble.expander
from ramble.namespace import namespace

from ramble.util.logger import logger
import ramble.util.matrices
import ramble.util.colors as rucolor

package_managers = Enum("package_managers", ['spack'])


class SoftwarePackage(object):
    """Class to represent a single software package"""

    def __init__(self, name: str, spec: str, compiler: str = None,
                 compiler_spec: str = None, package_manager: str = 'spack'):
        """Software package constructor

        Args:
            name (str): Name of package
            spec (str): Package spec (used to install / load package)
            compiler (optional str): Name of package definition to use as compiler
                                     for this package
            compiler_spec (optional str): Spec string to use when this package
                                          is used as a compiler
            package_manager (optional str): Name of package manager for this package
        """

        self.name = name
        self.spec = spec
        self.compiler = compiler
        self.compiler_spec = compiler_spec
        self._package_type = 'Rendered'
        self.package_manager = package_managers[package_manager]

    def spec_str(self, all_packages: dict = {}, compiler=False):
        """Return a spec string for this software package

        Args:
            all_packages (dict): Dictionary of all package definitions.
                                 Used to look up compiler packages.
            compiler (boolean): True of this package is used as a compiler for
                                another package. False if this is just a primary package.
                                Toggles returning compiler_spec vs. spec in case they are
                                different.

        Returns:
            (str): String representation of the spec for this package definition
        """

        out_str = ''
        if self.package_manager == package_managers.spack:
            if compiler and self.compiler_spec:
                out_str = self.compiler_spec
            else:
                out_str = self.spec

            if compiler:
                return out_str

            if self.compiler in all_packages:
                out_str += ' %' + all_packages[self.compiler].spec_str(all_packages, compiler=True)
            elif self.compiler:
                out_str += f' (built with {self.compiler})'
        else:
            raise RambleSoftwareEnvironmentError(
                f'Package {self.name} uses an unknown '
                f'package manager {self.package_manager}'
            )

        return out_str

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """String representation of package information

        Args:
            indent (int): Number of spaces to indent lines with
            verbosity (int): Verbosity level

        Returns:
            (str): String representation of this package
        """

        indentation = ' ' * indent
        color = rucolor.level_func(color_level)
        out_str  = color(f'{indentation}{self._package_type} package: {self.name}\n')
        out_str += f'{indentation}    Spec: {self.spec.replace("@", "@@")}\n'
        if self.compiler:
            out_str += f'{indentation}    Compiler: {self.compiler}\n'
        if self.compiler_spec:
            out_str += f'{indentation}    Compiler Spec: {self.compiler_spec.replace("@", "@@")}\n'
        return out_str

    def __str__(self):
        """String representation of software package

        Returns:
            (str): String representation of this software package
        """

        return self.info()

    def __eq__(self, other):
        """Equvialence test for two package definitions

        Args:
            other (SoftwarePackage): Package to compare with self.

        Returns:
            (boolean): True if packages are the same, False otherwise
        """

        return self.name == other.name and self.spec == other.spec and \
            self.compiler == other.compiler and self.compiler_spec == other.compiler_spec


class TemplatePackage(SoftwarePackage):
    """Class representing a template software package"""

    def __init__(self, name: str, spec: str,
                 compiler: str = None, compiler_spec: str = None,
                 package_manager: str = 'spack'):
        """Template package constructor

        Args:
            name (str): Name of package
            spec (str): Package spec (used to install / load package)
            compiler (optional str): Name of package definition to use as compiler
                                     for this package
            compiler_spec (optional str): Spec string to use when this package
                                          is used as a compiler
            package_manager (optional str): Name of package manager for this package
        """
        super().__init__(name, spec, compiler=compiler,
                         compiler_spec=compiler_spec,
                         package_manager=package_manager)
        self._rendered_packages = {}
        self._package_type = 'Template'

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """String representation of package information

        Args:
            indent (int): Number of spaces to indent lines with
            verbosity (int): Verbosity level

        Returns:
            (str): String representation of this package
        """

        out_str = super().info(indent, verbosity, color_level)
        new_indent = indent + 4
        for pkg in self._rendered_packages.values():
            out_str += pkg.info(indent=new_indent, verbosity=verbosity,
                                color_level=color_level + 1)
        return out_str

    def render_package(self, expander: object):
        """Render a SoftwarePackage from this TemplatePackage

        Args:
            expander (Expander): Expander to use to render a package from this template

        Returns:
            (SoftwarePackage): Rendered SoftwarePackage
        """
        name = expander.expand_var(self.name)
        spec = expander.expand_var(self.spec)
        compiler = expander.expand_var(self.compiler) if self.compiler else None
        compiler_spec = expander.expand_var(self.compiler_spec) if self.compiler_spec else None

        new_pkg = SoftwarePackage(name, spec, compiler, compiler_spec)

        if new_pkg.name in self._rendered_packages:
            if new_pkg != self._rendered_packages[name]:
                raise RambleSoftwareEnvironmentError(
                    f'Package {new_pkg.name} defined multiple times with '
                    'inconsistent definitions.\n'
                    'New definition is:\n'
                    f'{new_pkg}'
                    'Old definition is:\n'
                    f'{self._rendered_packages[name]}'
                )
            return self._rendered_packages[name]
        else:
            return new_pkg

    def add_rendered_package(self, new_package: object, all_packages: dict):
        """Add a rendered package to this template's list of rendered packages

        Args:
            new_package (SoftwarePackage): New package definition to add
            all_packages (dict): Dictionary of all package definitions
        """

        if new_package.name not in self._rendered_packages:
            self._rendered_packages[new_package.name] = new_package
            all_packages[new_package.name] = new_package


class SoftwareEnvironment(object):
    """Class representing a single software environment"""

    def __init__(self, name: str):
        """SoftwareEnvironment constructor

        Args:
            name (str): Name of the environment
        """

        self.name = name
        self._packages = []
        self._environment_type = 'Rendered'

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """Software environment information

        Args:
            indent (int): Number of spaces to inject as indentation
            verbosity (int): Verbosity level

        Returns:
            (str): information of this environment
        """

        indentation = ' ' * indent
        color = rucolor.level_func(color_level)
        out_str  = color(f'{indentation}{self._environment_type} environment: {self.name}\n')
        out_str += f'{indentation}    Packages:\n'
        for pkg in self._packages:
            if verbosity >= 1:
                out_str += f'{indentation}    - {pkg.name} = {pkg.spec_str().replace("@", "@@")}\n'
            else:
                out_str += f'{indentation}    - {pkg.name}\n'
        return out_str

    def __str__(self):
        """String representation of this environment

        Returns:
            (str): Representation of this environment
        """
        return self.info(indent=0)

    def add_package(self, package: object):
        """Add a package definition to this environment

        Args:
            package (SoftwarePackage): Package object
        """
        self._packages.append(package)

    def __eq__(self, other):
        """Equivalence test for environments

        Args:
            other (SoftwareEnvironment): Environment to compare with self

        Returns:
            (boolean): True if environments are equivalent, False otherwise
        """
        equal = self.name == other.name and len(self._packages) == len(other._packages)

        if not equal:
            return False

        for self_pkg, other_pkg in zip(self._packages, other._packages):
            if self_pkg != other_pkg:
                return False

        return True


class ExternalEnvironment(SoftwareEnvironment):
    """Class representing an externally defined software environment"""

    def __init__(self, name: str, name_or_path: str):
        """Constructor for external software environment

        """
        super().__init__(name)
        self.external_env = name_or_path


class TemplateEnvironment(SoftwareEnvironment):
    """Class representing a template software environment"""

    def __init__(self, name: str):
        """TemplateEnvironment constructor

        Args:
            name (str): Name of this environment
        """
        super().__init__(name)
        self._package_names = set()
        self._rendered_environments = {}
        self._environment_type = 'Template'

    def add_package_name(self, package: str = None):
        self._package_names.add(package)

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """Software environment information

        Args:
            indent (int): Number of spaces to inject as indentation
            verbosity (int): Verbosity level

        Returns:
            (str): information of this environment
        """
        out_str = super().info(indent, verbosity, color_level=color_level)
        new_indent = indent + 4
        for env in self._rendered_environments.values():
            out_str += env.info(new_indent, verbosity, color_level=color_level + 1)
        return out_str

    def __str__(self):
        """String representation of this environment

        Returns:
            (str): String representation of this environment (none of it's rendered environments)
        """

        return super().info()

    def render_environment(self, expander: object, all_package_templates: dict,
                           all_packages: dict):
        """Render a SoftwareEnvironment from this TemplateEnvironment

        Args:
            expander (Expander): Expander object to use when rendering
            all_packages (dict): All package definitions

        Returns:
            (SoftwareEnvironment) Reference to the rendered SoftwareEnvironment
        """
        name = expander.expand_var(self.name)

        new_env = SoftwareEnvironment(name)

        for env_pkg_template in self._package_names:
            rendered_env_pkg_name = expander.expand_var(env_pkg_template)

            if rendered_env_pkg_name:
                added = False
                for template_pkg in all_package_templates.values():
                    rendered_pkg = template_pkg.render_package(expander)

                    if rendered_env_pkg_name == rendered_pkg.name:
                        if rendered_pkg.name in all_packages:
                            if rendered_pkg != all_packages[rendered_pkg.name]:
                                raise RambleSoftwareEnvironmentError(
                                    f'Environment {name} defined multiple times in inconsistent '
                                    f'ways.\nPackage with differences is {rendered_pkg.name}'
                                )
                            rendered_pkg = all_packages[rendered_pkg.name]
                        else:
                            all_packages[rendered_pkg.name] = rendered_pkg

                        added = True
                        template_pkg.add_rendered_package(rendered_pkg, all_packages)
                        new_env.add_package(rendered_pkg)

                if not added:
                    raise RambleSoftwareEnvironmentError(
                        f'Environment template {self.name} references '
                        f'undefined package {env_pkg_template} rendered to {rendered_env_pkg_name}'
                    )

        return new_env

    def add_rendered_environment(self, environment: object, all_environments: dict,
                                 all_packages: dict):
        """Add a rendered environment to this template

        Args:
            environment (SoftwareEnvironment): Reference to rendered environment
            all_environments (dict): Dictionary containing all environments
            all_packages (dict): Dictionary containing all packages
        """
        if environment.name not in self._rendered_environments:
            self._rendered_environments[environment.name] = environment
            all_environments[environment.name] = environment
            for template_pkg, rendered_pkg in zip(self._packages, environment._packages):
                template_pkg.add_rendered_package(rendered_pkg, all_packages)

    def all_packages(self):
        """Iterator over all packages in this environment

        Yields:
            (SoftwarePackage) Each package in this environment
        """
        for _, pkg_obj in self._packages:
            yield pkg_obj


class SoftwareEnvironments(object):
    """Class representing a group of software environments"""

    _deprecated_sections = [namespace.variables, namespace.zips,
                            namespace.matrix, namespace.matrices, namespace.exclude]

    def __init__(self, workspace):
        """SoftwareEnvironments constructor

        Args:
            workspace (Workspace): Reference to workspace owning the software descriptions
        """

        self._workspace = workspace
        self._spack_dict = workspace.get_spack_dict().copy()
        self._environment_templates = {}
        self._package_templates = {}
        self._rendered_packages = {}
        self._rendered_environments = {}
        self._warn_for_deprecation = set()

        self._define_templates()

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """Information for all packages and environments

        Args:
            indent (int): Number of spaces to indent lines with
            verbosity (int): Verbosity level

        Returns:
            (str): Representation of all packages and environments
        """
        out_str = ''
        for pkg in self._package_templates.values():
            out_str += pkg.info(indent, verbosity=verbosity, color_level=color_level)
        for env in self._environment_templates.values():
            out_str += env.info(indent, verbosity=verbosity, color_level=color_level)
        return out_str

    def __str__(self):
        """String representation of all packages and environments in this object

        Returns:
            (str): Representation of all packages and environments
        """
        return self.info(indent=0)

    def _deprecated_warnings(self):
        if not self._warn_for_deprecation or hasattr(self, '_warned_deprecation'):
            return

        sections_to_print = []

        if namespace.variables in self._warn_for_deprecation:
            sections_to_print.append('spack:variables')
            sections_to_print.append('spack:packages:<name>:variables')
            sections_to_print.append('spack:environments:<name>:variables')

        if namespace.zips in self._warn_for_deprecation:
            sections_to_print.append('spack:zips')
            sections_to_print.append('spack:packages:<name>:zips')
            sections_to_print.append('spack:environments:<name>:zips')

        if namespace.matrix in self._warn_for_deprecation:
            sections_to_print.append('spack:packages:<name>:matrix')
            sections_to_print.append('spack:environments:<name>:matrix')

        if namespace.matrices in self._warn_for_deprecation:
            sections_to_print.append('spack:packages:<name>:matrices')
            sections_to_print.append('spack:environments:<name>:matrices')

        if namespace.exclude in self._warn_for_deprecation:
            sections_to_print.append('spack:packages:<name>:exclude')
            sections_to_print.append('spack:environments:<name>:exclude')

        if not hasattr(self, '_warned_deprecated_variables'):
            self._warned_deprecated_variables = True
            logger.warn('The following config sections are deprecated and ignore:')
            for section in sections_to_print:
                logger.warn(f'    {section}')
            logger.warn('Please remove from your configuration files.')

    def _define_templates(self):
        """Process software dictionary to generate templates"""

        for section in self._deprecated_sections:
            if section in self._spack_dict:
                self._warn_for_deprecation.add(section)

        if namespace.packages in self._spack_dict:
            for pkg_template, pkg_info in self._spack_dict[namespace.packages].items():
                for section in self._deprecated_sections:
                    if section in pkg_info:
                        self._warn_for_deprecation.add(section)

                spec = pkg_info['spack_spec'] if 'spack_spec' in pkg_info else pkg_info['spec']
                compiler = pkg_info['compiler'] \
                    if 'compiler' in pkg_info and pkg_info['compiler'] else None
                compiler_spec = pkg_info['compiler_spec'] \
                    if 'compiler_spec' in pkg_info and pkg_info['compiler_spec'] else None
                new_pkg = TemplatePackage(
                    pkg_template, spec, compiler=compiler, compiler_spec=compiler_spec
                )
                self._package_templates[pkg_template] = new_pkg

        if namespace.environments in self._spack_dict:
            for env_template, env_info in self._spack_dict[namespace.environments].items():
                for section in self._deprecated_sections:
                    if section in env_info:
                        self._warn_for_deprecation.add(section)
                if namespace.external_env in env_info and env_info[namespace.external_env]:
                    # External environments are considered rendered
                    new_env = ExternalEnvironment(env_template, env_info[namespace.external_env])
                    self._rendered_environments[env_template] = new_env
                else:
                    # Define a new template environment
                    new_env = TemplateEnvironment(env_template)
                    if namespace.packages in env_info:
                        for package in env_info[namespace.packages]:
                            new_env.add_package_name(package)
                    self._environment_templates[env_template] = new_env

    def define_compiler_packages(self, environment, expander):
        """Define packages for compilers in this environment

        If compilers referenced by (environment) are not defined, create
        definitions for them to properly create compiler specs.

        Args:
            environment (SoftwareEnvironment): Environment to extract necessary
                                               compilers from
            expander (Expander): Expander object to use when constructing
                                 compiler package names
        """
        for pkg in environment._packages:
            if pkg.compiler:
                cur_compiler = pkg.compiler
                while cur_compiler and cur_compiler not in self._rendered_packages:
                    added = False
                    for template_name, template_def in self._package_templates.items():
                        rendered_name = expander.expand_var(template_name)

                        if rendered_name == cur_compiler:
                            rendered_pkg = template_def.render_package(expander)

                            if cur_compiler in self._rendered_packages and \
                                    rendered_pkg != self._rendered_packages[cur_compiler]:
                                raise RambleSoftwareEnvironmentError(
                                    f'Package {rendered_pkg.name} defined '
                                    'multiple times in inconsistent ways'
                                )
                            added = True
                            template_def.add_rendered_package(rendered_pkg,
                                                              self._rendered_packages)
                            self._rendered_packages[rendered_pkg.name] = rendered_pkg

                            if rendered_pkg.compiler:
                                cur_compiler = rendered_pkg.compiler
                    if not added:
                        raise RambleSoftwareEnvironmentError(
                            f'Compiler {pkg.compiler} used, but not '
                            f'defined in environment {environment.name} '
                            f'by package {pkg.name}'
                        )

    def compiler_specs_for_environment(self, environment: object):
        """Iterator over compiler specs for a given environment

        Assumes all compilers have been defined via
        self.define_compiler_packages()

        Args:
            environment (SoftwareEnvironment): Environment to extract compiler specs for

        Yields:
            (str) Spec string for each compiler
        """

        root_compilers = []
        for pkg in environment._packages:
            if pkg.compiler:
                if pkg.compiler not in self._rendered_packages:
                    raise RambleSoftwareEnvironmentError(
                        f'Compiler {pkg.compiler} used, but not '
                        f'defined in environment {environment.name} '
                        f'by package {pkg.name}'
                    )

                root_compilers.append(pkg.compiler)

        dep_compilers = []
        for comp in root_compilers:
            comp_pkg = self._rendered_packages[comp]

            if comp_pkg.compiler:
                cur_compiler = comp_pkg.compiler

                while cur_compiler and cur_compiler not in dep_compilers:
                    dep_compilers.append(cur_compiler)
                    if comp_pkg.compiler:
                        cur_compiler = self._rendered_packages[comp_pkg.compiler].name

        for comp in reversed(root_compilers + dep_compilers):
            comp_pkg = self._rendered_packages[comp]
            yield comp_pkg.spec_str(all_packages=self._rendered_packages,
                                    compiler=False)

    def package_specs_for_environment(self, environment: object):
        """Iterator over package specs for a given environment

        Assumes all compilers have been defined via
        self.define_compiler_packages()

        Args:
            environment (SoftwareEnvironment): Environment to extract package specs for

        Yields:
            (str) Spec string for each package
        """

        for pkg in environment._packages:
            yield pkg.spec_str(all_packages=self._rendered_packages, compiler=False)

    def _check_environment(self, environment):
        """Check an environment for common issues

        Args:
            environment (SoftwareEnvironment): Environment to check for issues in
        """

        pkg_names = set()

        for pkg in environment._packages:
            pkg_names.add(pkg.name)

        used_compilers = set()
        compiler_warnings = []
        for pkg in environment._packages:
            if pkg.compiler and pkg.compiler in pkg_names:
                compiler_warnings.append((pkg.name, pkg.compiler))

        logger.debug(f' Used compilers: {used_compilers}')
        logger.debug(f' Compiler warnings: {compiler_warnings}')
        if compiler_warnings:
            logger.warn(
                f'Environment {environment.name} contains packages and their '
                'compilers in the package list. These include:'
            )
            for pkg_name, comp_name in compiler_warnings:
                logger.warn(
                    f'    Package: {pkg_name}, Compiler: {comp_name}'
                )
            logger.warn(
                'This might cause problems when installing the packages.'
            )

        self._deprecated_warnings()

    def render_environment(self, env_name: str, expander: object):
        """Render an environment needed by an experiment

        Args:
            env_name (str): Name of environment needed by the experiment
            expander (Expander): Expander object from the experiment

        Returns:
            (SoftwareEnvironment): Reference to software environment for
                                   the experiment
        """

        # Check for an external environment before checking templates
        if env_name in self._rendered_environments:
            if isinstance(self._rendered_environments[env_name], ExternalEnvironment):
                return self._rendered_environments[env_name]

        for template_name, template_def in self._environment_templates.items():
            rendered_name = expander.expand_var(template_name)
            if rendered_name == env_name:
                rendered_env = template_def.render_environment(expander, self._package_templates,
                                                               self._rendered_packages)

                if rendered_env.name == env_name:
                    if env_name in self._rendered_environments:
                        if rendered_env != self._rendered_environments[env_name]:
                            raise RambleSoftwareEnvironmentError(
                                f'Environment {env_name} defined multiple times '
                                'in inconsistent ways'
                            )
                        rendered_env = self._rendered_environments[env_name]

                    template_def.add_rendered_environment(rendered_env,
                                                          self._rendered_environments,
                                                          self._rendered_packages)
                    self.define_compiler_packages(rendered_env, expander)
                    self._check_environment(rendered_env)
                    return rendered_env

        raise RambleSoftwareEnvironmentError(
            f'No defined environment matches required name {env_name}'
        )


class RambleSoftwareEnvironmentError(ramble.error.RambleError):
    """Super class for all software environment errors"""
