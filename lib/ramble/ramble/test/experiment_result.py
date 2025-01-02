# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Tests on the ExperimentResult class"""

from ramble.experiment_result import ExperimentResult


def test_to_dict(mutable_mock_apps_repo):
    basic_app_inst = mutable_mock_apps_repo.get("basic")
    basic_app_inst.set_variables({"experiment_status": "Unknown", "test_var": "my_var"}, None)
    exp_res = ExperimentResult(basic_app_inst)
    res_dict = exp_res.to_dict()
    assert "name" in res_dict
    assert "application_name" in res_dict
    assert res_dict["RAMBLE_STATUS"] == "Unknown"
    assert res_dict["RAMBLE_RAW_VARIABLES"]["experiment_status"] == "Unknown"
    assert "EXPERIMENT_CHAIN" in res_dict
    assert "CONTEXTS" in res_dict
    assert "TAGS" in res_dict
    assert res_dict["N_REPEATS"] == 0
    assert res_dict["RAMBLE_VARIABLES"]["test_var"] == "my_var"
    assert res_dict["RAMBLE_RAW_VARIABLES"]["test_var"] == "my_var"
    assert "RAMBLE_RAW_VARIABLES" in res_dict
