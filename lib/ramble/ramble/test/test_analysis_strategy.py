# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Unit tests for analysis strategy pattern"""

import pytest

import ramble.analysis
from ramble.analysis.default import DefaultAnalysisStrategy


class DummyApp:
    pass


def test_get_strategy():
    app = DummyApp()

    strategy = ramble.analysis.get_strategy("default", app)
    assert isinstance(strategy, DefaultAnalysisStrategy)
    assert strategy.app_inst is app

    with pytest.raises(ValueError, match="Unknown analysis strategy: invalid"):
        ramble.analysis.get_strategy("invalid", app)
