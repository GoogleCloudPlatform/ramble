---
name: ramble-definition-author
description: "Guide for creating and editing Ramble Object Definitions (Applications, Modifiers, Package Managers, Workflow Managers, Systems, Platforms, Utilities) using Ramble's Python directive language."
---

# Ramble Definition Author Guide

This skill provides step-by-step guidance for authoring and updating Ramble **Object Definitions** in Python.

*Note*: For general codebase contribution rules, running unit tests, pytest fixtures (`make_workspace_from_config`), and style linters (`ramble style`), consult the [.agents/skills/ramble-developer/SKILL.md](../ramble-developer/SKILL.md) skill.

---

## 1. Repository Structure & Complete Object Types

Ramble object definitions live in Python files inside dedicated subdirectories of a Ramble repository (such as `var/ramble/repos/builtin/` or custom user repositories).

Valid object types and their structure are enumerated in `lib/ramble/ramble/repository.py` (`ObjectTypes` Enum):

| Object Type | Repository Directory | Definition File | Base Class / Interface |
| :--- | :--- | :--- | :--- |
| **Applications** | `applications/<name>/` | `application.py` | `ExecutableApplication` or `Application` |
| **Modifiers** | `modifiers/<name>/` | `modifier.py` | `BasicModifier` or `Modifier` |
| **Package Managers** | `package_managers/<name>/` | `package_manager.py` | `PackageManager` |
| **Workflow Managers** | `workflow_managers/<name>/` | `workflow_manager.py` | `WorkflowManager` |
| **Systems** | `systems/<name>/` | `system.py` | `System` |
| **Platforms** | `platforms/<name>/` | `platform.py` | `Platform` |
| **Utilities** | `utilities/<name>/` | `utility.py` | `Utility` |

---

## 2. Base Classes and Inheritance

When creating a new definition, determine whether to build from a fundamental base class or inherit from a concrete definition:

1. **Fundamental Base Classes**:
   Discover available base classes via CLI:
   ```bash
   ramble list --type base_classes
   ```
   *Common examples*: `executable-application` (for CLI-driven apps), `basic-modifier` (for simple modifiers).

2. **Inheritable Concrete Definitions**:
   Discover inheritable definitions via CLI:
   ```bash
   ramble list --type base_<object_type>
   ```
   *Examples*:
   ```bash
   ramble list --type base_applications
   ramble list --type base_modifiers
   ramble list --type base_package_managers
   ramble list --type base_workflow_managers
   ramble list --type base_systems
   ramble list --type base_platforms
   ramble list --type base_utilities
   ```

---

## 3. Declarative Directives

Ramble uses Python class directives defined in `lib/ramble/ramble/language/` (e.g., `application_language.py`, `modifier_language.py`, `shared_language.py`). Directives declare application behavior inside the class body.

### Directive Categories

#### A. Metadata
- `name(...)`: Human-readable name.
- `maintainers(...)`: GitHub handles of maintainers (e.g., `maintainers = ["github_user"]`).
- `tags(...)`: List of tags for categorizing workloads/applications.

#### B. Software Dependencies
- `software_spec(...)`: Define package specs (typically Spack specs).
  ```python
  software_spec('gromacs_spec', spack_name='gromacs', default_spec='gromacs@2023')
  ```
- `define_compiler(...)`: Define compiler specifications.

#### C. Executables & Workloads
- `executable(...)`: Declare named command templates.
  ```python
  executable('run_sim', 'gmx mdrun -s {tpr_file} -deffnm {output_prefix}', implicit=False)
  ```
- `input_file(...)`: Declare data files to download or copy.
- `workload(...)`: Combine executables and input files into named test cases.
  ```python
  workload('bench50', executables=['run_sim'])
  ```

#### D. Parameterization & Variables
- `workload_variable(...)`: Define default variables for workloads.
  ```python
  workload_variable('n_threads', default='1', description='Number of OpenMP threads', workloads=['bench50'])
  ```

#### E. Results & FOMs (Figures of Merit)
- `figure_of_merit(...)`: Extract performance data from log files using regex.
  ```python
  figure_of_merit('Performance', regexp=r'Performance:\s+(?P<fom>[0-9.]+)\s+ns/day', units='ns/day')
  ```
- `success_criteria(...)`: Define rules to check if an experiment succeeded.

#### F. Templating
- `register_template(...)`: Register template files to generate complex input/config files for executables.

---

## 4. Conditional Logic with `with when(...)`

Apply directives conditionally based on variants, package managers, or target environments using the `with when(...)` context manager:

```python
with when('package_manager=spack'):
    software_spec('mpi', spack_name='openmpi')

with when('package_manager=user-managed'):
    workload_variable('mpi_command', default='mpirun', description='User MPI launcher')
```

---

## 5. Software Conflict Checks

Before adding new `software_spec` definitions to an application:
1. Summarize existing software definitions:
   ```bash
   ramble software-definitions --summary
   ```
2. Check for conflicts across definitions:
   ```bash
   ramble software-definitions --conflicts
   ```
3. Use consistent specs and versions across applications to encourage software reuse.

---

## 6. Development Best Practices & Developer Skill Link

1. **Docstrings**: Provide informative docstrings on the class detailing what the application does, with links to source code and documentation.
2. **Developer Guidelines**: For unit testing mock classes (setting `__module__`) and running style checks, refer to [.agents/skills/ramble-developer/SKILL.md](../ramble-developer/SKILL.md).
