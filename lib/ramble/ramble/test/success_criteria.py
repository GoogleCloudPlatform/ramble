# Copyright 2022-2025 The Ramble Authors
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

    with open(path, "w+") as f:
        f.write(file_contents)


def remark_all(crit_list, file_path):
    for c in crit_list:
        c.reset()

    with open(file_path) as f:
        for line in f.readlines():
            for c in crit_list:
                if c.passed(line):
                    c.mark_found()
                if c.anti_matched(line):
                    c.mark_anti_found()


def test_single_criteria(tmpdir):
    log_path = tmpdir.join("log.out")
    generate_file(log_path)

    new_criteria = ramble.success_criteria.SuccessCriteria(
        "test", "string", r".*Success string.*", log_path
    )

    remark_all([new_criteria], log_path)

    assert new_criteria.ok()

    anti_criteria = ramble.success_criteria.SuccessCriteria(
        name="test-anti", mode="string", file=log_path, anti_match=r"Or maybe"
    )

    remark_all([anti_criteria], log_path)

    assert not anti_criteria.ok()


def test_criteria_list(tmpdir):
    log_path = tmpdir.join("log.out")
    generate_file(log_path)

    criteria_list = ramble.success_criteria.ScopedCriteriaList()

    criteria_list.add_criteria(
        "application_definition", "test-success", "string", r".*Success string.*", log_path
    )

    criteria_list.add_criteria("experiment", "test-exp", "string", r".*Experiment.*", log_path)

    criteria_list.add_criteria("workload", "test-wl", "string", r".*Some output.*", log_path)

    criteria_list.add_criteria("application", "test-app", "string", r".*exit code.*", log_path)

    criteria_list.add_criteria("workspace", "test-ws", "string", r".*Into a log file.*", log_path)

    remark_all(list(criteria_list.all_criteria()), log_path)

    assert criteria_list.passed()

    criteria_list.add_criteria(
        scope="application_definition",
        name="test-anti",
        mode="string",
        file=log_path,
        anti_match=r"From",
    )

    remark_all(list(criteria_list.all_criteria()), log_path)

    assert not criteria_list.passed()
