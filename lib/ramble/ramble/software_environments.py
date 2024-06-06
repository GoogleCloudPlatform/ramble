# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from collections import defaultdict

from spack.util.naming import spack_module_to_python_module

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
from ramble.package_manager import PackageManagerBase


def _get_spec(pkg_info: dict, spec_name: str, prefix: str, default=None) -> str:
    return pkg_info.get(f"{prefix}_{spec_name}", pkg_info.get(spec_name, default))


def _is_dict_empty(rendered: defaultdict):
    if not rendered:
        return True
    for k in rendered:
        if rendered[k]:
            return False
    return True


class SoftwarePackage(object):
    """Class to represent a single software package"""

    def __init__(
        self,
        name: str,
        pkg_info: dict,
    ):
        """Software package constructor

        Args:
            name (str): Name of package
            pkg_info (dict): Package info containing specs for supported package managers
        """

        self.name = name
        self.pkg_info = pkg_info
        self._package_type = "Base"

    def spec_str(self, all_packages: dict | None = None, compiler=False):
        """Return a spec string for this software package

        Args:
            all_packages (optional dict): Dictionary of all package definitions.
                                 Used to look up compiler packages.
            compiler (boolean): True of this package is used as a compiler for
                                another package. False if this is just a primary package.
                                Toggles returning compiler_spec vs. spec in case they are
                                different.

        Returns:
            (str): String representation of the spec for this package definition
        """

        return ""

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """String representation of package information

        Args:
            indent (int): Number of spaces to indent lines with
            verbosity (int): Verbosity level

        Returns:
            (str): String representation of this package
        """

        indentation = " " * indent
        color = rucolor.level_func(color_level)
        out_str = color(f"{indentation}{self._package_type} package: {self.name}\n")
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

        return (
            self.name == other.name
            and self.spec == other.spec
            and self.compiler == other.compiler
            and self.compiler_spec == other.compiler_spec
        )


class RenderedPackage(SoftwarePackage):
    """Class representing an already rendered software package"""

    def __init__(
        self,
        name: str,
        pkg_info: dict,
        package_manager: PackageManagerBase,
        spec: str,
        compiler: str | None = None,
        compiler_spec: str | None = None,
    ):
        """Software package constructor

        Args:
            name (str): Name of package
            pkg_info (dict): Package info containing specs for supported package managers
            package_manager (PackageManagerBase): package manager tied to this package
            spec (str): Package spec (used to install / load package)
            compiler (optional str): Name of package definition to use as compiler
                                     for this package
            compiler_spec (optional str): Spec string to use when this package
                                          is used as a compiler
        """
        super().__init__(name, pkg_info)
        self.name = name
        self.package_manager = package_manager
        self.spec = spec
        self.compiler = compiler
        self.compiler_spec = compiler_spec
        self._package_type = "Rendered"

    def spec_str(self, all_packages: dict | None = None, compiler=False):
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
        if not all_packages:
            all_packages = defaultdict(dict)
        out_str = self.package_manager.get_spec_str(self, all_packages, compiler)

        return out_str

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """String representation of package information

        Args:
            indent (int): Number of spaces to indent lines with
            verbosity (int): Verbosity level

        Returns:
            (str): String representation of this package
        """

        indentation = " " * indent
        out_str = super().info(indent, verbosity, color_level)
        out_str += f'{indentation}    Spec: {self.spec.replace("@", "@@")}\n'
        if self.compiler:
            out_str += f"{indentation}    Compiler: {self.compiler}\n"
        if self.compiler_spec:
            out_str += f'{indentation}    Compiler Spec: {self.compiler_spec.replace("@", "@@")}\n'
        return out_str

    def __eq__(self, other):
        return self.package_manager.name == other.package_manager.name and super().__eq__(other)


class TemplatePackage(SoftwarePackage):
    """Class representing a template software package"""

    def __init__(
        self,
        name: str,
        pkg_info: dict,
    ):
        """Template package constructor

        Args:
            name (str): Name of package
            pkg_info (dict): Package info containing specs for supported package managers
        """
        # package_manager is only associated with a software package at render time
        super().__init__(name, pkg_info)
        self._rendered_packages = defaultdict(dict)
        self._package_type = "Template"

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
        for pkgs in self._rendered_packages.values():
            for pkg in pkgs.values():
                out_str += pkg.info(
                    indent=new_indent, verbosity=verbosity, color_level=color_level + 1
                )
        return out_str

    def render_package(self, expander: object, package_manager: PackageManagerBase):
        """Render a SoftwarePackage from this TemplatePackage

        Args:
            expander (Expander): Expander to use to render a package from this template

        Returns:
            (SoftwarePackage): Rendered SoftwarePackage
        """
        name = expander.expand_var(self.name)
        pm_name = package_manager.name
        pkg_info = self.pkg_info
        pm_prefix = spack_module_to_python_module(pm_name)
        raw_spec = _get_spec(pkg_info, "pkg_spec", pm_prefix) or pkg_info["spec"]
        raw_compiler = _get_spec(pkg_info, "compiler", pm_prefix)
        raw_compiler_spec = _get_spec(pkg_info, "compiler_spec", pm_prefix)
        spec = expander.expand_var(raw_spec)
        compiler = expander.expand_var(raw_compiler) if raw_compiler else None
        compiler_spec = expander.expand_var(raw_compiler_spec) if raw_compiler_spec else None

        new_pkg = RenderedPackage(name, pkg_info, package_manager, spec, compiler, compiler_spec)

        if new_pkg.name in self._rendered_packages[pm_name]:
            if new_pkg != self._rendered_packages[pm_name][name]:
                raise RambleSoftwareEnvironmentError(
                    f"Package {new_pkg.name} defined multiple times with "
                    "inconsistent definitions.\n"
                    "New definition is:\n"
                    f"{new_pkg}"
                    "Old definition is:\n"
                    f"{self._rendered_packages[pm_name][name]}"
                )
            return self._rendered_packages[pm_name][name]
        else:
            return new_pkg

    def add_rendered_package(self, new_package: object, all_packages: dict, pm_name: str):
        """Add a rendered package to this template's list of rendered packages

        Args:
            new_package (SoftwarePackage): New package definition to add
            all_packages (dict): Dictionary of all package definitions
            pm_name (str): The name of the package manager used for the package
        """

        if new_package.name not in self._rendered_packages[pm_name]:
            self._rendered_packages[pm_name][new_package.name] = new_package
            all_packages[pm_name][new_package.name] = new_package


class SoftwareEnvironment(object):
    """Class representing a single software environment"""

    def __init__(self, name: str):
        """SoftwareEnvironment constructor

        Args:
            name (str): Name of the environment
            package_manager (PackageManagerBase): Package manager associated with the environment
        """

        self.name = name
        self._packages = []
        self._environment_type = "Base"

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """Software environment information

        Args:
            indent (int): Number of spaces to inject as indentation
            verbosity (int): Verbosity level

        Returns:
            (str): information of this environment
        """

        indentation = " " * indent
        color = rucolor.level_func(color_level)
        out_str = color(f"{indentation}{self._environment_type} environment: {self.name}\n")
        out_str += f"{indentation}    Packages:\n"
        for pkg in self._packages:
            if verbosity >= 1:
                out_str += f'{indentation}    - {pkg.name} = {pkg.spec_str().replace("@", "@@")}\n'
            else:
                out_str += f"{indentation}    - {pkg.name}\n"
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
        """Constructor for external software environment"""
        super().__init__(name)
        self.external_env = name_or_path

    @property
    def package_manager_name(self):
        return "spack"


class RenderedEnvironment(SoftwareEnvironment):
    """Class representing an already rendered software environment"""

    def __init__(self, name: str, package_manager: PackageManagerBase):
        """Constructor for rendered software environment"""
        super().__init__(name)
        self.package_manager = package_manager

    @property
    def package_manager_name(self):
        return self.package_manager.name

    def __eq__(self, other):
        return self.package_manager.name == other.package_manager.name and super().__eq__(other)


class TemplateEnvironment(SoftwareEnvironment):
    """Class representing a template software environment"""

    def __init__(self, name: str):
        """TemplateEnvironment constructor

        Args:
            name (str): Name of this environment
        """
        super().__init__(name)
        self._package_names = set()
        self._rendered_environments = defaultdict(dict)
        self._environment_type = "Template"

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
        for envs in self._rendered_environments.values():
            for env in envs.values():
                out_str += env.info(new_indent, verbosity, color_level=color_level + 1)
        return out_str

    def __str__(self):
        """String representation of this environment

        Returns:
            (str): String representation of this environment (none of it's rendered environments)
        """

        return super().info()

    def render_environment(
        self,
        expander: object,
        all_package_templates: dict,
        all_packages: dict,
        package_manager: PackageManagerBase,
    ):
        """Render a SoftwareEnvironment from this TemplateEnvironment

        Args:
            expander (Expander): Expander object to use when rendering
            all_packages (dict): All package definitions
            package_manager (PackageManagerBase): Package manager the environment is rendered with

        Returns:
            (RenderedEnvironment) Reference to the rendered SoftwareEnvironment
        """
        name = expander.expand_var(self.name)
        pm_name = package_manager.name

        new_env = RenderedEnvironment(name, package_manager)

        for env_pkg_template in self._package_names:
            rendered_env_pkg_name = expander.expand_var(env_pkg_template)

            if rendered_env_pkg_name:
                added = False
                for template_pkg in all_package_templates.values():
                    rendered_pkg = template_pkg.render_package(expander, package_manager)

                    if rendered_env_pkg_name == rendered_pkg.name:
                        if rendered_pkg.name in all_packages[pm_name]:
                            if rendered_pkg != all_packages[pm_name][rendered_pkg.name]:
                                raise RambleSoftwareEnvironmentError(
                                    f"Environment {name} defined multiple times in inconsistent "
                                    f"ways.\nPackage with differences is {rendered_pkg.name}"
                                )
                            rendered_pkg = all_packages[pm_name][rendered_pkg.name]
                        else:
                            all_packages[pm_name][rendered_pkg.name] = rendered_pkg

                        added = True
                        template_pkg.add_rendered_package(rendered_pkg, all_packages, pm_name)
                        new_env.add_package(rendered_pkg)

                if not added:
                    raise RambleSoftwareEnvironmentError(
                        f"Environment template {self.name} references "
                        f"undefined package {env_pkg_template} rendered to {rendered_env_pkg_name}"
                    )

        return new_env

    def add_rendered_environment(
        self,
        environment: RenderedEnvironment,
        all_environments: dict,
        all_packages: dict,
        pm_name: str,
    ):
        """Add a rendered environment to this template

        Args:
            environment (RenderedEnvironment): Reference to rendered environment
            all_environments (dict): Dictionary containing all environments
            all_packages (dict): Dictionary containing all packages
            pm_name (str): Name of the associated package manager
        """
        if environment.name not in self._rendered_environments[pm_name]:
            self._rendered_environments[pm_name][environment.name] = environment
            all_environments[pm_name][environment.name] = environment
            for template_pkg, rendered_pkg in zip(self._packages, environment._packages):
                template_pkg.add_rendered_package(rendered_pkg, all_packages, pm_name)


class SoftwareEnvironments(object):
    """Class representing a group of software environments"""

    def __init__(self, workspace):
        """SoftwareEnvironments constructor

        Args:
            workspace (Workspace): Reference to workspace owning the software descriptions
        """

        self._workspace = workspace
        self._software_dict = workspace.get_software_dict().copy()
        self._environment_templates = {}
        self._package_templates = {}
        self._rendered_packages = defaultdict(dict)
        self._rendered_environments = defaultdict(dict)

        self._define_templates()

    def info(self, indent: int = 0, verbosity: int = 0, color_level: int = 0):
        """Information for all packages and environments

        Args:
            indent (int): Number of spaces to indent lines with
            verbosity (int): Verbosity level

        Returns:
            (str): Representation of all packages and environments
        """
        out_str = ""
        for pkg in self._package_templates.values():
            out_str += pkg.info(indent, verbosity=verbosity, color_level=color_level)
        for env in self._environment_templates.values():
            out_str += env.info(indent, verbosity=verbosity, color_level=color_level)
        return out_str

    def unused_environments(self):
        """Iterator over environment templates that do not have any rendered environments

        Yields:
            (TemplateEnvironment) Each unused template environment in this group
        """
        for env in self._environment_templates.values():
            if _is_dict_empty(env._rendered_environments):
                yield env

    def unused_packages(self):
        """Iterator over package templates that do not have any rendered packages

        Yields:
            (TemplatePackage) Each unused template package in this group
        """
        for pkg in self._package_templates.values():
            if _is_dict_empty(pkg._rendered_packages):
                yield pkg

    def __str__(self):
        """String representation of all packages and environments in this object

        Returns:
            (str): Representation of all packages and environments
        """
        return self.info(indent=0)

    def _define_templates(self):
        """Process software dictionary to generate templates"""

        if namespace.packages in self._software_dict:
            for pkg_template, pkg_info in self._software_dict[namespace.packages].items():
                new_pkg = TemplatePackage(pkg_template, pkg_info)
                self._package_templates[pkg_template] = new_pkg

        if namespace.environments in self._software_dict:
            for env_template, env_info in self._software_dict[namespace.environments].items():
                if namespace.external_env in env_info and env_info[namespace.external_env]:
                    # External environments are considered rendered
                    new_env = ExternalEnvironment(env_template, env_info[namespace.external_env])
                    # TODO: is external env a spack-only concept?
                    self._rendered_environments["spack"][env_template] = new_env
                else:
                    # Define a new template environment
                    new_env = TemplateEnvironment(env_template)
                    if namespace.packages in env_info:
                        for package in env_info[namespace.packages]:
                            new_env.add_package_name(package)
                    self._environment_templates[env_template] = new_env

    def define_compiler_packages(self, environment: RenderedEnvironment, expander):
        """Define packages for compilers in this environment

        If compilers referenced by (environment) are not defined, create
        definitions for them to properly create compiler specs.

        Args:
            environment (RenderedEnvironment): Environment to extract necessary
                                               compilers from
            expander (Expander): Expander object to use when constructing
                                 compiler package names
        """
        pm_name = environment.package_manager_name
        for pkg in environment._packages:
            if pkg.compiler:
                cur_compiler = pkg.compiler
                while cur_compiler and cur_compiler not in self._rendered_packages[pm_name]:
                    added = False
                    for template_name, template_def in self._package_templates.items():
                        rendered_name = expander.expand_var(template_name)

                        if rendered_name == cur_compiler:
                            rendered_pkg = template_def.render_package(
                                expander, environment.package_manager
                            )

                            if (
                                cur_compiler in self._rendered_packages[pm_name]
                                and rendered_pkg != self._rendered_packages[pm_name][cur_compiler]
                            ):
                                raise RambleSoftwareEnvironmentError(
                                    f"Package {rendered_pkg.name} defined "
                                    "multiple times in inconsistent ways"
                                )
                            added = True
                            template_def.add_rendered_package(
                                rendered_pkg, self._rendered_packages, pm_name
                            )
                            self._rendered_packages[pm_name][rendered_pkg.name] = rendered_pkg

                            if rendered_pkg.compiler:
                                cur_compiler = rendered_pkg.compiler
                    if not added:
                        raise RambleSoftwareEnvironmentError(
                            f"Compiler {pkg.compiler} used, but not "
                            f"defined in environment {environment.name} "
                            f"by package {pkg.name}"
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
        pm_name = environment.package_manager_name
        for pkg in environment._packages:
            if pkg.compiler:
                if pkg.compiler not in self._rendered_packages[pm_name]:
                    raise RambleSoftwareEnvironmentError(
                        f"Compiler {pkg.compiler} used, but not "
                        f"defined in environment {environment.name} "
                        f"by package {pkg.name}"
                    )

                root_compilers.append(pkg.compiler)

        dep_compilers = []
        for comp in root_compilers:
            comp_pkg = self._rendered_packages[pm_name][comp]

            if comp_pkg.compiler:
                cur_compiler = comp_pkg.compiler

                while cur_compiler and cur_compiler not in dep_compilers:
                    dep_compilers.append(cur_compiler)
                    if comp_pkg.compiler:
                        cur_compiler = self._rendered_packages[pm_name][comp_pkg.compiler].name

        for comp in reversed(root_compilers + dep_compilers):
            comp_pkg = self._rendered_packages[pm_name][comp]
            yield comp_pkg.spec_str(all_packages=self._rendered_packages, compiler=False)

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

        logger.debug(f" Used compilers: {used_compilers}")
        logger.debug(f" Compiler warnings: {compiler_warnings}")
        if compiler_warnings:
            logger.warn(
                f"Environment {environment.name} contains packages and their "
                "compilers in the package list. These include:"
            )
            for pkg_name, comp_name in compiler_warnings:
                logger.warn(f"    Package: {pkg_name}, Compiler: {comp_name}")
            logger.warn("This might cause problems when installing the packages.")

    def render_environment(
        self, env_name: str, expander: object, package_manager: PackageManagerBase, require=True
    ):
        """Render an environment needed by an experiment

        Args:
            env_name (str): Name of environment needed by the experiment
            expander (Expander): Expander object from the experiment
            package_manager (PackageManagerBase): Package manager the environment is rendered with

        Returns:
            (SoftwareEnvironment): Reference to software environment for
                                   the experiment
        """

        pm_name = package_manager.name
        # Invoke render with the null package_manager is a programming error
        if not pm_name:
            raise RambleSoftwareEnvironmentError(
                "`render_environment` expects a non-null package manager"
            )

        # Check for an external environment before checking templates
        if env_name in self._rendered_environments[pm_name]:
            if isinstance(self._rendered_environments[pm_name][env_name], ExternalEnvironment):
                return self._rendered_environments[pm_name][env_name]

        for template_name, template_def in self._environment_templates.items():
            rendered_name = expander.expand_var(template_name)
            if rendered_name == env_name:
                rendered_env = template_def.render_environment(
                    expander, self._package_templates, self._rendered_packages, package_manager
                )

                if rendered_env.name == env_name:
                    if env_name in self._rendered_environments[pm_name]:
                        if rendered_env != self._rendered_environments[pm_name][env_name]:
                            raise RambleSoftwareEnvironmentError(
                                f"Environment {env_name} defined multiple times "
                                "in inconsistent ways"
                            )
                        rendered_env = self._rendered_environments[pm_name][env_name]

                    template_def.add_rendered_environment(
                        rendered_env, self._rendered_environments, self._rendered_packages, pm_name
                    )
                    self.define_compiler_packages(rendered_env, expander)
                    self._check_environment(rendered_env)
                    return rendered_env

        if require:
            raise RambleSoftwareEnvironmentError(
                f"No defined environment matches required name {env_name}"
            )


class RambleSoftwareEnvironmentError(ramble.error.RambleError):
    """Super class for all software environment errors"""
