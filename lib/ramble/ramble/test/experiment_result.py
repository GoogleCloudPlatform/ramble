# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Tests on the ExperimentResult class"""

import os
import time

import pytest

from ramble.experiment_result import ExperimentResult
from ramble.util.file_util import get_newest_experiment_file


@pytest.fixture
def experiment_result():
    """Returns a basic experiment result"""

    class AppInst:
        def __init__(self):
            class Expander:
                def __init__(self):
                    self.experiment_run_dir = ""

            self.expander = Expander()
            self.experiment_hash = "test_hash"

    return ExperimentResult(AppInst())


def test_experiment_result_to_dict(mutable_mock_apps_repo):
    basic_app_inst = mutable_mock_apps_repo.get("basic")
    basic_app_inst.set_variables_and_variants(
        {"workload_name": "test_wl", "experiment_status": "placeholder", "test_var": "my_var"},
        {},
        None,
    )
    basic_app_inst.set_status("UNKNOWN")
    exp_res = ExperimentResult(basic_app_inst)
    exp_res.finalize(None)
    res_dict = exp_res.to_dict()

    assert "name" in res_dict
    assert "application_name" in res_dict
    assert res_dict["RAMBLE_STATUS"] == "FAILED"
    assert res_dict["RAMBLE_RAW_VARIABLES"]["experiment_status"] == "UNKNOWN"
    assert "EXPERIMENT_CHAIN" in res_dict
    assert "CONTEXTS" in res_dict
    assert "TAGS" in res_dict
    assert res_dict["N_REPEATS"] == 0
    assert res_dict["RAMBLE_VARIABLES"]["test_var"] == "my_var"
    assert res_dict["RAMBLE_RAW_VARIABLES"]["test_var"] == "my_var"
    assert "RAMBLE_RAW_VARIABLES" in res_dict


def test_experiment_result_read_write_cache(tmpdir, experiment_result):
    """Test that the cache is written and read correctly"""
    experiment_dir = tmpdir.mkdir("experiment")
    experiment_result._app_inst.expander.experiment_run_dir = str(experiment_dir)

    # Test that the cache is written
    experiment_result.write_cache(experiment_result._app_inst)
    cache_file = os.path.join(str(experiment_dir), experiment_result.cache_file_name)
    assert os.path.exists(cache_file)

    # Test that the cache is read correctly
    assert experiment_result.read_cache(None, experiment_result._app_inst)


def test_experiment_result_cache_invalidation_new_file(tmpdir, experiment_result):
    """Test that the cache is invalidated if a file is newer than the cache"""
    experiment_dir = tmpdir.mkdir("experiment")
    experiment_result._app_inst.expander.experiment_run_dir = str(experiment_dir)

    # Write the cache
    experiment_result.write_cache(experiment_result._app_inst)
    time.sleep(0.1)

    # Create a new file
    new_file = os.path.join(str(experiment_dir), "new_file")
    with open(new_file, "w") as f:
        f.write("test")

    # Test that the cache is invalidated
    assert not experiment_result.read_cache(None, experiment_result._app_inst)


def test_experiment_result_cache_invalidation_hash_change(tmpdir, experiment_result):
    """Test that the cache is invalidated if the experiment hash changes"""
    experiment_dir = tmpdir.mkdir("experiment")
    experiment_result._app_inst.expander.experiment_run_dir = str(experiment_dir)

    # Write the cache
    experiment_result.write_cache(experiment_result._app_inst)

    # Change the experiment hash
    experiment_result._app_inst.experiment_hash = "new_hash"

    # Test that the cache is invalidated
    assert not experiment_result.read_cache(None, experiment_result._app_inst)


def test_experiment_result_get_newest_experiment_file(tmpdir):
    """Test that the newest experiment file is found correctly"""
    experiment_dir = tmpdir.mkdir("experiment")
    sub_dir = os.path.join(str(experiment_dir), "sub")
    os.mkdir(sub_dir)

    # Create some files
    file1 = os.path.join(str(experiment_dir), "file1")
    file2 = os.path.join(sub_dir, "file2")
    ramble_file = os.path.join(str(experiment_dir), "ramble_file")

    with open(file1, "w") as f:
        f.write("test")
    time.sleep(0.1)

    with open(file2, "w") as f:
        f.write("test")
    time.sleep(0.1)

    with open(ramble_file, "w") as f:
        f.write("test")

    # Test that the newest file is found correctly
    newest_file, _ = get_newest_experiment_file(str(experiment_dir))
    assert newest_file == file2

    # Test that ramble_file is ignored
    newest_file, _ = get_newest_experiment_file(str(experiment_dir))
    assert "ramble_file" not in newest_file
