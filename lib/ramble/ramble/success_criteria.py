# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import re

import llnl.util.tty as tty


class ScopedCriteriaList(object):
    """A scoped list of success criteria

    This object represents a list of success criteria. The criteria are scoped
    based on which portion of a workspace they are defined in.

    Possible scopes are:
     - application_definition
     - application
     - workload
     - experiment

    To see if success was met, all criteria will be checked and are ANDed together.
    """

    _valid_scopes = [
        'application_definition',
        'workspace',
        'application',
        'workload',
        'experiment'
    ]
    _flush_scopes = {
        'experiment': ['experiment'],
        'workload': ['workload', 'experiment'],
        'application': ['application', 'workload', 'experiment'],
        'workspace': ['workspace', 'application', 'workload', 'experiment'],
        'application_definition': ['application_definition']
    }

    def __init__(self):
        self.criteria = {}
        for scope in self._valid_scopes:
            self.criteria[scope] = []

    def validate_scope(self, scope):
        if scope not in self._valid_scopes:
            tty.die('Success scope %s is not valid. Possible scopes are: %s'
                    % (scope, self._valid_scopes))

    def add_criteria(self, scope, name, mode, match, file):
        self.validate_scope(scope)
        exists = self.find_criteria(name)
        if exists:
            tty.die(f'Criteria {name} is not unique.')

        self.criteria[scope].append(SuccessCriteria(name, mode, match, file))

    def flush_scope(self, scope):
        """Remove criteria within a scope, and lower level scopes

        Scope to be purged are defined in self._flush_scopes.
        """
        self.validate_scope(scope)

        for scope in self._flush_scopes[scope]:
            tty.debug(' Flushing scope: %s' % scope)
            tty.debug('    It contained:')
            for crit in self.criteria[scope]:
                tty.debug('      %s' % crit.name)
            del self.criteria[scope]
            self.criteria[scope] = []

    def passed(self):
        succeed = True
        for scope in self._valid_scopes:
            for criteria in self.criteria[scope]:
                succeed = succeed and criteria.found
        return succeed

    def all_criteria(self):
        for scope in self._valid_scopes:
            for criteria in self.criteria[scope]:
                yield criteria

    def find_criteria(self, name):
        for scope in self._valid_scopes:
            for criteria in self.criteria[scope]:
                if criteria.name == name:
                    return criteria
        return None


class SuccessCriteria(object):
    """A single success criteria object

    This object represents a single criteria for success for a Ramble
    experiment.
    """

    _valid_modes = ['string']

    def __init__(self, name, mode, match, file):
        self.name = name
        if mode not in self._valid_modes:
            tty.die(f'{mode} is not valid. Possible modes are: {self._valid_modes}')

        self.mode = mode
        self.match = re.compile(match)
        self.file = file
        self.found = False

    def matches(self, test):
        tty.debug(f'Testing criteria {self.name}')
        if self.mode == 'string':
            match_obj = self.match.match(test)
            if match_obj:
                return True

        return False

    def mark_found(self):
        tty.debug(f'   {self.name} was matched!')
        self.found = True

    def reset_found(self):
        self.found = False
