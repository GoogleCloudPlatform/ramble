# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.language.shared_language as shared_language
from ramble.appkit import ExecutableApplication, maintainers
from ramble.error import DirectiveError
from ramble.language.language_base import DirectiveMeta


def test_when_context_cleanup_on_exception():
    assert len(DirectiveMeta._when_constraints_from_context) == 0

    with pytest.raises(RuntimeError):
        with shared_language.when("package_manager_family=spack"):
            assert len(DirectiveMeta._when_constraints_from_context) == 1
            raise RuntimeError("simulated error inside when block")

    assert len(DirectiveMeta._when_constraints_from_context) == 0

    # Ensure subsequent class with non-when directives (like maintainers) works cleanly
    class CleanApp(ExecutableApplication):
        __module__ = "ramble.app"
        name = "clean-app"
        maintainers("test_maintainer")

    assert len(DirectiveMeta._when_constraints_from_context) == 0


def test_default_args_context_cleanup_on_exception():
    assert len(DirectiveMeta._default_args) == 0

    with pytest.raises(RuntimeError):
        with shared_language.default_args(workload="test_wl"):
            assert len(DirectiveMeta._default_args) == 1
            raise RuntimeError("simulated error inside default_args block")

    assert len(DirectiveMeta._default_args) == 0


def test_directive_meta_reset_staging():
    DirectiveMeta._directives_to_be_executed.append(lambda cls: None)
    DirectiveMeta._when_constraints_from_context.append("some_condition")
    DirectiveMeta._default_args.append({"key": "val"})

    DirectiveMeta._reset_staging()

    assert len(DirectiveMeta._directives_to_be_executed) == 0
    assert len(DirectiveMeta._when_constraints_from_context) == 0
    assert len(DirectiveMeta._default_args) == 0


def test_unsupported_directive_in_when_does_not_leak_context():
    assert len(DirectiveMeta._when_constraints_from_context) == 0

    with pytest.raises(DirectiveError, match=r'cannot be used within a "when" context'):
        with shared_language.when("+some_when_condition"):
            # maintainers does not support when=
            maintainers("invalid_in_when")

    assert len(DirectiveMeta._when_constraints_from_context) == 0

    # Next class definition should not see any leftover when context
    class SubsequentApp(ExecutableApplication):
        __module__ = "ramble.app"
        name = "subsequent-app"
        maintainers("valid_maintainer")

    assert len(DirectiveMeta._when_constraints_from_context) == 0
