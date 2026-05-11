# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.language.language_helpers
from ramble.language.shared_language import edit_file


class MockApp:
    def __init__(self):
        self.name = "mock_app"
        self.origin_type = "application"
        self.executables = {}
        self.custom_edit_functions = {}


@pytest.fixture
def mock_app():
    return MockApp()


def test_edit_file_valid_function(mock_app):
    def my_custom_edit(content):
        return content.replace("a", "b")

    # The directive is usually used as a decorator on the class,
    # but here we call the returned function directly.
    edit_func = edit_file("my_edit", "/path/f", function=my_custom_edit)
    edit_func(mock_app)

    assert "my_edit" in mock_app.custom_edit_functions
    source = mock_app.custom_edit_functions["my_edit"]
    assert "def custom_edit_my_edit_my_custom_edit(content):" in source
    assert "return my_custom_edit(content)" in source

    template = mock_app.executables[frozenset()]["my_edit"].template[0]
    assert "--function custom_edit_my_edit_my_custom_edit" in template


def test_edit_file_invalid_lambda(mock_app):
    with pytest.raises(
        ramble.language.language_helpers.DirectiveError,
        match="Directive 'my_edit' in application 'mock_app' requires a named top-level "
        "function, not a lambda or a method",
    ):
        edit_func = edit_file("my_edit", "/path/f", function=lambda c: c)
        edit_func(mock_app)


def test_edit_file_invalid_method(mock_app):
    class SomeClass:
        def my_method(self, content):
            return content

    with pytest.raises(
        ramble.language.language_helpers.DirectiveError,
        match="Directive 'my_edit' in application 'mock_app' requires a named top-level "
        "function, not a lambda or a method",
    ):
        edit_func = edit_file("my_edit", "/path/f", function=SomeClass().my_method)
        edit_func(mock_app)


def test_edit_file_invalid_signature(mock_app):
    def too_many_args(content, extra):
        return content

    with pytest.raises(
        ramble.language.language_helpers.DirectiveError,
        match="Directive 'my_edit' in application 'mock_app' requires a function that "
        "accepts exactly one argument",
    ):
        edit_func = edit_file("my_edit", "/path/f", function=too_many_args)
        edit_func(mock_app)


def test_edit_file_missing_return(mock_app):
    def no_return(content):
        print(content)

    with pytest.raises(
        ramble.language.language_helpers.DirectiveError,
        match="Directive 'my_edit' in application 'mock_app' requires the function "
        "'no_return' to return a value",
    ):
        edit_func = edit_file("my_edit", "/path/f", function=no_return)
        edit_func(mock_app)


def test_edit_file_collision_avoidance(mock_app):
    def edit(content):
        return content + "1"

    def another_edit(content):
        return content + "2"

    edit_func1 = edit_file("e1", "/path/f1", function=edit)
    edit_func1(mock_app)

    edit_func2 = edit_file("e2", "/path/f2", function=another_edit)
    edit_func2(mock_app)

    assert "e1" in mock_app.custom_edit_functions
    assert "e2" in mock_app.custom_edit_functions

    source1 = mock_app.custom_edit_functions["e1"]
    source2 = mock_app.custom_edit_functions["e2"]

    assert "def custom_edit_e1_edit(content):" in source1
    assert "def custom_edit_e2_another_edit(content):" in source2

    template1 = mock_app.executables[frozenset()]["e1"].template[0]
    template2 = mock_app.executables[frozenset()]["e2"].template[0]

    assert "--function custom_edit_e1_edit" in template1
    assert "--function custom_edit_e2_another_edit" in template2


def test_write_utilities(tmpdir):
    import os

    from ramble.workspace import workspace

    ws_root = str(tmpdir.mkdir("ws"))
    ws = workspace.Workspace(ws_root, True)

    ws.write_utilities()

    shared_util_dir = os.path.join(ws_root, "shared", "utilities")
    assert os.path.exists(shared_util_dir)

    # Base script
    assert os.path.exists(os.path.join(shared_util_dir, "_ramble_file_editor.py"))


def test_edit_file_missing_replace(mock_app):
    with pytest.raises(
        ramble.language.language_helpers.DirectiveError,
        match="requires both 'match' and 'replace' to be specified together",
    ):
        edit_func = edit_file("my_edit", "/path/f", match="foo")
        edit_func(mock_app)


def test_edit_file_missing_match(mock_app):
    with pytest.raises(
        ramble.language.language_helpers.DirectiveError,
        match="requires both 'match' and 'replace' to be specified together",
    ):
        edit_func = edit_file("my_edit", "/path/f", replace="foo")
        edit_func(mock_app)


def test_edit_file_no_actions(mock_app):
    with pytest.raises(
        ramble.language.language_helpers.DirectiveError,
        match="requires at least one action \\(match/replace, append, "
        "prepend, or function\\) to be specified",
    ):
        edit_func = edit_file("my_edit", "/path/f")
        edit_func(mock_app)


def test_edit_file_unretrievable_source(mock_app):
    # Dynamically created function has no source code file
    d = {}
    exec("def dynamic_func(content):\n    return content", d)
    dynamic_func = d["dynamic_func"]

    with pytest.raises(
        ramble.language.language_helpers.DirectiveError,
        match="could not retrieve source for function",
    ):
        edit_func = edit_file("my_edit", "/path/f", function=dynamic_func)
        edit_func(mock_app)


def test_patch_file_directive():
    from ramble.language.shared_language import patch_file

    # Create an app without executables to cover that branch
    class EmptyApp:
        def __init__(self):
            self.name = "empty_app"

    app = EmptyApp()
    patch_func = patch_file("my_patch", "/path/f", "/path/to/patch")
    patch_func(app)

    # Adding a second one to hit the line where executables dict exists
    patch_func2 = patch_file("my_patch2", "/path/f2", "/path/to/patch2")
    patch_func2(app)

    when_set = frozenset()
    assert "my_patch" in app.executables[when_set]
    assert "my_patch2" in app.executables[when_set]
    template = app.executables[when_set]["my_patch"].template[0]
    assert "--mode patch" in template


def test_edit_file_directive_empty_app():
    # Same for edit_file
    class EmptyApp:
        def __init__(self):
            self.name = "empty_app"
            self.custom_edit_functions = {}

    app = EmptyApp()
    edit_func = edit_file("my_edit", "/path/f", match="a", replace="b")
    edit_func(app)
    assert "my_edit" in app.executables[frozenset()]
