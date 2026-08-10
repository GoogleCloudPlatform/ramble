---
name: ramble-developer
description: "Guide for Ramble codebase contributors on writing Python code, running unit tests (pytest), fixture usage (make_workspace_from_config), directive lazy-loading rules, and running style checks (ramble style)."
---

# Ramble Developer Guide

This skill provides guidelines for AI agents contributing code, bug fixes, unit tests, or directives to the Ramble Python codebase.

---

## 1. Python Version Compatibility

- **Supported Versions**: When making Python code changes, consult `bin/ramble` to determine officially supported Python versions.
- **Compatibility Guardrails**: Ensure code works across all supported Python versions. Use feature detection (`hasattr`) or version checks (`sys.version_info`) when necessary to maintain backward compatibility.

---

## 2. Running Unit Tests

Ramble uses `pytest` for unit testing. Tests **must** be run using the `ramble unit-test` wrapper command (not `pytest` directly) to ensure correct environment setup.

### Test Execution Commands
- **Run all tests in parallel**:
  ```bash
  ramble unit-test -n auto
  ```
- **Run tests serially**:
  ```bash
  ramble unit-test
  ```
- **Filter tests by name or pattern**:
  ```bash
  ramble unit-test -k gromacs
  ```
- **Get help on test options**:
  ```bash
  ramble unit-test --help
  ramble unit-test --pytest-help
  ```

---

## 3. Writing Unit Tests & Fixtures

### `make_workspace_from_config` Fixture
When creating and configuring workspaces in unit tests, **always** use the `make_workspace_from_config` fixture defined in `conftest.py`. Avoid creating workspace directories manually via `tmpdir` or writing raw YAML files to disk.

#### Signature
```python
make_workspace_from_config(config_str=None, name=None, activate=False)
```

#### Behavior & Features
- Accepts a raw YAML configuration string (`config_str`) defining the `ramble:` dictionary.
- Automatically isolates workspace files under `mutable_mock_workspace_path` and mocks configuration scopes (`mutable_config`).
- Returns `(ws, ws_name)` where `ws` is the `ramble.workspace.Workspace` object and `ws_name` is the string name of the workspace.
- Pass `activate=True` if the test requires an activated workspace environment (`ramble.workspace.activate(ws)`).

#### Example Unit Test
```python
def test_my_workspace_feature(make_workspace_from_config):
    test_config = """
ramble:
  variants:
    package_manager: spack
    workflow_manager: slurm
  variables:
    n_nodes: 1
    slurm_partition: standard
    mpi_command: 'mpirun -n {n_ranks}'
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test_exp: {}
"""
    ws, ws_name = make_workspace_from_config(test_config, activate=True)
    # Test logic using ws or ws_name
```

---

## 4. Implementing Directives & Mock Test Classes

- **Lazy Directive Processing**: Directives in Ramble are processed lazily based on class module namespace (via `DirectiveMeta` in `lib/ramble/ramble/language/`).
- **Crucial Rule for Mock Classes**: If creating a mock application or modifier class inside a unit test file to test a directive, you **must** explicitly set its `__module__` attribute to a valid Ramble namespace:
  ```python
  class MockApp(ExecutableApplication):
      __module__ = "ramble.app"  # Required for DirectiveMeta to process directives!
  ```
  Without this explicit `__module__` assignment, `DirectiveMeta` will silently skip processing directives for your mock test class.

---

## 5. Running Style Checks

Ramble enforces code formatting and type safety using `isort`, `black`, `flake8`, `mypy`, and `ruff`.

### Commands
- **Check changed files**:
  ```bash
  ramble style
  ```
- **Check all files in repository**:
  ```bash
  ramble style --all
  ```
- **Automatically fix style errors**:
  ```bash
  ramble style --fix
  ramble style --all --fix
  ```
- **Filter specific tools**:
  ```bash
  # Run only isort and black
  ramble style -t isort -t black

  # Skip flake8 and mypy
  ramble style -s flake8 -s mypy
  ```

### Mock Files and Style Checks
When adding mock application or modifier files (e.g., in `var/ramble/repos/builtin.mock/`), ensure these files contain valid Python syntax, appropriate docstrings, and standard copyright headers. `ramble style` runs on the entire repository and will fail if mock files have syntax or formatting errors.
