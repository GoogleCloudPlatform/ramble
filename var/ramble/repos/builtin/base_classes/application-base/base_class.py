# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for application definitions"""

import copy
import fnmatch
import operator
import os
import re
import shutil
import stat
import string
import time
from html import escape
from typing import List

import llnl.util.filesystem as fs
import llnl.util.tty.color as color

import ramble.config
import ramble.expander
import ramble.fetch_strategy
import ramble.graphs
import ramble.keywords
import ramble.mirror
import ramble.repeats
import ramble.repository
import ramble.stage
import ramble.success_criteria
import ramble.util.class_attributes
import ramble.util.colors as rucolor
import ramble.util.directives
import ramble.util.env
import ramble.util.executable
import ramble.util.hashing
import ramble.util.lock as lk
import ramble.util.path
import ramble.util.stats
import ramble.variants
from ramble.error import (
    ApplicationError,
    ChainCycleDetectedError,
    ExecutableNameError,
    FormattedExecutableError,
    InvalidChainError,
    ObjectValidationError,
)
from ramble.experiment_result import ExperimentResult, ExperimentStatus
from ramble.language.application_language import ApplicationMeta
from ramble.language.shared_language import (
    SharedMeta,
    register_builtin,
    register_phase,
)
from ramble.util import constants, conversions
from ramble.util.foms import FomType, SummaryFoms
from ramble.util.logger import logger
from ramble.util.naming import NS_SEPARATOR
from ramble.util.output_capture import output_mapper
from ramble.util.shell_utils import source_str
from ramble.workspace import namespace

import spack.util.compression
import spack.util.executable
import spack.util.spack_json

ObjectMixin = ramble.repository.get_base_class("object-mixin")

_NULL_CONTEXT = "null"

_DEFAULT_CONTENT_PERM = (
    stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH
)


def _get_context_display_name(context):
    return (
        f"default ({_NULL_CONTEXT}) context"
        if context == _NULL_CONTEXT
        else f"{context} context"
    )


def _check_shell_support(app_inst):
    def _check_match(inst, shell_to_support):
        pat = getattr(inst, "shell_support_pattern", None)
        matched = pat is None or fnmatch.fnmatch(shell_to_support, pat)
        if not matched:
            logger.die(
                f"{inst.name} does not support {shell_to_support} shell"
                f", the supported shell pattern is '{pat}'"
            )

    shell = ramble.config.get("config:shell")
    _check_match(app_inst, shell)
    for mod_inst in app_inst._modifier_instances:
        _check_match(mod_inst, shell)
    _check_match(app_inst.package_manager, shell)


def _run_phase_hook(obj, workspace, pipeline, hook):
    """Helper to enable an object run phase hooks defined in application"""
    phase_defs = obj.phase_definitions
    if pipeline in phase_defs and hook in phase_defs[pipeline]:
        return

    hook_func_name = f"_{hook}"
    if hasattr(obj, hook_func_name):
        phase_func = _get_phase_func_wrapper(
            workspace, getattr(obj, hook_func_name), hook
        )
        phase_func(workspace)


def _get_phase_func_wrapper(workspace, phase_func, phase_name):
    if workspace.profile_config is None:
        return phase_func
    (profiler, profile_phases) = workspace.profile_config
    if phase_name not in profile_phases:
        return phase_func
    return profiler(phase_func)


class ApplicationBase(ObjectMixin, metaclass=ApplicationMeta):
    origin_type = "application"
    _builtin_name = NS_SEPARATOR.join(("builtin", "{name}"))
    _builtin_required_key = "required"
    _inventory_file_name = "ramble_inventory.json"
    _status_file_name = "ramble_status.json"
    _pipelines = [
        "analyze",
        "archive",
        "mirror",
        "setup",
        "pushdeployment",
        "pushtocache",
        "execute",
        "logs",
    ]
    _language_classes = [ApplicationMeta, SharedMeta]

    license_names: List[str] = []

    def __init__(self, file_path):
        super().__init__()

        ramble.util.class_attributes.convert_class_attributes(self)

        self.object_variants = ramble.variants.VariantSet()
        for var_args in self.class_variants.values():
            self.object_variants.default_variant(**var_args)

        self.keywords = ramble.keywords.keywords.copy()

        self._vars_are_expanded = False
        self.expander = None
        self._formatted_executables = {}
        self.variables = None
        self.variants = None
        self._active_workload = None
        self.no_expand_vars = None
        self.experiment_set = None
        self.internals = {}
        self.is_template = False
        self.generated_experiments = []
        self.repeats = ramble.repeats.Repeats()
        self._command_list = []
        self._command_list_without_logs = []
        self.chained_experiments = None
        self.chain_order = []
        self.chain_prepend = []
        self.chain_append = []
        self.chain_commands = {}
        self._env_variable_sets = []
        self.modifiers = []
        self.experiment_tags = []
        self._modifier_instances = []
        self._input_fetchers = None
        self.result = None
        self._phase_times = {}
        self._pipeline_graphs = None
        self.package_manager = None
        self.custom_executables = {}
        self.success_list = None
        self._exp_lock = None
        self._input_lock = None
        self._software_lock = None
        self._experiment_graph = None
        # A dict storing fom values, currently it only stores inmem FOMs
        self._fom_map = {}

        # Ensure we always have the application name, and this is never empty
        self._file_path = file_path

        self.license_names = self.license_names + [self.name]

        self.application_class = "ApplicationBase"

        self.license_path = ""
        self.license_file = ""

        self.workflow_manager = None

        self.result = ExperimentResult(self)

        ramble.util.directives.define_directive_methods(self)

    @property
    def experiment_lock(self):
        """Create a lock for the experiment directory, and return it"""
        if self._exp_lock is None:
            lock_path = os.path.join(
                self.expander.expand_var("{experiment_run_dir}"),
                ".ramble-experiment",
            )

            self._exp_lock = lk.Lock(lock_path)

        return self._exp_lock

    def clone(self):
        """Deep clone an application instance"""
        new_clone = type(self)(self._file_path)
        self.generated_experiments.append(new_clone)

        clone_variables = {} if not self.variables else self.variables
        clone_variants = {} if not self.variants else self.variants
        new_clone.set_variables_and_variants(
            clone_variables, clone_variants, self.experiment_set
        )
        if self._env_variable_sets:
            new_clone.set_env_variable_sets(self._env_variable_sets.copy())
        if self.internals:
            new_clone.set_internals(self.internals.copy())
        if self._formatted_executables:
            new_clone.set_formatted_executables(
                self._formatted_executables.copy()
            )

        new_clone.workloads = copy.deepcopy(self.workloads)
        new_clone.keywords = ramble.keywords.keywords.copy()
        new_clone.set_template(False)
        new_clone.repeats.set_repeats(False, 0)
        new_clone.set_chained_experiments(None)

        return new_clone

    def is_actionable(self):
        """Determine if an experiment should be actioned in pipelines

        Returns True if the experiment should be actioned in a pipeline, False
        if not.
        """

        if self.is_template:
            return False

        return True

    def _validate_workload(self, workload_name):
        """Checks if a workload name is valid and returns the workload that
        satisfies `when` conditions.
        """
        workload = None
        workload_found = False
        for when_set, workloads in self.workloads.items():
            if workload_name in workloads:
                workload_found = True
                if self.expander.satisfies(
                    when_set, self.experiment_variants()
                ):
                    if workload:
                        logger.die(
                            f"Workload {workload_name} is defined with "
                            "overlapping `when` conditions. Ensure that "
                            "conditions are mutually exclusive."
                        )
                    workload = workloads[workload_name]

        if not workload_found:
            raise ApplicationError(
                f"Workload {workload_name} is not defined "
                f"as a workload of application {self.name}."
            )
        if not workload:
            logger.die(
                f"Workload {workload_name} is not defined "
                "for the active `when` conditions."
            )

        return workload

    def set_active_workload(self):
        """Retrieves the current workload name from the expander, evaluates
        `when` conditions, and sets the active workload to the one that matches
        conditions.
        """
        self._active_workload = self._validate_workload(
            self.expander.workload_name
        )

    def get_workload(self, workload_name=None):
        """Retrieves a workload that satisfies current `when` conditions. If
        workload_name is not provided, retrieves the active workload.
        """
        if not workload_name or (
            self.expander.workload_name
            and self.expander.workload_name == workload_name
        ):
            if not self._active_workload:
                self.set_active_workload()
            return self._active_workload
        else:
            return self._validate_workload(workload_name)

    def get_workloads(self, workload_name=None):
        """Retrieves all workloads with workload_name, ignoring `when`
        conditions. If workload_name is not provided, retrieves all workloads
        with the same name as the active workload.

        Use this instead of get_workload() if calling before variants are set,
        e.g. in set_variables()
        """
        if not workload_name:
            workload_name = self.expander.workload_name

        found_workload = False
        for workloads in self.workloads.values():
            if workload_name in workloads:
                found_workload = True
                yield workloads[workload_name]

        if not found_workload:
            raise ApplicationError(
                f"Workload {workload_name} is not defined "
                f"as a workload of application {self.name}."
            )

    def get_all_workloads(self):
        """Retrieves all workloads satisfying current `when` conditions."""
        all_workloads_names = set()
        found = False
        for when_set, workloads in self.workloads.items():
            if self.expander.satisfies(
                when_set, self.experiment_variants(allow_caching=False)
            ):
                for workload_name, workload in workloads.items():
                    if workload_name in all_workloads_names:
                        logger.die(
                            f"Workload {workload_name} is defined with "
                            "overlapping `when` conditions. Ensure that "
                            "conditions are mutually exclusive."
                        )
                    all_workloads_names.add(workload_name)
                    yield workload
                    found = True

        if not found:
            logger.die(
                "No workloads satisfy the current `when` conditions: \n"
                f"  {self.experiment_variants(allow_caching=False).as_set()}"
            )

    def _set_package_manager(self):
        pkgman_name = conversions.canonical_none(
            self.experiment_variants(allow_caching=False).value(
                namespace.package_manager
            )
        )

        if pkgman_name is not None:
            try:
                pkgman_type = ramble.repository.ObjectTypes.package_managers
                self.package_manager = ramble.repository.get(
                    pkgman_name, pkgman_type
                ).copy()
                self.package_manager.set_application(self)
            except ramble.repository.UnknownObjectError:
                logger.die(
                    f"{pkgman_name} is not a valid package manager. "
                    "Valid package managers can be listed via:\n"
                    "\tramble list --type package_managers"
                )

        if self.package_manager is not None:
            for pkgname, config in self.required_packages.items():
                if self.expander.satisfies(
                    config["when"],
                    variant_set=self.experiment_variants(allow_caching=False),
                ):
                    self.keywords.update_keys(
                        {
                            f"{pkgname}_path": {
                                "type": ramble.keywords.key_type.reserved,
                                "level": ramble.keywords.output_level.variable,
                            }
                        }
                    )

    def _set_workflow_manager(self):
        workflow_name = conversions.canonical_none(
            self.experiment_variants(allow_caching=False).value(
                namespace.workflow_manager
            )
        )

        # Map None to the default of user-managed
        if workflow_name is None:
            workflow_name = "user-managed"

        try:
            wfman_type = ramble.repository.ObjectTypes.workflow_managers
            self.workflow_manager = ramble.repository.get(
                workflow_name, wfman_type
            ).copy()
            self.workflow_manager.set_application(self)
        except ramble.repository.UnknownObjectError:
            logger.die(
                f"{workflow_name} is not a valid workflow manager. "
                "Valid workflow managers can be listed via:\n"
                "\tramble list --type workflow_managers"
            )

    def set_success_list(self, success_criteria):
        self.success_list = ramble.success_criteria.ScopedCriteriaList()

        if success_criteria:
            for conf in success_criteria:
                self.success_list.add_criteria("experiment", **conf)

    def build_phase_order(self):
        if self._pipeline_graphs is not None:
            return

        self._pipeline_graphs = {}
        for pipeline in self._pipelines:
            if pipeline not in self.phase_definitions:
                self.phase_definitions[pipeline] = {}

            self._pipeline_graphs[pipeline] = ramble.graphs.PhaseGraph(
                self.phase_definitions[pipeline], self
            )

            for mod_inst in self._modifier_instances:
                # Define phase nodes
                for _, phase_node in mod_inst.all_pipeline_phases(pipeline):
                    self._pipeline_graphs[pipeline].add_node(
                        phase_node, obj_inst=mod_inst
                    )

                # Define phase edges
                for _, phase_node in mod_inst.all_pipeline_phases(pipeline):
                    self._pipeline_graphs[pipeline].define_edges(
                        phase_node, internal_order=True
                    )

            if self.package_manager:
                # Define phase nodes
                for _, phase_node in self.package_manager.all_pipeline_phases(
                    pipeline
                ):
                    self._pipeline_graphs[pipeline].add_node(
                        phase_node, obj_inst=self.package_manager
                    )

                # Define phase edges
                for _, phase_node in self.package_manager.all_pipeline_phases(
                    pipeline
                ):
                    self._pipeline_graphs[pipeline].define_edges(
                        phase_node, internal_order=True
                    )

    def set_env_variable_sets(self, env_variable_sets):
        """Set internal reference to application environment variable sets"""

        self._env_variable_sets = env_variable_sets.copy()

        new_env_vars = {
            "set": {},
            "append": [],
            "prepend": [],
        }
        for env_var in self.selected_environment_variables.values():
            action = env_var.method
            value = env_var.value
            # Pull out base group from the new_env_vars dict, based on the env_var's action.
            new_group = new_env_vars[action]

            if action == "append":
                # If action is append, we need to pull out the append actions.
                # Here, the value in the dict is a list (instead of a dict) to allow
                # for different separators.
                # We need to find the group (if it exists) with the correct separator,
                # and add the new env-var to that group.
                found = False
                for group in new_group:
                    if (
                        "var-separator" in group
                        and group["var-separator"] == env_var.separator
                    ):
                        found = True
                        new_group = group["vars"]
                        break

                if not found:
                    # Create a group, if it wasn't found previously, and
                    # add to the append action's group.
                    append_set = {
                        "var-separator": env_var.separator,
                        "vars": {},
                    }
                    new_group.append(append_set)
                    new_group = append_set["vars"]
            elif action == "prepend":
                # If action is prepend, we need to pull out the prepend actions.
                # Here, the value is again a list instead of a dict.
                # However, we don't allow different separators
                # when prepending. So, here we simply grab the first entry in the list.
                if not new_group:
                    prepend_set = {"paths": {}}
                    new_group.append(prepend_set)

                new_group = new_group[0]["paths"]
            else:
                # If action is set, just pull out the value
                new_group = new_env_vars["set"]

            add = True
            # Find the env var set with a matching action, and
            # decide of the env-var should be added or not.
            for env_var_set in self._env_variable_sets:
                if action in env_var_set:
                    if env_var.name in env_var_set[action]:
                        add = False

            if add:
                new_group[env_var.name] = value

        # Remove any actions that don't have env-vars, to prevent them
        # from being actioned later.
        for action in ["set", "append", "prepend"]:
            if not new_env_vars[action]:
                del new_env_vars[action]

        # Add the new env vars to the object's environment variable sets.
        if new_env_vars:
            self._env_variable_sets.append(new_env_vars)

    def set_variables_and_variants(self, variables, variants, experiment_set):
        """Set internal reference to variables and variants

        Also, create an application specific expander class.

        Args:
            variables (dict): Dictionary of variable definitions for this
                             experiment.
            variants (dict): Dictionary of variant controls for this
                             experiment.
            experiment_set: Reference to experiment set, for expanding
                            referenced variables.
        """

        self.variables = variables.copy()
        self.variants = variants.copy()
        self.experiment_set = experiment_set
        self.expander = ramble.expander.Expander(
            self.variables, self.experiment_set
        )

        # Define experiment variants
        for name, value in variants.items():
            expanded_value = self.expander.expand_var(value, typed=True)
            self.object_variants.experiment_variant(name, expanded_value)

        # Set up remaining variants
        self._set_package_manager()
        self._set_workflow_manager()

        base_chain = self.__class__.__mro__
        for cls in base_chain:
            if hasattr(cls, "name") and cls.name is not None:
                self.object_variants.multi_value_variant(
                    "application_name",
                    value=self.expander.application_name,
                )

        # Define workload_name variant as early as possible
        self.object_variants.default_variant(
            "workload_name",
            default=self.expander.workload_name,
            description="Name of experiment workload",
        )

        self.no_expand_vars = set()
        workloads = self.get_workloads()

        for workload in workloads:
            for var_when_set, var_list in workload.variables.items():
                if self.expander.satisfies(
                    var_when_set, self.experiment_variants(allow_caching=False)
                ):
                    for var in var_list:
                        if not var.expandable:
                            self.no_expand_vars.add(var.name)

        self.define_missing_variables()

        self.expander.set_no_expand_vars(self.no_expand_vars)
        if experiment_set and experiment_set._workspace:
            self.expander.replacement_paths = (
                experiment_set._workspace.workspace_paths()
            )

    def define_missing_variables(self):
        """Iterate over missing variable definitions, and add them until there
        are no more to add."""

        while True:
            missing_vars = {}
            for _, obj in self._objects():
                for var, val in obj.selected_variables.items():
                    # Check for its presence in missing_vars, for the "first-defined-wins" semantic
                    if var not in self.variables and var not in missing_vars:
                        missing_vars[var] = val.default

            if not missing_vars:
                break

            for var, default_val in missing_vars.items():
                self.define_variable(var, default_val)

    def set_internals(self, internals):
        """Set internal reference to application internals"""

        self.internals = internals

    def set_template(self, is_template):
        """Set if this instance is a template or not"""
        self.is_template = is_template

    def set_chained_experiments(self, chained_experiments):
        """Set chained experiments for this instance"""
        self.chained_experiments = None
        if chained_experiments:
            self.chained_experiments = chained_experiments.copy()

    def set_modifiers(self, modifiers):
        """Set modifiers for this instance"""
        if modifiers:
            self.modifiers = modifiers.copy()
            self.build_modifier_instances()

    def set_tags(self, tags):
        """Set experiment tags for this instance"""

        self.experiment_tags = self.tags.copy()

        self.experiment_tags.extend(self.get_workload().tags)

        if tags:
            self.experiment_tags.extend(tags)

    def set_formatted_executables(self, formatted_executables):
        """Set formatted executables for this instance"""
        self._formatted_executables = formatted_executables.copy()

    def has_tags(self, tags):
        """Check if this instance has provided tags.

        Args:
            tags (list): List of strings, where each string is an individual tag
        Returns:
            (bool): True if all tags are in this instance, False otherwise
        """

        if tags and self.experiment_tags:
            tag_set = set(tags)
            exp_tag_set = set(self.experiment_tags)

            for tag in tag_set:
                if tag not in exp_tag_set:
                    return False
            return True

        return False

    def experiment_log_file(self, logs_dir):
        """Returns an experiment log file path for the given logs directory"""
        return (
            os.path.join(logs_dir, self.expander.experiment_namespace) + ".out"
        )

    def get_pipeline_phases(self, pipeline, phase_filters=None):
        if phase_filters is None:
            phase_filters = ["*"]

        self.build_modifier_instances()
        self.build_phase_order()

        if pipeline not in self._pipelines:
            logger.die(
                f"Requested pipeline {pipeline} is not valid.\n",
                f"\tAvailable pipelinese are {self._pipelines}",
            )

        if pipeline not in self._pipeline_graphs:
            return

        ordered_phases = list(self._pipeline_graphs[pipeline].walk())

        selected_phases = set()
        last_match_idx = -1

        for i, phase in enumerate(ordered_phases):
            if self.expander.satisfies(
                phase.when, variant_set=self.experiment_variants()
            ) and any(fnmatch.fnmatch(phase.key, pf) for pf in phase_filters):
                selected_phases.add(phase)
                last_match_idx = i

        final_phases = selected_phases
        include_phase_deps = ramble.config.get(
            "config:include_phase_dependencies"
        )
        if include_phase_deps and last_match_idx > -1:
            dependencies = ordered_phases[:last_match_idx]
            final_phases.update(dependencies)

        for phase in ordered_phases:
            if phase in final_phases:
                yield phase.key

    def print_vars(self, header="", vars_to_print=None, indent=""):
        print_vars = vars_to_print
        if not print_vars:
            print_vars = self.variables

        color.cprint(f"{indent}{header}:")
        for var, val in print_vars.items():
            expansion_var = self.expander.expansion_str(var)
            expanded = self.expander.expand_var(expansion_var)
            color.cprint(
                f"{indent}  {var} = {val} ==> {expanded}".replace("@", "@@")
            )

    def build_used_variables(self, workspace):
        """Build a set of all used variables

        By expanding all necessary portions of this experiment (required /
        reserved keywords, templates, commands, etc...), determine which
        variables are used throughout the experiment definition.

        Variables can have list definitions. These are iterated over to ensure
        variables referenced by any of them are tracked properly.

        Args:
            workspace (ramble.workspace.Workspace): Workspace to extract templates from

        Returns:
            (set): All variable names used by this experiment.
        """
        self.build_modifier_instances()
        self.define_variables_for_template_path(workspace)

        backup_variables = self.variables.copy()

        self._define_commands(success_list=self.success_list)
        self._define_formatted_executables()

        ########################
        # Define extra variables
        ########################
        self.define_missing_variables()

        ##########################################
        # Expand used variables to track all usage
        ##########################################

        # Add all known keywords
        for key in self.keywords.keys:
            self.expander.expand_var_name(key)

        if self.chained_experiments:
            for chained_exp in self.chained_experiments:
                if namespace.inherit_variables in chained_exp:
                    for var in chained_exp[namespace.inherit_variables]:
                        self.expander._used_variables.add(var)
                        self.expander.expand_var_name(var)

        # Add variables from success criteria
        criteria_list = self.success_list
        for criteria, _ in criteria_list.all_criteria():
            if criteria.mode == "fom_comparison":
                self.expander.expand_var(criteria.fom_formula)
                self.expander.expand_var(criteria.fom_name)
                self.expander.expand_var(criteria.fom_context)
            elif criteria.mode == "application_function":
                self.evaluate_success()

        if self.package_manager is not None:
            self.package_manager.build_used_variables(workspace)

        for template_name, template_conf in workspace.all_templates():
            self.expander._used_variables.add(template_name)
            self.expander.expand_var(template_conf["contents"])

        ############################
        # Reset variable definitions
        ############################
        to_remove = set()
        for var in self.variables:
            if var not in backup_variables:
                to_remove.add(var)

        for var in to_remove:
            del self.variables[var]

        for var, val in backup_variables.items():
            self.variables[var] = val

        self._command_list = []

        return self.expander._used_variables

    def print_internals(self, indent=""):
        if not self.internals:
            return

        if namespace.custom_executables in self.internals:
            header = rucolor.nested_4("Custom Executables")
            color.cprint(f"{indent}{header}:")

            for name in self.internals[namespace.custom_executables]:
                color.cprint(f"{indent}  {name}")

        if namespace.executables in self.internals:
            header = rucolor.nested_4("Executable Order")
            color.cprint(
                f"{indent}{header}: {str(self.internals[namespace.executables])}"
            )

        if namespace.executable_injection in self.internals:
            header = rucolor.nested_4("Executable Injection")
            color.cprint(
                f"{indent}{header}: {str(self.internals[namespace.executable_injection])}"
            )

    def print_chain_order(self, indent=""):
        if not self.chain_order:
            return

        header = rucolor.nested_4("Experiment Chain")
        color.cprint(f"{indent}{header}:")
        for exp in self.chain_order:
            color.cprint(f"{indent}- {exp}")

    # Phase execution helpers
    def run_phase(self, pipeline, phase, workspace):
        """Run a phase, by getting its function pointer"""
        if self.is_template:
            logger.debug(f"{self.name} is a template. Skipping phases")
            return
        if self.repeats.is_repeat_base:
            logger.debug(f"{self.name} is a repeat base. Skipping phases")
            return

        phase_node = self._pipeline_graphs[pipeline].get_node(phase)

        if phase_node is None:
            logger.die(f"Phase {phase} is not defined in pipeline {pipeline}")

        logger.msg(f"  Executing phase {phase}")
        start_time = time.time()

        for _, obj in self._objects(
            exclude_types=[ramble.repository.ObjectTypes.applications]
        ):
            _run_phase_hook(obj, workspace, pipeline, phase)
        phase_func = _get_phase_func_wrapper(
            workspace, phase_node.attribute, phase
        )
        phase_func(workspace, app_inst=self)
        self._phase_times[phase] = time.time() - start_time

    def print_phase_times(self, pipeline, phase_filters=None):
        """Print phase execution times by pipeline phase order

        Args:
            pipeline (str): Name of pipeline to print timing information for
            phase_filters (list(str) | None): Filters to limit phases to print
        """
        logger.msg("Phase timing statistics:")
        if phase_filters is None:
            phase_filters = ["*"]
        for phase in self.get_pipeline_phases(
            pipeline, phase_filters=phase_filters
        ):
            # Set default time to 0.0 s, to prevent KeyError from skipped phases
            if phase not in self._phase_times:
                self._phase_times[phase] = 0.0
            logger.msg(
                f"  {phase} time: {round(self._phase_times[phase], 5)} (s)"
            )

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
        classes_in_stack = {self}
        chain_idx = 0
        chain_stack = []
        for exp in reversed(self.chained_experiments):
            for exp_name in self.experiment_set.search_primary_experiments(
                exp["name"]
            ):
                child_inst = self.experiment_set.get_experiment(exp_name)

                if child_inst in classes_in_stack:
                    raise ChainCycleDetectedError(
                        "Cycle detected in experiment chain:\n"
                        + f"    Primary experiment {parent_namespace}\n"
                        + f"    Chained expeirment name: {exp_name}\n"
                        + f"    Chain definition: {str(exp)}"
                    )
                chain_stack.append((exp_name, exp.copy()))

        parent_run_dir = self.expander.expand_var(
            self.expander.expansion_str(self.keywords.experiment_run_dir)
        )

        # Continue until the stack is empty
        while len(chain_stack) > 0:
            cur_exp_name = chain_stack[-1][0]
            cur_exp_def = chain_stack[-1][1]

            # Perform basic validation on the chained experiment definition
            if "name" not in cur_exp_def:
                raise InvalidChainError(
                    "Invalid experiment chain defined:\n"
                    + f"    Primary experiment {parent_namespace}\n"
                    + f"    Chain definition: {str(exp)}\n"
                    + '    "name" keyword must be defined'
                )

            if "order" in cur_exp_def:
                possible_orders = [
                    "after_chain",
                    "after_root",
                    "before_chain",
                    "before_root",
                ]
                if cur_exp_def["order"] not in possible_orders:
                    raise InvalidChainError(
                        "Invalid experiment chain defined:\n"
                        + f"    Primary experiment {parent_namespace}\n"
                        + f"    Chain definition: {str(exp)}\n"
                        + '    Optional keyword "order" must '
                        + f"be one of {str(possible_orders)}\n"
                    )

            if "command" not in cur_exp_def.keys():
                raise InvalidChainError(
                    "Invalid experiment chain defined:\n"
                    + f"    Primary experiment {parent_namespace}\n"
                    + f"    Chain definition: {str(exp)}\n"
                    + '    "command" keyword must be defined'
                )

            if "variables" in cur_exp_def:
                if not isinstance(cur_exp_def["variables"], dict):
                    raise InvalidChainError(
                        "Invalid experiment chain defined:\n"
                        + f"    Primary experiment {parent_namespace}\n"
                        + f"    Chain definition: {str(exp)}\n"
                        + '    Optional keyword "variables" '
                        + "must be a dictionary"
                    )

            base_inst = self.experiment_set.get_experiment(cur_exp_name)
            if base_inst in classes_in_stack:
                chain_stack.pop()
                classes_in_stack.remove(base_inst)

                order = "after_root"
                if "order" in cur_exp_def:
                    order = cur_exp_def["order"]

                chained_name = f"chain.{chain_idx}.{cur_exp_name}"
                new_name = f"{parent_namespace}.{chained_name}"

                new_run_dir = os.path.join(
                    parent_run_dir, namespace.chained_experiments, chained_name
                )

                if order == "before_chain":
                    self.chain_prepend.insert(0, new_name)
                elif order == "before_root":
                    self.chain_prepend.append(new_name)
                elif order == "after_root":
                    self.chain_append.insert(0, new_name)
                elif order == "after_chain":
                    self.chain_append.append(new_name)
                self.chain_commands[new_name] = cur_exp_def[namespace.command]

                # Skip editing the new instance if the base_inst doesn't work
                # This happens if the originating command is `workspace info`
                # The printing experiment set doesn't have access to all
                # of the experiment, so the base_inst command above
                # doesn't get an application instance.
                if base_inst:
                    new_inst = base_inst.clone()

                    if namespace.variables in cur_exp_def:
                        for var, val in cur_exp_def[
                            namespace.variables
                        ].items():
                            new_inst.variables[var] = val

                    new_inst.expander._experiment_namespace = new_name
                    new_inst.variables[self.keywords.experiment_run_dir] = (
                        new_run_dir
                    )
                    new_inst.variables[self.keywords.experiment_name] = (
                        new_name
                    )
                    new_inst.variables[self.keywords.experiment_index] = (
                        self.expander.expand_var_name(
                            self.keywords.experiment_index
                        )
                    )
                    new_inst.repeats = self.repeats
                    new_inst.read_status()

                    # Extract inherited variables
                    if namespace.inherit_variables in cur_exp_def:
                        for inherit_var in cur_exp_def[
                            namespace.inherit_variables
                        ]:
                            new_inst.variables[inherit_var] = self.variables[
                                inherit_var
                            ]

                    # Expand the chained experiment vars, so we can build the execution command
                    new_inst.define_variables_for_template_path(workspace)
                    chain_cmd = new_inst.expander.expand_var(
                        cur_exp_def[namespace.command]
                    )
                    self.chain_commands[new_name] = chain_cmd
                    cur_exp_def[namespace.command] = chain_cmd
                    self.experiment_set.add_chained_experiment(
                        new_name, new_inst
                    )

                chain_idx += 1
            else:
                # Avoid cycles, from children
                if base_inst in classes_in_stack:
                    chain_stack.pop()
                else:
                    if base_inst.chained_experiments:
                        for exp in reversed(base_inst.chained_experiments):
                            for (
                                exp_name
                            ) in self.experiment_set.search_primary_experiments(
                                exp["name"]
                            ):
                                child_inst = (
                                    self.experiment_set.get_experiment(
                                        exp_name
                                    )
                                )
                                if child_inst in classes_in_stack:
                                    raise ChainCycleDetectedError(
                                        "Cycle detected in "
                                        + "experiment chain:\n"
                                        + "    Primary experiment "
                                        + f"{parent_namespace}\n"
                                        + "    Chained expeirment name: "
                                        + f"{cur_exp_name}\n"
                                        + "    Chain definition: "
                                        + f"{str(cur_exp_def)}"
                                    )

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

    def define_variable(self, var_name, var_value):
        self.variables[var_name] = var_value
        self.expander._variables[var_name] = var_value
        for mod_inst in self._modifier_instances:
            mod_inst.define_variable(var_name, var_value)

    def build_modifier_instances(self):
        """Built a map of modifier names to modifier instances needed for this
        application instance
        """

        if not self.modifiers:
            return

        self._modifier_instances = []

        mod_type = ramble.repository.ObjectTypes.modifiers

        for mod in self.modifiers:
            mod_inst = ramble.repository.get(mod["name"], mod_type).copy()

            if "on_executable" in mod:
                mod_inst.set_on_executables(mod["on_executable"])
            else:
                mod_inst.set_on_executables(None)

            if "mode" in mod:
                mode_name = self.expander.expand_var(mod["mode"])
                mod_inst.set_usage_mode(mode_name)
            else:
                mod_inst.set_usage_mode(None)

            if not mod_inst.disabled:
                mod_inst.inherit_from_application(self)
                mod_inst.modify_experiment(self)
                mod_inst.set_modifier_variants()
            else:
                base_class_type = ramble.repository.ObjectTypes.base_classes
                DisabledModifier = ramble.repository.get_obj_class(
                    "disabled-modifier", object_type=base_class_type
                )
                mod_inst = DisabledModifier(mod_inst)

            mod_inst.check_conflicts(self._modifier_instances)
            self._modifier_instances.append(mod_inst)

            # Add this modifiers required variables for validation
            self.keywords.update_keys(mod_inst.required_variables)

        for mod_inst in self._modifier_instances:
            # Ensure no expand vars are set correctly for modifiers
            for var in mod_inst.no_expand_vars():
                self.expander.add_no_expand_var(var)
                mod_inst.expander.add_no_expand_var(var)

            # Define any missing modifier variables
            self.define_missing_variables()

    def validate_experiment(
        self, warn_validation=True, die_on_validate_error=True
    ):
        # Validate the new modifiers variables exist
        # (note: the base ramble variables are checked earlier too)
        self.keywords.check_required_keys(
            self.variables,
            warn_validation=warn_validation,
            die_on_validate_error=die_on_validate_error,
        )
        self._check_object_validators()

    def _check_object_validators(self):
        expander = self.expander
        for _, obj in self._objects():
            for when_set, validator_defs in obj.validators.items():
                if not self.expander.satisfies(
                    when_set, variant_set=self.experiment_variants()
                ):
                    continue

                for name, validator in validator_defs.items():
                    try:
                        valid = expander.evaluate_predicate(
                            validator["predicate"]
                        )
                    except ramble.expander.ExpanderError:
                        valid = False
                    if not valid:
                        msg = expander.expand_var(validator["message"])
                        err_msg = (
                            f"Validator '{name}' (defined in '{obj.name}') "
                            f"fails with message: '{msg}'"
                        )
                        if validator["fail_on_invalid"]:
                            raise ObjectValidationError(err_msg)
                        else:
                            logger.warn(err_msg)

    def _generate_cleanup_cmd(self, key):
        commands = []
        all_cleanups = {}
        for when_set, named_cleanups in self.cleanups.items():
            if self.expander.satisfies(when_set, self.object_variants):
                all_cleanups.update(named_cleanups)

        for name, cleanup_props in all_cleanups.items():
            if not cleanup_props.get(key):
                continue

            if cleanup_props["directory"]:
                dir = self.expander.expand_var(cleanup_props["directory"])
            else:
                dir = self.expander.experiment_run_dir
            regex = self.expander.expand_var(cleanup_props["regex"])
            if cleanup_props["recurse"]:
                recurse_opt = ""
            else:
                recurse_opt = "-maxdepth 1"
            regex_opts = f"-regextype posix-extended -regex '{regex}'"
            delete_opts = "-exec rm -rf {} +"
            find_cmd = f"find '{dir}' -mindepth 1 {recurse_opt} {regex_opts} {delete_opts}"

            commands.append(f"# {key}-cleanup: {name}")
            commands.append(find_cmd)

        return commands

    register_builtin("pre_cleanup", required=True, injection_method="prepend")

    def pre_cleanup(self):
        return self._generate_cleanup_cmd("pre")

    register_builtin("post_cleanup", required=True, injection_method="append")

    def post_cleanup(self):
        return self._generate_cleanup_cmd("post")

    def _get_filtered_and_full_executables(self):
        """Returns a dict of executables that satisfy `when` conditions, and a dict of all the executables"""
        filtered_executables = {}
        all_executables = self.executables.copy()
        full_executables = set().union(*all_executables.values())

        when_satisfied = {
            when_set
            for when_set in all_executables.keys()
            if self.expander.satisfies(
                when_set, variant_set=self.experiment_variants()
            )
        }

        for when_set in when_satisfied:
            executables = all_executables[when_set]
            for executable in executables:
                if executable in filtered_executables:
                    logger.die(
                        f"Executable {executable} is defined for overlapping `when` "
                        "conditions. Ensure conditions are mutually exclusive."
                    )
            filtered_executables.update(executables)

        return filtered_executables, full_executables

    def _define_custom_executables(self):
        # Define custom executables
        if namespace.custom_executables in self.internals:
            for name, conf in self.internals[
                namespace.custom_executables
            ].items():
                filtered_executabls, _ = (
                    self._get_filtered_and_full_executables()
                )
                if (
                    name in filtered_executabls
                    or name in self.custom_executables
                ):
                    experiment_namespace = self.expander.expand_var_name(
                        "experiment_namespace"
                    )
                    raise ExecutableNameError(
                        f"In experiment {experiment_namespace} "
                        f'a custom executable "{name}" is defined.\n'
                        f'However, an executable "{name}" is already '
                        "defined"
                    )

                self.custom_executables[name] = (
                    ramble.util.executable.CommandExecutable(name=name, **conf)
                )

    def _get_executable_graph(self, workload_name):
        """Construct and return an executable graph

        Builds an executable graph for a given workload.

        Returns:
            ExecutableGraph: Graph of executables for workload
        """
        self._define_custom_executables()
        exec_order = self.get_workload(workload_name).executables
        # Use yaml defined executable order, if defined
        if namespace.executables in self.internals:
            exec_order = self.internals[namespace.executables]

        builtin_objects = []
        all_builtins = []
        for _, obj in self._objects():
            for when_set, builtins in obj.builtins.items():
                if self.expander.satisfies(
                    when_set, variant_set=self.experiment_variants()
                ):
                    builtin_objects.append(obj)
                    all_builtins.append(builtins)

        filtered_executables, full_executables = (
            self._get_filtered_and_full_executables()
        )
        filtered_executables.update(self.custom_executables)

        filtered_exec_order = []
        for executable in exec_order:
            if executable in filtered_executables or any(
                executable in b for b in all_builtins
            ):
                filtered_exec_order.append(executable)
            else:
                if executable not in full_executables:
                    logger.die(f"Executable {executable} is not defined.")
                logger.debug(
                    f"Skipping executable {executable}. `When` conditions not satisfied."
                )

        executable_graph = ramble.graphs.ExecutableGraph(
            filtered_exec_order,
            filtered_executables,
            builtin_objects,
            all_builtins,
            self,
        )

        # Perform executable injection
        if namespace.executable_injection in self.internals:
            for exec_injection in self.internals[
                namespace.executable_injection
            ]:
                exec_name = exec_injection["name"]
                order = "before"
                if "order" in exec_injection:
                    order = exec_injection["order"]
                relative_to = None
                if "relative_to" in exec_injection:
                    relative_to = exec_injection["relative_to"]
                executable_graph.inject_executable(
                    exec_name, order, relative_to
                )

        return executable_graph

    def _set_input_path(self):
        """Define input file path variables

        Define variables for each input file, of the format:
            '{input_file_name}' = <path_to_input>
        """
        self._inputs_and_fetchers(self.expander.workload_name)

        for input_file, input_conf in self._input_fetchers.items():
            input_vars = {}
            if input_conf["expand"]:
                input_vars[self.keywords.input_name] = input_conf["input_name"]
            else:
                input_vars[self.keywords.input_name] = input_file

            input_path = os.path.join(
                self.expander.expand_var(
                    os.path.join(input_conf["target_dir"], input_file),
                    extra_vars=input_vars,
                ),
            )
            self.variables[input_conf["input_name"]] = input_path

    @property
    def selected_variables(self):
        """Extract all variables which would be included based
        on the current variants. This overrides the one defined in
        the base mixin.

        Returns:
            (dict) Keys are variable names, values are variable instances
        """

        wl_vars = {}

        workloads = self.get_workloads()
        for workload in workloads:
            for var_when_set, var_list in workload.variables.items():
                if self.expander.satisfies(
                    var_when_set, self.experiment_variants()
                ):
                    for var in var_list:
                        wl_vars[var.name] = var

        for when_key, var_list in self.object_variables.items():
            if self.expander.satisfies(when_key, self.experiment_variants()):
                for var in var_list:
                    wl_vars[var.name] = var

        return wl_vars

    @property
    def selected_environment_variables(self):
        """Extract all environment variables which would be included based
        on the current variants. This overrides the one defined in
        the base mixin.

        Returns:
            (dict) Keys are environment variable names, values are environment
            variable instances
        """

        selected_env_vars = {}

        workloads = self.get_workloads()
        for workload in workloads:
            for (
                when_set,
                env_var_list,
            ) in workload.environment_variables.items():
                if self.expander.satisfies(
                    when_set, self.experiment_variants()
                ):
                    for env_var in env_var_list:
                        selected_env_vars[env_var.name] = env_var

        for (
            when_set,
            env_var_list,
        ) in self.object_environment_variables.items():
            if self.expander.satisfies(when_set, self.experiment_variants()):
                for env_var in env_var_list:
                    selected_env_vars[env_var.name] = env_var

        return selected_env_vars

    @property
    def environment_variable_sets(self):
        """Get environment variable sets for all objects.

        Returns:
            (list) List of environment variable sets from all objects
        """
        obj_env_var_sets = self._env_variable_sets.copy()

        env_var_objs = []
        if self.package_manager is not None:
            env_var_objs.append(self.package_manager)
        if self.workflow_manager is not None:
            env_var_objs.append(self.workflow_manager)
        for mod_inst in self._modifier_instances:
            env_var_objs.append(mod_inst)

        for env_var_obj in env_var_objs:
            obj_env_vars = {}
            for env_var in env_var_obj.selected_environment_variables.values():
                obj_env_vars[env_var.name] = env_var.value

            if obj_env_vars:
                obj_env_var_sets.append({"set": obj_env_vars})

        return obj_env_var_sets

    def _define_commands(self, exec_graph=None, success_list=None):
        """Populate the internal list of commands based on executables

        Populates self._command_list with a list of the executable commands that
        should be executed by this experiment.
        """
        if len(self._command_list) > 0:
            return

        exec_graph = getattr(self, "_executable_graph", exec_graph)
        if exec_graph is None:
            self._executable_graph = self._get_executable_graph(
                self.expander.workload_name
            )
            exec_graph = self._executable_graph

        # Do not replace escaped braces here, to allow them to
        # be replace properly when templates are written.
        with self.expander.preserve_escaped_braces():
            self._command_list = []
            self._command_list_without_logs = []

            success_list = self.success_list
            if not success_list:
                success_list = ramble.success_criteria.ScopedCriteriaList()

            # Inject all prepended chained experiments
            for chained_exp in self.chain_prepend:
                self._command_list.append(self.chain_commands[chained_exp])
                self._command_list_without_logs.append(
                    self.chain_commands[chained_exp]
                )

            # ensure all log files are purged and set up
            logs = []

            for exec_node in exec_graph.walk():
                if isinstance(
                    exec_node.attribute,
                    ramble.util.executable.CommandExecutable,
                ):
                    exec_cmd = exec_node.attribute
                    if exec_cmd.redirect:
                        expanded_log = self.expander.expand_var(
                            exec_cmd.redirect
                        )
                        logs.append(expanded_log)

            analysis_logs, _, _ = self._analysis_dicts(success_list)
            logs = list(set(logs) | analysis_logs.keys())

            for log in logs:
                self._command_list.append(f'rm -f "{log}"')
                self._command_list.append(f'touch "{log}"')

            for exec_node in exec_graph.walk():
                exec_vars = {"executable_name": exec_node.key}

                if isinstance(
                    exec_node.attribute,
                    ramble.util.executable.CommandExecutable,
                ):
                    exec_vars.update(exec_node.attribute.variables)

                for mod in self._modifier_instances:
                    if mod.applies_to_executable(exec_node.key):
                        exec_vars.update(mod.modded_variables(self, exec_vars))

                if isinstance(
                    exec_node.attribute,
                    ramble.util.executable.CommandExecutable,
                ):
                    # Process directive defined executables
                    base_command = exec_node.attribute.copy()
                    pre_commands = []
                    post_commands = []

                    for mod in self._modifier_instances:
                        if mod.applies_to_executable(exec_node.key):
                            pre_cmd, post_cmd = mod.apply_executable_modifiers(
                                exec_node.key, base_command, app_inst=self
                            )
                            pre_commands.extend(pre_cmd)
                            post_commands.extend(post_cmd)

                    command_configs = pre_commands.copy()
                    command_configs.append(base_command)
                    command_configs.extend(post_commands)

                    for cmd_conf in command_configs:
                        mpi_cmd = ""
                        if cmd_conf.mpi:
                            raw_mpi_cmd = self.expander.expand_var(
                                "{mpi_command}",
                                exec_vars,
                            ).strip()
                            if (
                                not raw_mpi_cmd
                                and int(
                                    self.expander.expand_var_name(
                                        self.keywords.n_nodes
                                    )
                                )
                                > 1
                            ):
                                logger.warn(
                                    f"Command {cmd_conf.name} requires a non-empty `mpi_command` "
                                    "variable in a multi-node experiment"
                                )
                            mpi_cmd = " " + raw_mpi_cmd + " "

                        redirect = ""
                        if cmd_conf.redirect:
                            out_log = self.expander.expand_var(
                                cmd_conf.redirect,
                                exec_vars,
                            )
                            output_operator = cmd_conf.output_capture

                            redirect_mapper = output_mapper()
                            redirect = redirect_mapper.generate_out_string(
                                out_log, output_operator
                            )

                        if cmd_conf.run_in_background:
                            bg_cmd = " &"
                        else:
                            bg_cmd = ""

                        for part in cmd_conf.template:
                            command_part = f"{mpi_cmd}{part}"
                            suffix_part = f"{redirect}{bg_cmd}"

                            expanded_cmd = self.expander.expand_var(
                                command_part,
                                exec_vars,
                            ).lstrip()
                            suffix_cmd = self.expander.expand_var(
                                suffix_part,
                                exec_vars,
                            ).lstrip()

                            self._command_list.append(
                                (expanded_cmd + " " + suffix_cmd).rstrip()
                            )
                            self._command_list_without_logs.append(
                                expanded_cmd
                            )

                else:  # All Builtins
                    func = exec_node.attribute
                    func_cmds = func()
                    for cmd in func_cmds:
                        expanded = self.expander.expand_var(cmd, exec_vars)
                        self._command_list.append(expanded)
                        self._command_list_without_logs.append(expanded)

            # Inject all appended chained experiments
            for chained_exp in self.chain_append:
                expanded = self.expander.expand_var(
                    self.chain_commands[chained_exp]
                )
                self._command_list.append(expanded)
                self._command_list_without_logs.append(expanded)

    def _define_formatted_executables(self):
        """Define variables representing the formatted executables

        Process the formatted_executables definitions, and construct their
        variable definitions.

        Each formatted executable definition is injected as its own variable
        based on the formatting requested.
        """

        self.variables[self.keywords.unformatted_command] = "\n".join(
            self._command_list
        )
        self.variables[self.keywords.unformatted_command_without_logs] = (
            "\n".join(self._command_list_without_logs)
        )
        formatted_exec_groups = [{frozenset(): self._formatted_executables}]

        objs_to_extract = [self, self.workflow_manager, self.package_manager]

        for obj in objs_to_extract + self._modifier_instances:
            if obj and hasattr(obj, "formatted_executables"):
                formatted_exec_groups.append(obj.formatted_executables)

        all_execs = {}

        for formatted_exec_group in formatted_exec_groups:
            for when_set, formatted_exec_defs in formatted_exec_group.items():
                if not self.expander.satisfies(
                    when_set, variant_set=self.experiment_variants()
                ):
                    continue

                for var_name, formatted_conf in formatted_exec_defs.items():
                    if var_name in self.variables:
                        raise FormattedExecutableError(
                            f"Formatted executable {var_name} defined, but variable "
                            "definition already exists."
                        )

                    if var_name in all_execs:
                        raise FormattedExecutableError(
                            f"Formatted executable {var_name} already defined."
                        )

                    all_execs[var_name] = formatted_conf

        # Set formatted executable dependencies and order
        formatted_exec_graph = ramble.graphs.FormattedExecutableGraph(
            all_execs, obj_inst=self
        )
        for node in formatted_exec_graph.walk():
            formatted_conf = node.attribute

            # Create the formatted command for the executable
            n_indentation = 0
            if namespace.indentation in formatted_conf:
                n_indentation = int(formatted_conf[namespace.indentation])

            prefix = ""
            if namespace.prefix in formatted_conf:
                prefix = formatted_conf[namespace.prefix]

            join_separator = "\n"
            if namespace.join_separator in formatted_conf:
                join_separator = formatted_conf[
                    namespace.join_separator
                ].replace(r"\n", "\n")

            indentation = " " * n_indentation

            commands_to_format = self._command_list
            if namespace.commands in formatted_conf:
                commands_to_format = formatted_conf[namespace.commands].copy()

            formatted_lines = []
            for command in commands_to_format:
                # Do not replace escaped braces here, to allow them to
                # be replace properly when templates are written.
                expanded = self.expander.expand_var(
                    command, replace_escaped_braces=False
                )

                for out_line in expanded.split("\n"):
                    formatted_lines.append(indentation + prefix + out_line)

            self.variables[node.key] = join_separator.join(formatted_lines)

    def define_variables_for_template_path(self, workspace):
        """Define variables for all workspace and object template paths"""
        for template_name, _ in workspace.all_templates():
            expand_path = os.path.join(
                self.expander.expand_var("{experiment_run_dir}"),
                template_name,
            )
            self.variables[template_name] = expand_path

        var_attr = {
            "type": ramble.keywords.key_type.reserved,
            "level": ramble.keywords.output_level.variable,
        }
        for obj, tpl_config in self._object_templates(workspace):
            var_name = tpl_config["var_name"]
            if var_name is not None:
                if var_name in self.variables:
                    old_var = f"_old_{var_name}"
                    self.variables[old_var] = self.variables[var_name]
                    self.keywords.update_keys({old_var: var_attr})
                self.variables[var_name] = tpl_config["dest_path"]
                self.keywords.update_keys({var_name: var_attr})
            if hasattr(obj, "template_render_vars"):
                render_vars = obj.template_render_vars
                self.variables.update(render_vars)
                for name in render_vars.keys():
                    self.keywords.update_keys({name: var_attr})

    def _inputs_and_fetchers(self, workload=None):
        """Extract all inputs for a given workload

        Take a workload name and extract all inputs for the workload.
        If the workload is set to None, extract all inputs for all workloads.
        """

        if self._input_fetchers is not None:
            return

        self._input_fetchers = {}

        # Batch 'when' evaluation to avoid repeat expander calls
        when_satisfied = {
            when_set
            for when_set in self.inputs.keys()
            if self.expander.satisfies(
                when_set, variant_set=self.experiment_variants()
            )
        }

        inputs = {}
        workloads = (
            [self.get_workload(workload)]
            if workload
            else self.get_all_workloads()
        )
        for workload in workloads:
            for input_file in workload.inputs:
                inputs_found = 0
                active_inputs = 0
                input_conf = {}
                for when_set, app_inputs in self.inputs.items():
                    if input_file in app_inputs:
                        inputs_found += 1
                        if when_set in when_satisfied:
                            active_inputs += 1
                            input_conf = app_inputs[input_file].copy()

                if not inputs_found:
                    logger.die(
                        f"Workload {workload.name} references a non-existent input file "
                        f"{input_file}.\n"
                        f"Make sure this input file is defined before using it in a workload."
                    )
                if active_inputs == 0:
                    logger.debug(
                        f"Skipping input {input_file}. `When` conditions not satisfied."
                    )
                    continue
                elif active_inputs > 1:
                    logger.die(
                        f"Input files {input_file} are defined with overlapping 'when' "
                        f"conditions. Make sure that conditions are mutually exclusive."
                    )

                # Expand input value as it may be a var
                expanded_url = self.expander.expand_var(input_conf["url"])
                input_conf["url"] = expanded_url

                fetcher = ramble.fetch_strategy.URLFetchStrategy(**input_conf)

                file_name = os.path.basename(input_conf["url"])
                if not fetcher.extension:
                    fetcher.extension = spack.util.compression.extension(
                        file_name
                    )

                file_name = file_name.replace(f".{fetcher.extension}", "")

                namespace = f"{self.name}.{workload.name}"

                inputs[file_name] = {
                    "fetcher": fetcher,
                    "namespace": namespace,
                    "target_dir": input_conf["target_dir"],
                    "extension": fetcher.extension,
                    "input_name": input_file,
                    "expand": input_conf["expand"],
                }
        self._input_fetchers = inputs

    register_phase("mirror_inputs", pipeline="mirror")

    def _mirror_inputs(self, workspace, app_inst=None):
        """Mirror application inputs

        Perform mirroring of inputs within this application class.
        """
        mirror_lock = lk.Lock(
            os.path.join(workspace.input_mirror_path, ".ramble-mirror")
        )
        self._inputs_and_fetchers(self.expander.workload_name)

        with lk.WriteTransaction(mirror_lock):
            for input_file, input_conf in self._input_fetchers.items():
                mirror_paths = ramble.mirror.mirror_archive_paths(
                    input_conf["fetcher"], os.path.join(self.name, input_file)
                )
                fetch_dir = os.path.join(
                    workspace.input_mirror_path, self.name
                )
                fs.mkdirp(fetch_dir)
                stage = ramble.stage.InputStage(
                    input_conf["fetcher"],
                    name=input_conf["namespace"],
                    path=fetch_dir,
                    mirror_paths=mirror_paths,
                    lock=False,
                )

                stage.cache_mirror(
                    workspace.input_mirror_cache, workspace.input_mirror_stats
                )

    register_phase("get_inputs", pipeline="setup")

    def _get_inputs(self, workspace, app_inst=None):
        """Download application inputs

        Download application inputs into the proper directory within the workspace.
        """
        workload_namespace = self.expander.workload_namespace

        self._inputs_and_fetchers(self.expander.workload_name)

        for input_file, input_conf in self._input_fetchers.items():
            if not workspace.dry_run:
                input_vars = {
                    self.keywords.input_name: input_conf["input_name"]
                }
                input_namespace = workload_namespace + "." + input_file
                input_path = self.expander.expand_var(
                    os.path.join(input_conf["target_dir"], input_file),
                    extra_vars=input_vars,
                )
                input_tuple = (f"input-file-{input_file}", input_path)

                # Skip inputs that have already been cached
                if workspace.check_cache(input_tuple):
                    continue

                mirror_paths = ramble.mirror.mirror_archive_paths(
                    input_conf["fetcher"], os.path.join(self.name, input_file)
                )

                input_dir = os.path.dirname(input_path)
                input_base = os.path.basename(input_path)

                input_lock = lk.Lock(os.path.join(input_dir, ".ramble-input"))

                with lk.WriteTransaction(input_lock):
                    with ramble.stage.InputStage(
                        input_conf["fetcher"],
                        name=input_namespace,
                        path=input_dir,
                        mirror_paths=mirror_paths,
                    ) as stage:
                        stage.set_subdir(input_base)
                        try:
                            stage.fetch()
                            if input_conf["fetcher"].digest:
                                stage.check()
                            stage.cache_local()

                            if input_conf["expand"]:
                                try:
                                    stage.expand_archive()
                                except spack.util.executable.ProcessError:
                                    pass
                        except ramble.fetch_strategy.FetchError as e:
                            logger.all_msg(
                                f"Failed fetching input {input_file} in application {self.name}"
                            )
                            logger.all_msg(
                                f"Input url was: {input_conf['fetcher'].url}"
                            )
                            logger.die(str(e))

                workspace.add_to_cache(input_tuple)
            else:
                logger.msg(
                    f'DRY-RUN: Would download {input_conf["fetcher"].url}'
                )

    def _prepare_license_path(self, workspace):
        self.license_path = os.path.join(
            workspace.shared_license_dir, self.name
        )
        self.license_file = os.path.join(
            self.license_path, constants.LICENSE_INC_NAME
        )

        fs.mkdirp(self.license_path)

    register_phase("license_includes", pipeline="setup")

    def _license_includes(self, workspace, app_inst=None):
        logger.debug("Writing License Includes")
        self._prepare_license_path(workspace)

        action_funcs = ramble.util.env.action_funcs
        config_scopes = ramble.config.scopes()
        shell = ramble.config.get("config:shell")
        var_set = set()
        for scope in config_scopes:
            license_conf = ramble.config.config.get_config(
                "licenses", scope=scope
            )
            if license_conf:
                # If we have multiple matches, the last entry should win (latest in hierarchy)
                app_licenses = {}
                for lic in self.license_names:
                    if lic in license_conf:
                        app_licenses = license_conf[lic]

                for action, conf in app_licenses.items():
                    (env_cmds, var_set) = action_funcs[action](
                        conf, self.expander, var_set, shell=shell
                    )

                    lock = lk.Lock(
                        os.path.join(self.license_path, ".ramble-license")
                    )
                    with lk.WriteTransaction(lock):
                        with open(self.license_file, "w+") as f:
                            for cmd in env_cmds:
                                if cmd:
                                    f.write(
                                        self.expander.expand_var(cmd) + "\n"
                                    )

    register_phase(
        "make_experiments", pipeline="setup", run_after=["get_inputs"]
    )

    def _make_experiments(self, workspace, app_inst=None):
        """Create experiment directories

        Create the experiment this application encapsulates. This includes
        creating the experiment run directory, rendering the necessary
        templates, and injecting the experiment into the workspace all
        experiments file.
        """

        _check_shell_support(self)

        exp_lock = self.experiment_lock

        self._set_input_path()
        self._define_commands(success_list=self.success_list)
        self._define_formatted_executables()

        with lk.WriteTransaction(exp_lock):
            experiment_run_dir = self.expander.experiment_run_dir
            fs.mkdirp(experiment_run_dir)

            exec_vars = {}

            for mod in self._modifier_instances:
                exec_vars.update(mod.modded_variables(self, exec_vars))

            for template_name, template_conf in workspace.all_templates():
                expand_path = os.path.join(experiment_run_dir, template_name)
                logger.msg(
                    f"Writing template {template_name} to {expand_path}"
                )
                fs.mkdirp(os.path.dirname(expand_path))

                with open(expand_path, "w+") as f:
                    f.write(
                        self.expander.expand_var(
                            template_conf["contents"], extra_vars=exec_vars
                        )
                    )
                os.chmod(expand_path, _DEFAULT_CONTENT_PERM)

            self._render_object_templates(exec_vars, workspace)

            experiment_script = workspace.experiments_script
            experiment_script.write(
                self.expander.expand_var("{batch_submit}\n")
            )

        self.set_status(status=ExperimentStatus.SETUP)

    def _clean_hash_variables(self, workspace, variables):
        """Cleanup variables to hash before computing the hash

        Perform some general cleanup operations on variables
        before hashing, to help give useful hashes.
        """

        remove_variables = [
            "workspace_name",
            "experiment_hash",
            "experiment_status",
            "RAMBLE_STATUS",
        ]

        # Remove some variables that don't affect the experiment, and change
        # frequently (or are actually output variables)
        for var in remove_variables:
            if var in variables:
                del variables[var]

        # Remove the workspace path from variable definitions before hashing
        for var in variables:
            if isinstance(variables[var], str):
                variables[var] = variables[var].replace(
                    workspace.root, "$workspace_root"
                )

    def variant_inventory(self):
        """Construct a list of all variants from any object in the experiment,
        for the experiment's inventory.

        Returns:
            (list[str]): List of variant definitions from all objects
        """

        variant_definitions = set()

        for _, obj in self._objects():
            variant_definitions = variant_definitions.union(
                obj.experiment_variants(app_inst=self).as_set()
            )

        return list(sorted(variant_definitions))

    def _purge_inventory(self):
        self.hash_inventory = {
            "object_configuration": [],
            "attributes": [],
            "inputs": [],
            "software": [],
            "templates": [],
        }
        self.experiment_hash = None

    def populate_inventory(
        self,
        workspace,
        force_compute: bool = False,
    ) -> bool:
        """Populate this experiment's hash inventory

        If an inventory file exists, read it first.
        If it does not exist, compute it using the internal information.

        If force_compute is set to true, always compute and never read.

        Args:
            force_compute: Boolean that allows forces the inventory to be computed instead of read
                           Used in pipelines that should create the inventory, instead of
                           consuming it.
        """

        changed = False
        self._purge_inventory()

        experiment_run_dir = self.expander.experiment_run_dir
        inventory_file = os.path.join(
            experiment_run_dir, self._inventory_file_name
        )

        force = force_compute or ramble.config.get(
            "config:overwrite_inventories", default=False
        )

        existing_hash = None
        if os.path.exists(inventory_file) and not force:
            with open(inventory_file) as f:
                existing_inventory = spack.util.spack_json.load(f)
            existing_hash = ramble.util.hashing.hash_json(existing_inventory)

        # Clean up variables before hashing
        vars_to_hash = self.variables.copy()
        self._clean_hash_variables(workspace, vars_to_hash)

        # Build inventory of attributes
        attributes_to_hash = [
            ("variables", vars_to_hash),
            ("modifiers", self.modifiers),
            ("variants", self.variant_inventory()),
            ("chained_experiments", self.chained_experiments),
            ("internals", self.internals),
            ("env_vars", self._env_variable_sets),
        ]

        added_objects = {}
        for obj_type, obj in self._objects():
            if obj_type not in added_objects:
                added_objects[obj_type] = set()

            if obj.name not in added_objects[obj_type]:
                added_objects[obj_type].add(obj.name)
                object_inventory = {
                    "name": obj.name,
                    "object_type": obj_type.name,
                    "digest": ramble.util.hashing.hash_file(obj._file_path),
                }

                version_func = getattr(obj, "get_version", None)
                if version_func is not None and callable(version_func):
                    object_inventory["version"] = obj.get_version(
                        workspace=workspace
                    )

                if obj is not self:
                    populate_func = getattr(obj, "populate_inventory", None)
                    if populate_func is not None and callable(populate_func):
                        obj.populate_inventory(workspace, force)

                artifact_func = getattr(obj, "artifact_inventory", None)
                if artifact_func is not None and callable(artifact_func):
                    inventory = obj.artifact_inventory(workspace, self)
                    if inventory:
                        if hasattr(obj, "_usage_mode"):
                            object_inventory["mode"] = obj._usage_mode
                        object_inventory["artifacts"] = inventory

                self.hash_inventory["object_configuration"].append(
                    object_inventory
                )

        for attr, attr_dict in attributes_to_hash:
            self.hash_inventory["attributes"].append(
                {
                    "name": attr,
                    "digest": ramble.util.hashing.hash_json(attr_dict),
                }
            )

        # Build inventory of workspace templates
        for template_name, template_conf in workspace.all_templates():
            self.hash_inventory["templates"].append(
                {
                    "name": template_name,
                    "digest": template_conf["digest"],
                }
            )

        # Build inventory of inputs
        self._inputs_and_fetchers(self.expander.workload_name)

        for input_conf in self._input_fetchers.values():
            if input_conf["fetcher"].digest:
                self.hash_inventory["inputs"].append(
                    {
                        "name": input_conf["input_name"],
                        "digest": input_conf["fetcher"].digest,
                    }
                )
            else:
                self.hash_inventory["inputs"].append(
                    {
                        "name": input_conf["input_name"],
                        "digest": ramble.util.hashing.hash_string(
                            input_conf["fetcher"].url
                        ),
                    }
                )

        self.experiment_hash = ramble.util.hashing.hash_json(
            self.hash_inventory
        )

        # Compare inventory hashes, to validate experiment hasn't changed
        if existing_hash is not None and self.experiment_hash != existing_hash:
            logger.die(
                f"Mismatch on experiment hash for experiment {self.expander.experiment_namespace}.\n"
                f"  Hash from experiment directory: {existing_hash}\n"
                f"  Hash computed current config: {self.experiment_hash}\n"
                "To overwrite the experiment hash, use the global --overwrite-inventories option"
            )

        self.variables[self.keywords.experiment_hash] = self.experiment_hash

        # Write out experiment inventory, if hash is different
        if existing_hash != self.experiment_hash:
            changed = True

        writable = True
        if self.repeats.is_repeat_base:
            writable = False

        if changed and writable:
            with lk.WriteTransaction(self.experiment_lock):
                with open(inventory_file, "w+") as f:
                    spack.util.spack_json.dump(self.hash_inventory, f)

        return changed

    register_phase("archive_experiments", pipeline="archive")

    def _archive_experiments(self, workspace, app_inst=None):
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

        archive_experiment_dir = experiment_run_dir.replace(
            workspace.root, ws_archive_dir
        )

        fs.mkdirp(archive_experiment_dir)

        archive_lock = lk.Lock(
            os.path.join(archive_experiment_dir, ".ramble-exp-archive")
        )

        with lk.WriteTransaction(archive_lock):
            # Copy all log files from executables
            exec_logs = set()
            workload = self.get_workload()
            filtered_executables, _ = self._get_filtered_and_full_executables()
            for exec_name in workload.executables:
                if exec_name in filtered_executables:
                    exec_obj = filtered_executables[exec_name]
                    exec_log = self.expander.expand_var(exec_obj.redirect)
                    exec_logs.add(exec_log)

            for exec_log in exec_logs:
                file = exec_log
                if not os.path.isabs(file):
                    file = os.path.join(experiment_run_dir, exec_log)

                if os.path.isfile(file):
                    dest_dir = os.path.dirname(
                        file.replace(workspace.root, ws_archive_dir)
                    )
                    fs.mkdirp(dest_dir)
                    shutil.copy(file, dest_dir)

            # Copy all of the templates to the archive directory
            for template_name, _ in workspace.all_templates():
                src = os.path.join(experiment_run_dir, template_name)
                if os.path.exists(src):
                    shutil.copy(src, archive_experiment_dir)

            # Copy all rendered templates generated by `register_template`
            for _, tpl_config in self._object_templates(workspace):
                src_path = tpl_config["dest_path"]
                if os.path.exists(src_path):
                    shutil.copy(src_path, archive_experiment_dir)

            # Copy all figure of merit files
            criteria_list = self.success_list
            analysis_files, _, _ = self._analysis_dicts(criteria_list)
            for file in analysis_files.keys():
                if os.path.exists(file):
                    shutil.copy(file, archive_experiment_dir)

            # Copy all archive patterns
            archive_patterns = set(self.archive_patterns.keys())
            if self.package_manager:
                for pattern in self.package_manager.archive_patterns.keys():
                    archive_patterns.add(pattern)

            for mod in self._modifier_instances:
                for pattern in mod.archive_patterns.keys():
                    archive_patterns.add(pattern)

            for pattern in archive_patterns:
                exp_pattern = self.expander.expand_var(pattern)
                for file in glob.glob(exp_pattern):
                    dest_dir = os.path.dirname(
                        file.replace(workspace.root, ws_archive_dir)
                    )
                    fs.mkdirp(dest_dir)
                    shutil.copy(file, dest_dir)

            for file_name in [
                self._inventory_file_name,
                self._status_file_name,
            ]:
                file = os.path.join(experiment_run_dir, file_name)
                if os.path.exists(file):
                    shutil.copy(file, archive_experiment_dir)

    register_phase("prepare_analysis", pipeline="analyze")

    def _prepare_analysis(self, workspace, app_inst=None):
        """Prepapre experiment for analysis extraction

        This function performs any actions that are necessary before the
        figures of merit, and success criteria can be properly extracted.

        This function can be overridden at the application level to perform
        application specific processing of the output.
        """
        pass

    def _extract_inmem_foms(self, inmem_fom_defs, fom_values):
        """Extract in-memory FOMs"""
        for context, foms in inmem_fom_defs.items():
            if context not in fom_values:
                fom_values[context] = {}
            foms = inmem_fom_defs[context]["foms"]
            for fom in foms:
                fom_conf = inmem_fom_defs[context]["foms"][fom]
                # Currently inmem FOM does not have semantics for expanded vars,
                # so use the already expanded name and unit
                fom_name = fom_conf["fom_name_expanded"]
                # TODO: this can be extended to support derived FOMs,
                # since the `fom_values` contains resolved file-based FOMs
                fom_map_key = fom_conf["fom_map_key"]
                if fom_map_key not in self._fom_map:
                    continue
                fom_value = self._fom_map.get(fom_map_key)
                expanded_fom_value = self.expander.expand_var(fom_value)
                fom_values[context][fom_name] = {
                    "value": expanded_fom_value,
                    "units": fom_conf["units_expanded"],
                    "origin": fom_conf["origin"],
                    "origin_type": fom_conf["origin_type"],
                    "fom_type": fom_conf["fom_type"],
                }

    register_phase(
        "analyze_experiments",
        pipeline="analyze",
        run_after=["prepare_analysis"],
    )

    def _analyze_experiments(self, workspace, app_inst=None):
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

        if (
            self.get_status() == ExperimentStatus.UNKNOWN
            and not workspace.dry_run
        ):
            logger.warn(
                f"Experiment has status {self.get_status()}. Skipping analysis..\n"
            )
            self.result.finalize()
            return

        def format_context(context_match, context_format):

            context_val = {}
            if isinstance(context_format, str):
                for group in string.Formatter().parse(context_format):
                    if group[1]:
                        context_val[group[1]] = context_match[group[1]]

            context_string = context_format.format(**context_val)
            return context_string

        criteria_list = self.success_list
        if not criteria_list:
            criteria_list = ramble.success_criteria.ScopedCriteriaList()
        criteria_list.reset()

        files, f_defs, inmem_defs = self._analysis_dicts(criteria_list)

        exp_lock = self.experiment_lock

        fom_values = {}
        # Iterate over files. We already know they exist
        with lk.ReadTransaction(exp_lock):
            for file, file_conf in files.items():

                # Start with no active contexts in a file.
                active_contexts = {}
                logger.debug(f"Reading log file: {file}")

                if not os.path.exists(file):
                    logger.debug(
                        f"Skipping analysis of non-existent file: {file}"
                    )
                    continue

                per_file_crit_objs = [
                    criteria_list.find_criteria(c)
                    for c in file_conf["success_criteria"]
                ]

                with open(file) as f:
                    for line in f.readlines():
                        new_per_file_crit_objs = []
                        for crit_obj in per_file_crit_objs:
                            if crit_obj.passed(line, self):
                                crit_obj.mark_found()
                            elif crit_obj.anti_matched(line):
                                crit_obj.mark_anti_found()
                            else:
                                new_per_file_crit_objs.append(crit_obj)
                        per_file_crit_objs = new_per_file_crit_objs

                        # Iterate over contexts and add matched contexts to active_contexts
                        for context, foms in file_conf["contexts"].items():
                            if not context == _NULL_CONTEXT:
                                context_conf = f_defs[context]["definition"]
                                context_match = context_conf["regex"].match(
                                    line
                                )

                                if context_match:
                                    context_name = format_context(
                                        context_match, context_conf["format"]
                                    )
                                    logger.debug("Line was: %s" % line)
                                    logger.debug(
                                        f" Context match {context} -- {context_name}"
                                    )

                                    active_contexts[context] = context_name

                                    if context_name not in fom_values:
                                        fom_values[context_name] = {}

                            for fom in foms:
                                fom_conf = f_defs[context]["foms"][fom]
                                fom_match = fom_conf["regex"].match(line)

                                if fom_match:
                                    fom_vars = {}
                                    for k, v in fom_match.groupdict().items():
                                        fom_vars[k] = v
                                    if (
                                        fom_conf["fom_name_expanded"]
                                        is not None
                                    ):
                                        fom_name = fom_conf[
                                            "fom_name_expanded"
                                        ]
                                    else:
                                        fom_name = self.expander.expand_var(
                                            fom, extra_vars=fom_vars
                                        )

                                    if (
                                        fom_conf["group"]
                                        in fom_conf["regex"].groupindex
                                    ):
                                        logger.debug(
                                            " --- Matched fom %s" % fom_name
                                        )
                                        fom_contexts = []
                                        # if a FOM has contexts, check if each is active
                                        if fom_conf["contexts"]:
                                            for _ in fom_conf["contexts"]:
                                                context_name = (
                                                    active_contexts[context]
                                                    if context
                                                    in active_contexts
                                                    else _NULL_CONTEXT
                                                )
                                                fom_contexts.append(
                                                    context_name
                                                )
                                        else:
                                            fom_contexts.append(_NULL_CONTEXT)

                                        for fom_context in fom_contexts:
                                            if fom_context not in fom_values:
                                                fom_values[fom_context] = {}
                                            fom_val = fom_match.group(
                                                fom_conf["group"]
                                            )
                                            if (
                                                fom_conf["units_expanded"]
                                                is not None
                                            ):
                                                fom_unit = fom_conf["units"]
                                            else:
                                                fom_unit = (
                                                    self.expander.expand_var(
                                                        fom_conf["units"],
                                                        extra_vars=fom_vars,
                                                    )
                                                )
                                            fom_values[fom_context][
                                                fom_name
                                            ] = {
                                                "value": fom_val,
                                                "units": fom_unit,
                                                "origin": fom_conf["origin"],
                                                "origin_type": fom_conf[
                                                    "origin_type"
                                                ],
                                                "fom_type": fom_conf[
                                                    "fom_type"
                                                ],
                                            }
        self._extract_inmem_foms(inmem_defs, fom_values)

        # Test all non-file based success criteria
        for criteria_obj, _ in criteria_list.all_criteria():
            if criteria_obj.file is None:
                if criteria_obj.passed(app_inst=self, fom_values=fom_values):
                    criteria_obj.mark_found()

        # If an app has no FOMs defined, don't fail it for that
        success = (not f_defs and not inmem_defs) or False
        for fom in fom_values.values():
            for value in fom.values():
                if (
                    "origin_type" in value
                    and value["origin_type"] == "application"
                ):
                    success = True
        success = success and criteria_list.passed()

        status = self.get_status()
        if status == ExperimentStatus.SUCCESS and not success:
            status = ExperimentStatus.FAILED
        elif success:
            status = ExperimentStatus.SUCCESS

        # When workflow_manager is present, only use app_status when workflow is completed or
        # unresolved.
        if self.workflow_manager is not None:
            wm_status = self.workflow_manager.get_status(workspace)
            if not (
                wm_status is None
                or wm_status
                in [ExperimentStatus.COMPLETE, ExperimentStatus.UNRESOLVED]
            ):
                status = wm_status

        self.set_status(status)

        self.result.finalize()

        for criteria_obj, criteria_scope in criteria_list.all_criteria():
            if criteria_obj.owner is not None:
                criteria_name = (
                    f"{criteria_obj.owner.scoped_name}::{criteria_obj.name}"
                )
            else:
                criteria_name = (
                    f"config::{criteria_scope}::{criteria_obj.name}"
                )
            if criteria_obj.ok():
                self.result.success_criteria[criteria_name] = "PASSED"
            else:
                self.result.success_criteria[criteria_name] = "FAILED"

        for context, fom_map in fom_values.items():
            context_map = {
                "name": context,
                "foms": [],
                "display_name": _get_context_display_name(context),
            }

            for fom_name, fom in fom_map.items():
                fom_copy = fom.copy()
                fom_copy["name"] = fom_name
                context_map["foms"].append(fom_copy)

            if context == _NULL_CONTEXT:
                self.result.contexts.insert(0, context_map)
            else:
                self.result.contexts.append(context_map)

    register_phase(
        "append_results_to_workspace",
        pipeline="analyze",
        run_after=["analyze_experiments"],
    )

    def _append_results_to_workspace(self, workspace, app_inst=None):
        """Phase for injected experiment results into workspace results

        This allows an experiment to register its results into the workspace,
        so when the workspace dumps results they are included.
        """

        if hasattr(self, "result") and self.result is not None:
            workspace.append_result(self.result.to_dict())

    def calculate_statistics(self, workspace):
        """Calculate statistics for results of repeated experiments

        When repeated experiments are used, this method aggregates the results of
        each experiment's repeats and calculates statistics for each numeric FOM.

        If a FOM is non-numeric, no calculations are performed.

        Statistics are injected into the results file under the base experiment
        namespace.
        """

        def is_numeric_fom(fom):
            """Returns true if a fom value is numeric, and of an applicable type"""

            value = fom["value"]
            try:
                value = float(value)
                if (
                    fom["fom_type"]["name"] is FomType.CATEGORY.name
                    or fom["fom_type"]["name"] is FomType.INFO.name
                ):
                    return False
                return True
            except (ValueError, TypeError):
                return False

        if not self.repeats.is_repeat_base:
            return

        repeat_experiments = {}
        repeat_foms = {}
        first_repeat_exp = ""

        # repeat_experiments dict = {repeat_experiment_namespace: {dict}}
        # repeat_foms dict = {context: {(fom_name, units, origin, origin_type): [list of values]}}
        # origin_type is generated as 'summary::stat_name'

        base_exp_name = self.expander.experiment_name
        base_exp_namespace = self.expander.experiment_namespace

        # Create a list of all repeats by inserting repeat index
        for n in range(1, self.repeats.n_repeats + 1):
            if (
                base_exp_name in self.experiment_set.chained_experiments.keys()
                and base_exp_name not in self.experiment_set.experiments.keys()
            ):
                insert_idx = base_exp_name.find(".chain")
                repeat_exp_namespace = (
                    base_exp_name[:insert_idx]
                    + f".{n}"
                    + base_exp_name[insert_idx:]
                )
            else:
                base_exp_namespace = self.expander.experiment_namespace
                repeat_exp_namespace = f"{base_exp_namespace}.{n}"
            repeat_experiments[repeat_exp_namespace] = {}
            repeat_experiments[repeat_exp_namespace][
                "base_exp"
            ] = base_exp_namespace
            if n == 1:
                first_repeat_exp = repeat_exp_namespace

        # If repeat_success_strict is true, one failed experiment will fail the whole set
        # If repeat_success_strict is false, any passing experiment will pass the whole set
        repeat_success = False
        exp_status_list = []
        for exp in repeat_experiments.keys():
            if exp in self.experiment_set.experiments.keys():
                exp_inst = self.experiment_set.experiments[exp]
            elif exp in self.experiment_set.chained_experiments.keys():
                exp_inst = self.experiment_set.chained_experiments[exp]
            else:
                continue

            exp_status_list.append(exp_inst.get_status())

        if workspace.repeat_success_strict:
            if ExperimentStatus.FAILED in exp_status_list:
                repeat_success = False
            else:
                repeat_success = True
        else:
            if ExperimentStatus.SUCCESS in exp_status_list:
                repeat_success = True
            else:
                repeat_success = False

        if repeat_success:
            self.set_status(status=ExperimentStatus.SUCCESS)
        else:
            self.set_status(status=ExperimentStatus.FAILED)

        self.result.finalize()

        logger.debug(
            f"Calculating statistics for {self.repeats.n_repeats} repeats of {base_exp_name}"
        )

        results = []

        # Iterate through repeat experiment instances, extract foms, and aggregate them
        for exp in repeat_experiments.keys():
            if exp in self.experiment_set.experiments.keys():
                exp_inst = self.experiment_set.experiments[exp]
            elif exp in self.experiment_set.chained_experiments.keys():
                exp_inst = self.experiment_set.chained_experiments[exp]
            else:
                continue

            # When strict success is off for repeats (loose success), skip failed exps
            if exp_inst.result.status == ExperimentStatus.FAILED:
                continue

            if exp_inst.result.contexts:
                for context in exp_inst.result.contexts:
                    context_name = context["name"]

                    if context_name not in repeat_foms.keys():
                        repeat_foms[context_name] = {}

                    for fom in context["foms"]:
                        fom_key = (
                            fom["name"],
                            fom["units"],
                            fom["origin"],
                            fom["origin_type"],
                        )

                        # Stats will not be calculated for non-numeric foms so they're skipped
                        if fom_key not in repeat_foms[context_name].keys():
                            repeat_foms[context_name][fom_key] = {
                                "fom_type": fom["fom_type"],
                                "fom_values": [],
                            }
                            if is_numeric_fom(fom):
                                repeat_foms[context_name][fom_key][
                                    "fom_is_numeric"
                                ] = True
                            else:
                                repeat_foms[context_name][fom_key][
                                    "fom_is_numeric"
                                ] = False
                            fom_contents = (
                                False,
                                fom["value"],
                                fom["fom_type"],
                            )
                        if repeat_foms[context_name][fom_key][
                            "fom_is_numeric"
                        ]:
                            repeat_foms[context_name][fom_key][
                                "fom_values"
                            ].append(float(fom["value"]))
                        else:
                            repeat_foms[context_name][fom_key][
                                "fom_values"
                            ].append(fom["value"])

        # Iterate through the aggregated foms, calculate stats, and insert into results
        for context, fom_dict in repeat_foms.items():
            if not fom_dict:
                continue

            context_map = {
                "name": context,
                "foms": [],
                "display_name": _get_context_display_name(context),
            }

            summary_foms = []
            if context == _NULL_CONTEXT:
                # Use the app name as the origin of the FOM
                summary_origin = self.name
                n_total_dict = {
                    "value": self.repeats.n_repeats,
                    "units": "repeats",
                    "origin": summary_origin,
                    "origin_type": f"summary::{SummaryFoms.N_TOTAL.value}",
                    "name": SummaryFoms.SUMMARY.value,
                    "fom_type": FomType.MEASURE.to_dict(),
                }
                summary_foms.append(n_total_dict)

                n_success = exp_status_list.count(ExperimentStatus.SUCCESS)

                n_success_dict = {
                    "value": n_success,
                    "units": "repeats",
                    "origin": summary_origin,
                    "origin_type": f"summary::{SummaryFoms.N_SUCCESS.value}",
                    "name": SummaryFoms.SUMMARY.value,
                    "fom_type": FomType.MEASURE.to_dict(),
                }
                summary_foms.append(n_success_dict)

            for fom_key, fom_contents in fom_dict.items():
                fom_name, fom_units, fom_origin, fom_origin_type = fom_key

                fom_type = fom_contents["fom_type"]
                fom_values = fom_contents["fom_values"]

                if fom_contents["fom_is_numeric"]:
                    calcs = []

                    for statistic in ramble.util.stats.all_stats:
                        calcs.append(statistic.report(fom_values, fom_units))

                    for calc in calcs:
                        if calc[0] == ramble.util.stats.NA:
                            continue
                        fom_calc_dict = {
                            "value": calc[0],
                            "units": calc[1],
                            "origin": fom_origin,
                            "origin_type": calc[2],
                            "name": fom_name,
                            "fom_type": fom_type,
                        }

                        context_map["foms"].append(fom_calc_dict)
                else:
                    # Only elevate non-numeric FOMs when they have the same value for all repeats
                    if len(set(fom_values)) == 1:

                        fom_str_dict = {
                            "value": fom_values[0],
                            "units": fom_units,
                            "origin": fom_origin,
                            "origin_type": fom_origin_type,
                            "name": fom_name,
                            "fom_type": fom_type,
                        }

                        context_map["foms"].append(fom_str_dict)
                    else:
                        continue

            # Display the FOMs in alphabetic order, even if the corresponding log entries
            # may be in different ordering.
            context_map["foms"].sort(key=operator.itemgetter("name"))
            if context == _NULL_CONTEXT:
                context_map["foms"] = summary_foms + context_map["foms"]
            results.append(context_map)

        if results:
            self.result.contexts = results

        workspace.insert_result(self.result.to_dict(), first_repeat_exp)

    def _new_file_dict(self):
        """Create a dictionary to represent a new log file"""
        return {"success_criteria": [], "contexts": {}}

    def _analysis_dicts(self, criteria_list):
        """Extract files that need to be analyzed.

        Process figures_of_merit, and return the manipulated dictionaries
        to allow them to be extracted.

        Additionally, ensure the success criteria list is complete.

        Returns:
            files (dict): All files that need to be processed
            file_fom_defs (dict): Definitions of all file-backed FOMs to be extracted
            inmem_fom_defs (dict): Definitions of all in-memory FOMs to be extracted
        """

        files = {}
        file_fom_defs = {}
        inmem_fom_defs = {}

        # Add the application defined criteria
        criteria_list.flush_scope("application_definition")

        success_lists = [
            ("application_definition", self, self.success_criteria),
        ]

        logger.debug(
            f" Number of modifiers are: {len(self._modifier_instances)}"
        )
        if self._modifier_instances:
            criteria_list.flush_scope("modifier_definition")
        for mod in self._modifier_instances:
            success_lists.append(
                ("modifier_definition", mod, mod.success_criteria)
            )

        if self.workflow_manager is not None:
            criteria_list.flush_scope("workflow_manager_definition")
            success_lists.append(
                (
                    "workflow_manager_definition",
                    self.workflow_manager,
                    self.workflow_manager.success_criteria,
                )
            )

        for success_scope, obj, success_list in success_lists:
            for criteria, conf in success_list.items():
                if not self.expander.satisfies(
                    conf["when"], variant_set=self.experiment_variants()
                ):
                    continue

                if conf["mode"] == "string":
                    match = (
                        self.expander.expand_var(conf["match"])
                        if conf["match"] is not None
                        else None
                    )
                    anti_match = (
                        self.expander.expand_var(conf["anti_match"])
                        if conf["anti_match"] is not None
                        else None
                    )
                    criteria_list.add_criteria(
                        success_scope,
                        criteria,
                        mode=conf["mode"],
                        match=match,
                        file=conf["file"],
                        anti_match=anti_match,
                        owning_object=obj,
                    )
                elif conf["mode"] == "fom_comparison":
                    criteria_list.add_criteria(
                        success_scope,
                        criteria,
                        conf["mode"],
                        fom_name=conf["fom_name"],
                        fom_context=conf["fom_context"],
                        formula=conf["formula"],
                        owning_object=obj,
                    )

        criteria_list.add_criteria(
            scope="application_definition",
            name="_application_function",
            mode="application_function",
            owning_object=self,
        )

        # Extract file paths for all criteria
        for criteria, _ in criteria_list.all_criteria():
            log_path = self.expander.expand_var(criteria.file)

            # Ensure log path is absolute. If not, prepend the experiment run directory
            if (
                not os.path.isabs(log_path)
                and self.expander.experiment_run_dir not in log_path
            ):
                log_path = os.path.join(
                    self.expander.experiment_run_dir, log_path
                )

            if log_path not in files and os.path.exists(log_path):
                files[log_path] = self._new_file_dict()

            if log_path in files:
                files[log_path]["success_criteria"].append(criteria.name)

        # Could push this into the language features in the future
        fom_sources = [self]
        for mod in self._modifier_instances:
            fom_sources.append(mod)
        if self.workflow_manager is not None:
            fom_sources.append(self.workflow_manager)

        all_contexts = {}
        for source in fom_sources:
            for (
                when_fs,
                source_context_defs,
            ) in source.figure_of_merit_contexts.items():
                if self.expander.satisfies(
                    when_fs, variant_set=self.experiment_variants()
                ):
                    for context, context_def in source_context_defs.items():
                        all_contexts[context] = context_def
            extra_vars = (
                source.modded_variables(self)
                if source.origin_type == "modifier"
                else None
            )
            # figures_of_merit[frozenset(when_list)][frozenset(context_list)][fom_name]
            for when_fs, source_contexts in source.figures_of_merit.items():
                if not self.expander.satisfies(
                    when_fs, variant_set=self.experiment_variants()
                ):
                    continue

                for context_fs, source_foms in source_contexts.items():
                    if (
                        not context_fs
                    ):  # FOMs with no defined context are set to the null context
                        context_fs = frozenset([_NULL_CONTEXT])
                        all_contexts[_NULL_CONTEXT] = {}
                    for context in context_fs:
                        if context not in all_contexts:
                            fom_list = str(list(source_foms.keys()))
                            logger.die(
                                f"Figure(s) of merit {fom_list} registered to context "
                                f"'{context}', which is not found. Check FOM and FOM context "
                                "definitions and 'when' conditions."
                            )

                        def _preset_context_dict(dest_def_dict, context):
                            # Copy context definition for contexts used by a FOM
                            if context not in dest_def_dict:
                                dest_def_dict[context] = {
                                    "definition": {},
                                    "foms": {},
                                }
                                if context != _NULL_CONTEXT:
                                    regex_str = self.expander.expand_var(
                                        all_contexts[context]["regex"]
                                    )
                                    dest_def_dict[context]["definition"] = {
                                        "regex": re.compile(regex_str),
                                        "format": all_contexts[context][
                                            "output_format"
                                        ],
                                    }

                        for fom, source_def in source_foms.items():
                            is_inmem = source_def["fom_map_key"] is not None
                            dest_def_dict = (
                                inmem_fom_defs if is_inmem else file_fom_defs
                            )
                            _preset_context_dict(dest_def_dict, context)
                            if fom in dest_def_dict[context]["foms"]:
                                logger.warn(
                                    f"FOM {fom} already defined in context {context} by "
                                    f"{dest_def_dict[context]['foms'][fom]['origin']}. "
                                    f"Overwriting with new definition from {source.name}"
                                )
                            else:
                                dest_def_dict[context]["foms"][fom] = {}

                            def _expand_var(var, extra_vars=extra_vars):
                                return self.expander.expand_var(
                                    var, extra_vars=extra_vars
                                )

                            def _try_expand_var_or_none(var: str, expander):
                                try:
                                    return expander.expand_var(
                                        var, allow_passthrough=False
                                    )
                                except ramble.expander.RambleSyntaxError:
                                    return None

                            fom_def = {
                                "origin": source.name,
                                "origin_type": source.origin_type,
                                "contexts": set(source_def["contexts"]),
                                "group": (
                                    ""
                                    if is_inmem
                                    else _expand_var(source_def["group_name"])
                                ),
                                "units": _expand_var(source_def["units"]),
                                "regex": (
                                    ""
                                    if is_inmem
                                    else re.compile(
                                        _expand_var(source_def["regex"])
                                    )
                                ),
                                "fom_type": source_def["fom_type"].to_dict(),
                                "fom_map_key": source_def["fom_map_key"],
                                # If expansion works (i.e., it doesn't rely on the matched fom
                                # groups), then cache it here to avoid repeated expansion later.
                                "units_expanded": _try_expand_var_or_none(
                                    source_def["units"], self.expander
                                ),
                                "fom_name_expanded": _try_expand_var_or_none(
                                    fom, self.expander
                                ),
                            }

                            dest_def_dict[context]["foms"][fom] = fom_def

                            if is_inmem:
                                continue
                            log_path = _expand_var(source_def["log_file"])
                            # Ensure log path is absolute. If not, prepend the experiment run dir
                            if (
                                not os.path.isabs(log_path)
                                and self.expander.experiment_run_dir
                                not in log_path
                            ):
                                log_path = os.path.join(
                                    self.expander.experiment_run_dir, log_path
                                )

                            if log_path not in files:
                                files[log_path] = self._new_file_dict()

                            if context not in files[log_path]["contexts"]:
                                files[log_path]["contexts"][context] = []
                            files[log_path]["contexts"][context].append(fom)

                            logger.debug("Log = %s" % log_path)
                            logger.debug("Conf = %s" % fom_def)

        return files, file_fom_defs, inmem_fom_defs

    def add_inmem_fom_value(self, fom_map_key, value):
        """Add value to an in-memory FOM"""
        self._fom_map[fom_map_key] = value

    def read_status(self):
        """Read status from an experiment's status file, if possible.

        Set this experiment's status based on the status file in the experiment
        run directory, if it exists. If it doesn't exist, set its status to
        ExperimentStatus.UNKNOWN
        """
        status_path = os.path.join(
            self.expander.expand_var_name(self.keywords.experiment_run_dir),
            self._status_file_name,
        )

        if os.path.isfile(status_path):
            exp_lock = self.experiment_lock
            with lk.ReadTransaction(exp_lock):
                with open(status_path) as f:
                    status_data = spack.util.spack_json.load(f)
                    self.set_status(
                        ExperimentStatus(
                            status_data[self.keywords.experiment_status]
                        )
                    )
        else:
            self.set_status(ExperimentStatus.UNKNOWN)

    def set_status(self, status=ExperimentStatus.UNKNOWN):
        """Set the status of this experiment"""
        self.variables[self.keywords.experiment_status] = status
        self.set_ramble_status(status)

    def get_status(self):
        """Get the status of this experiment"""
        return self.variables[self.keywords.experiment_status]

    def get_ramble_status(self):
        """Get the RAMBLE_STATUS of this experiment (boolifyied status)"""
        return self.variables[self.keywords.RAMBLE_STATUS]

    def set_ramble_status(self, status):
        """Set the RAMBLE_STATUS (boolifyied status) of this experiment"""

        self.variables[self.keywords.RAMBLE_STATUS] = status
        if status != ExperimentStatus.SUCCESS:
            self.variables[self.keywords.RAMBLE_STATUS] = (
                ExperimentStatus.FAILED
            )

    register_phase(
        "write_status", pipeline="analyze", run_after=["analyze_experiments"]
    )
    register_phase(
        "write_status", pipeline="setup", run_after=["make_experiments"]
    )

    def _write_status(self, workspace, app_inst=None):
        """Phase to write an experiment's ramble_status.json file"""

        status_data = {}
        status_data[self.keywords.experiment_status] = (
            self.expander.expand_var_name(self.keywords.experiment_status)
        )

        exp_dir = self.expander.expand_var_name(
            self.keywords.experiment_run_dir
        )

        status_path = os.path.join(exp_dir, self._status_file_name)

        if os.path.exists(exp_dir):
            exp_lock = self.experiment_lock
            with lk.ReadTransaction(exp_lock):
                with open(status_path, "w+") as f:
                    spack.util.spack_json.dump(status_data, f)

    register_phase("deploy_artifacts", pipeline="pushdeployment")

    def _deploy_artifacts(self, workspace, app_inst=None):
        """Copy all relevant ramble objects to the deployment directory.

        All the ramble objects are grouped under a "ramble" directory, and
        further organized based on the object's original repo namespace.

        Package manager (like Spack) may also create its own repos.

        An example:

        object_repos/
        ├── ramble
        │   ├── builtin
        │   │   ├── modifiers
        │   │   │   ├── gcp-metadata
        │   │   │   │   └── modifier.py
        │   │   ├── package_managers
        │   │   │   ├── spack
        │   │   │   │   └── package_manager.py
        │   │   │   └── spack-lightweight
        │   │   │       └── package_manager.py
        │   │   ├── repo.yaml
        │   └── googleaux
        │       ├── applications
        │       │   ├── base-app
        │       │   │   └── application.py
        │       │   └── derived-app
        │       │       └── application.py
        │       └── repo.yaml
        └── spack
            └── obj_repo
                ├── packages
                │   └── my-package
                │       └── package.py
                └── repo.yaml
        """

        def _copy_files(obj_inst, obj_type, root_path):
            flist = ramble.repository.list_object_files(obj_inst, obj_type)
            for type_dir_name, obj_path, repo_namespace in flist:
                obj_src_dir_path = os.path.dirname(obj_path)
                obj_dir_name = os.path.basename(obj_src_dir_path)
                repo_root = os.path.join(root_path, "ramble", repo_namespace)
                obj_dest_dir = os.path.join(
                    repo_root, type_dir_name, obj_dir_name
                )
                shutil.rmtree(obj_dest_dir, ignore_errors=True)
                shutil.copytree(
                    obj_src_dir_path,
                    obj_dest_dir,
                    ignore=shutil.ignore_patterns("*.pyc", "__pycache__"),
                )
                config_path = os.path.join(
                    repo_root, ramble.repository.unified_config
                )
                if not os.path.exists(config_path):
                    with open(config_path, "w+") as f:
                        f.write("repo:\n")
                        f.write(f"  namespace: {repo_namespace}\n")

        repo_path = workspace.deployment_repos_dir

        repo_lock = lk.Lock(os.path.join(repo_path, ".ramble-obj-repos.lock"))

        with lk.WriteTransaction(repo_lock):
            for obj_type, obj in self._objects():
                _copy_files(obj, obj_type, repo_path)

    register_builtin("env_vars", required=True)

    def env_vars(self):
        command = []
        # ensure license variables are set / modified
        # Process one scope at a time, to ensure
        # highest-precedence scopes are processed last
        config_scopes = ramble.config.scopes()
        shell = ramble.config.get("config:shell")

        action_funcs = ramble.util.env.action_funcs

        license_set = set()
        for scope in config_scopes:
            license_conf = ramble.config.config.get_config(
                "licenses", scope=scope
            )
            if license_conf:
                if self.name in license_conf:
                    app_licenses = license_conf[self.name]
                    if app_licenses:
                        # Append logic to source file which contains the exports
                        shell = ramble.config.get("config:shell")
                        license_set.add(
                            f"{source_str(shell)} {{license_input_dir}}/{constants.LICENSE_INC_NAME}"
                        )

        command.extend(license_set)

        # Process environment variable actions
        for env_var_set in self.environment_variable_sets:
            for action, conf in env_var_set.items():
                (env_cmds, _) = action_funcs[action](
                    conf, self.expander, set(), shell=shell
                )

                for cmd in env_cmds:
                    if cmd:
                        command.append(cmd)

        for mod_inst in self._modifier_instances:
            for env_var_mod in mod_inst.all_env_var_modifications():
                for method in env_var_mod.all_methods:
                    if getattr(env_var_mod, method):
                        conf = {env_var_mod.name: env_var_mod.set}
                        (env_cmds, _) = action_funcs[method](
                            getattr(env_var_mod, method),
                            self.expander,
                            set(),
                            shell=shell,
                        )
                        for cmd in env_cmds:
                            if cmd:
                                command.append(cmd)

        return command

    def evaluate_success(self):
        """Hook for applications to evaluate custom success criteria

        Expected to perform analysis and return either true or false.
        """

        return True

    def _object_templates(self, workspace):
        """Return templates defined from different objects associated with the app_inst"""
        run_dir = self.expander.experiment_run_dir
        replacements = workspace.workspace_paths()
        expander = self.expander
        tpl_ext = constants.TEMPLATE_EXTENSION

        def _expand_path(path):
            return ramble.util.path.substitute_path_variables(
                expander.expand_var(path), local_replacements=replacements
            )

        def _get_template_config(obj, tpl_config, obj_type):
            # Resolve the source path
            src_path_config = _expand_path(tpl_config["src_path"])
            if not src_path_config.endswith(tpl_ext):
                # Enforce the template extension to template's source path.
                src_path_config = src_path_config + tpl_ext
            if not os.path.isabs(src_path_config):
                # Search up the object chain to resolve source path
                found = False
                object_paths = [
                    e[1]
                    for e in ramble.repository.list_object_files(obj, obj_type)
                ]
                searched_paths = []
                for obj_path in object_paths:
                    src_path = os.path.join(
                        os.path.dirname(obj_path), src_path_config
                    )
                    if os.path.isfile(src_path):
                        found = True
                        break
                    searched_paths.append(src_path)
                if not found:
                    raise ApplicationError(
                        f"Object {obj.name} is missing template file {src_path_config}. "
                        f"Searched paths: {searched_paths}"
                    )
            else:
                if not os.path.isfile(src_path_config):
                    raise ApplicationError(
                        f"Template file {src_path_config} does not exist"
                    )
                src_path = src_path_config

            # Resolve the destination path
            dest_path_config = tpl_config["dest_path"]
            if dest_path_config is None:
                dest_path = os.path.basename(src_path)
                if dest_path.endswith(tpl_ext):
                    dest_path = dest_path[: -len(tpl_ext)]
            else:
                dest_path = _expand_path(dest_path_config)
            if not os.path.isabs(dest_path):
                dest_path = os.path.join(run_dir, dest_path)

            return (
                obj,
                {**tpl_config, "src_path": src_path, "dest_path": dest_path},
            )

        for obj_type, obj in self._objects():
            for when_set, tpl in obj.templates.items():
                if not self.expander.satisfies(
                    when_set, variant_set=self.experiment_variants()
                ):
                    continue

                for tpl_conf in tpl.values():
                    yield _get_template_config(
                        obj, tpl_conf, obj_type=obj_type
                    )

    def _render_object_templates(self, extra_vars_origin, workspace):
        for obj, tpl_config in self._object_templates(workspace):
            extra_vars = extra_vars_origin.copy()
            src_path = tpl_config["src_path"]
            content = workspace.read_file_content(src_path)
            extra_vars_dict = tpl_config.get("extra_vars")
            if extra_vars_dict is not None:
                extra_vars.update(extra_vars_dict)
            extra_vars_func_name = tpl_config.get("extra_vars_func_name")
            if extra_vars_func_name is not None:
                extra_vars_func = getattr(obj, extra_vars_func_name)
                extra_vars.update(extra_vars_func())
            rendered = self.expander.expand_var(content, extra_vars=extra_vars)
            out_path = tpl_config["dest_path"]
            perm = tpl_config.get("content_perm", _DEFAULT_CONTENT_PERM)
            with open(out_path, "w+") as f_out:
                f_out.write(rendered)
                f_out.write("\n")
            os.chmod(out_path, perm)

    def _objects(self, exclude_types=None):
        """Return a tuple for each object instance associated with the app_inst.

        The tuple format is (obj_type, obj_inst). This is used to iterate over
        all associated objects with the given app_inst.

        Args:
          exclude_types (list(obj_type) | None): object types to exclude
        """
        if exclude_types is None:
            exclude_types = set()
        else:
            exclude_types = set(exclude_types)

        if ramble.repository.ObjectTypes.applications not in exclude_types:
            yield (ramble.repository.ObjectTypes.applications, self)

        if ramble.repository.ObjectTypes.modifiers not in exclude_types:
            for mod_inst in self._modifier_instances:
                yield (ramble.repository.ObjectTypes.modifiers, mod_inst)

        if ramble.repository.ObjectTypes.package_managers not in exclude_types:
            if self.package_manager is not None:
                yield (
                    ramble.repository.ObjectTypes.package_managers,
                    self.package_manager,
                )

        if (
            ramble.repository.ObjectTypes.workflow_managers
            not in exclude_types
        ):
            if self.workflow_manager is not None:
                yield (
                    ramble.repository.ObjectTypes.workflow_managers,
                    self.workflow_manager,
                )

    def set_required_variables(self):
        """Set required variables from all objects"""
        for _, obj in self._objects():
            logger.debug(f"Setting required variables for {obj.name}")
            self.keywords.update_keys(obj.required_variables)

    def _format_docs_details(self, out):
        if self.workloads:
            out.write("<dt>Workloads:</dt>\n")
            out.write("<dd>\n")
            for when_set in self.workloads:
                for workload in self.workloads[when_set].values():
                    out.write("<details>\n")
                    out.write(f"<summary>{workload.name}</summary>\n")
                    out.write('<dl class="docutils">\n')
                    if workload.executables:
                        out.write("<dt>Executables:</dt>\n")
                        out.write("<dd>\n")
                        out.write(", ".join(workload.executables))
                        out.write("</dd>\n")
                    if workload.inputs:
                        out.write("<dt>Inputs:</dt>\n")
                        out.write("<dd>\n")
                        all_input_defs = {}
                        for input_conf in self.inputs.values():
                            for (
                                input_name,
                                input_def,
                            ) in input_conf.items():
                                if input_name not in all_input_defs:
                                    all_input_defs[input_name] = input_def

                        out.write('<dl class="docutils">\n')
                        for input_name in workload.inputs:
                            out.write(f"<dt>{escape(input_name, True)}</dt>\n")
                            input_def = all_input_defs.get(input_name)
                            if input_def and input_def.get("description"):
                                out.write("<dd>\n")
                                out.write(
                                    escape(input_def["description"], True)
                                )
                                out.write("</dd>\n")
                        out.write("</dl>\n")
                        out.write("</dd>\n")
                    if workload.variables:
                        out.write("<dt>Variables:</dt>\n")
                        out.write("<dd>\n")
                        out.write('<dl class="docutils">\n')
                        for var_when_set in workload.variables:
                            for var in workload.variables[var_when_set]:
                                out.write(f"<dt>{var.name}</dt>\n")
                                if var.description:
                                    out.write("<dd>\n")
                                    out.write(escape(var.description, True))
                                    out.write("</dd>\n")
                        out.write("</dl>\n")
                        out.write("</dd>\n")
                    out.write("</dl>\n")
                    out.write("</details>\n")
            out.write("</dd>\n")
