# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import sys

import pytest

import ramble.caches
import ramble.main

clean = ramble.main.RambleCommand("clean")

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")


@pytest.fixture()
def mock_calls_for_clean(monkeypatch):

    counts = {}

    class Counter:
        def __init__(self, name):
            self.name = name
            counts[name] = 0

        def __call__(self, *args, **kwargs):
            counts[self.name] += 1

    monkeypatch.setattr(ramble.caches.fetch_cache, "destroy", Counter("downloads"), raising=False)
    monkeypatch.setattr(ramble.caches.misc_cache, "destroy", Counter("caches"))
    monkeypatch.setattr(ramble.cmd.clean, "remove_python_caches", Counter("python_caches"))

    yield counts


all_effects = ["downloads", "caches", "python_caches"]


@pytest.mark.usefixtures("config")
@pytest.mark.parametrize(
    "command_line,effects",
    [
        ("-d", ["downloads"]),
        ("-m", ["caches"]),
        ("-p", ["python_caches"]),
        ("-a", all_effects),
    ],
)
def test_function_calls(command_line, effects, mock_calls_for_clean):

    # Call the command with the supplied command line
    clean(command_line)

    # Assert that we called the expected functions the correct
    # number of times
    for name in all_effects:
        assert mock_calls_for_clean[name] == (1 if name in effects else 0)
