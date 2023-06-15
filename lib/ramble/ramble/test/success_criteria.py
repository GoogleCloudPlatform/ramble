# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.success_criteria


def generate_file(path):
    file_contents = """
Some output
Into a log file
From
An
Experiment
Success string
Or maybe an exit code: 0
    """

    with open(path, 'w+') as f:
        f.write(file_contents)


def test_single_criteria(tmpdir):
    log_path = tmpdir.join('log.out')
    generate_file(log_path)

    new_criteria = ramble.success_criteria.SuccessCriteria('test', 'string',
                                                           r'.*Success string.*',
                                                           log_path)

    with open(log_path, 'r') as f:
        for line in f.readlines():
            if new_criteria.passed(line):
                new_criteria.mark_found()

    assert new_criteria.found


def test_criteria_list(tmpdir):
    log_path = tmpdir.join('log.out')
    generate_file(log_path)

    criteria_list = ramble.success_criteria.ScopedCriteriaList()

    criteria_list.add_criteria('application_definition',
                               'test-success',
                               'string',
                               r'.*Success string.*',
                               log_path)

    criteria_list.add_criteria('experiment',
                               'test-exp',
                               'string',
                               r'.*Experiment.*',
                               log_path)

    criteria_list.add_criteria('workload',
                               'test-wl',
                               'string',
                               r'.*Some output.*',
                               log_path)

    criteria_list.add_criteria('application',
                               'test-app',
                               'string',
                               r'.*exit code.*',
                               log_path)

    criteria_list.add_criteria('workspace',
                               'test-ws',
                               'string',
                               r'.*Into a log file.*',
                               log_path)

    with open(log_path, 'r') as f:
        for line in f.readlines():
            for criteria in criteria_list.all_criteria():
                if criteria.passed(line):
                    criteria.mark_found()

    assert criteria_list.passed()
