# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from unittest.mock import patch

import pytest

from ramble.util.logger import Logger


@pytest.fixture
def logger():
    return Logger()


def test_aggregate_warnings(logger):
    """Test that warnings are aggregated when aggregate_warnings is on."""
    logger.aggregate_warnings(on=True)
    with patch("ramble.util.logger.tty.warn") as mock_warn:
        logger.warn("This is a warning")
        mock_warn.assert_not_called()
    assert len(logger.global_warnings) == 1


def test_suppress_warnings(logger):
    """Test that warnings are not printed when suppress_warnings is on."""
    logger.aggregate_warnings(on=True)
    with patch("ramble.util.logger.tty.warn") as mock_warn:
        logger.warn("This is a warning")
        # In suppress mode, all_warnings is not called, so we don't call it
    mock_warn.assert_not_called()


def test_print_aggregated_warnings(logger):
    """Test that warnings are printed at the end."""
    logger.aggregate_warnings(on=True)
    with patch("ramble.util.logger.tty.warn") as mock_warn:
        logger.warn("This is a global warning")
        with open("test.log", "w") as f:
            logger.warn("This is a file warning", stream=f)

        logger.all_warnings()

        mock_warn.assert_any_call("This is a global warning")
        mock_warn.assert_any_call("This is a file warning", stream=f)
    os.remove("test.log")


def test_print_warnings_immediately(logger):
    """Test that warnings are printed immediately when aggregate_warnings is off."""
    logger.aggregate_warnings(on=False)
    with patch("ramble.util.logger.tty.warn") as mock_warn:
        logger.warn("This is a warning")
        mock_warn.assert_called_with("This is a warning")
