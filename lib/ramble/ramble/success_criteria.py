# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import re
import fnmatch

from ramble.util.logger import logger


class ScopedCriteriaList:
    """A scoped list of success criteria

    This object represents a list of success criteria. The criteria are scoped
    based on which portion of a workspace they are defined in.

    Possible scopes are:
     - application_definition
     - application
     - workload
     - experiment

    To see if success was met, all criteria will be checked and are AND-ed together.
    """

    _valid_scopes = [
        "application_definition",
        "modifier_definition",
        "workspace",
        "application",
        "workload",
        "experiment",
    ]
    _flush_scopes = {
        "experiment": ["experiment"],
        "workload": ["workload", "experiment"],
        "application": ["application", "workload", "experiment"],
        "workspace": ["workspace", "application", "workload", "experiment"],
        "modifier_definition": ["modifier_definition"],
        "application_definition": ["application_definition"],
    }

    def __init__(self):
        self.criteria = {}
        for scope in self._valid_scopes:
            self.criteria[scope] = []

    def validate_scope(self, scope):
        if scope not in self._valid_scopes:
            logger.die(
                f"Success scope {scope} is not valid. "
                f"Possible scopes are: {self._valid_scopes}"
            )

    def add_criteria(self, scope, name, mode, *args, **kwargs):
        self.validate_scope(scope)
        exists = self.find_criteria(name)
        if exists:
            logger.die(f"Success criteria {name} is not unique.")

        self.criteria[scope].append(SuccessCriteria(name, mode, *args, **kwargs))

    def flush_scope(self, scope):
        """Remove criteria within a scope, and lower level scopes

        Scope to be purged are defined in self._flush_scopes.
        """
        self.validate_scope(scope)

        for scope in self._flush_scopes[scope]:
            logger.debug(f" Flushing scope: {scope}")
            logger.debug("    It contained:")
            for crit in self.criteria[scope]:
                logger.debug(f"      {crit.name}")
            del self.criteria[scope]
            self.criteria[scope] = []

    def passed(self):
        succeed = True
        for scope in self._valid_scopes:
            for criteria in self.criteria[scope]:
                succeed = succeed and criteria.ok()
        return succeed

    def all_criteria(self):
        for scope in self._valid_scopes:
            yield from self.criteria[scope]

    def find_criteria(self, name):
        for scope in self._valid_scopes:
            for criteria in self.criteria[scope]:
                if criteria.name == name:
                    return criteria
        return None


class SuccessCriteria:
    """A single success criteria object

    This object represents a single criteria for success for a Ramble
    experiment.
    """

    _valid_modes = ["string", "application_function", "fom_comparison"]
    _success_function = "evaluate_success"

    def __init__(
        self,
        name,
        mode,
        match=None,
        file="{log_file}",
        fom_name=None,
        fom_context="null",
        formula=None,
        anti_match=None,
    ):
        self.name = name
        if mode not in self._valid_modes:
            logger.die(f"{mode} is not valid. Possible modes are: {self._valid_modes}")

        self.mode = mode
        self.match = None
        self.anti_match = None
        self.file = None
        self.fom_name = None
        self.fom_context = None
        self.fom_formula = None
        self.found = False
        self.anti_found = False

        if mode == "string":
            if match is None and anti_match is None:
                logger.die(
                    f'Success criteria with mode="{mode}" '
                    'require a "match" or "anti_match" attribute.'
                )
            if anti_match is not None and match is not None:
                logger.die(
                    f'Success criteria {name} with mode="{mode}" '
                    'require exactly one of "anti_match" and "match" to be set.'
                )
            if match is not None:
                self.match = re.compile(match)
            else:
                self.anti_match = re.compile(anti_match)
            self.file = file

        elif mode == "fom_comparison":
            if formula is None or fom_name is None:
                logger.die(
                    f'Success criteria with mode="{mode}" '
                    'require a "fom_name" and "formula" attribute.'
                )
            self.formula = formula
            self.fom_name = fom_name
            self.fom_context = fom_context

    def passed(self, test=None, app_inst=None, fom_values=None):
        logger.debug(f"Testing criteria {self.name} mode = {self.mode}")
        if self.mode == "string":
            if self.match is not None:
                match_obj = self.match.match(test)
                if match_obj:
                    return True
        elif self.mode == "application_function":
            if hasattr(app_inst, self._success_function):
                func = getattr(app_inst, self._success_function)
                return func()
        elif self.mode == "fom_comparison":
            if fom_values is None:
                logger.die(
                    f'Success criteria of mode="{self.mode}" requires '
                    'defined fom_values attribute in "passed" function.'
                )

            if app_inst is None:
                logger.die(
                    f'Success criteria of mode="{self.mode}" requires '
                    'defined app_inst attribute in "passed" function.'
                )

            comparison_tested = False
            result = True

            contexts = fnmatch.filter(
                fom_values.keys(), app_inst.expander.expand_var(self.fom_context)
            )
            # If fom context doesn't exist, fail the comparison
            if not contexts:
                logger.debug(
                    f'When checking success criteria "{self.name}" FOM '
                    f'context "{self.fom_context}" matches no contexts.'
                )
                return False

            for context in contexts:
                fom_names = fnmatch.filter(
                    fom_values[context].keys(), app_inst.expander.expand_var(self.fom_name)
                )

                for fom_name in fom_names:
                    comparison_vars = {
                        "value": fom_values[context][fom_name]["value"],
                    }

                    comparison_tested = True
                    result = app_inst.expander.evaluate_predicate(
                        self.formula, extra_vars=comparison_vars
                    )

            # If fom doesn't match any fom names, fail the comparison
            if not comparison_tested:
                logger.debug(
                    f'When checking success criteria "{self.name}" FOM '
                    f'"{self.fom_name}" did not match any FOMs.'
                )
                return False
            return result

        return False

    def anti_matched(self, test=None):
        logger.debug(f"Testing anti-criterion {self.name} mode = {self.mode}")
        if self.mode == "string":
            if self.anti_match is not None:
                anti_match_obj = self.anti_match.match(test)
                if anti_match_obj:
                    return True
        return False

    def mark_found(self):
        logger.debug(f"   {self.name} was matched!")
        self.found = True

    def mark_anti_found(self):
        logger.debug(f"   {self.name} was anti-matched!")
        self.anti_found = True

    def reset(self):
        self.found = False
        self.anti_found = False

    def ok(self):
        if self.anti_match is not None:
            return not self.anti_found
        return self.found
