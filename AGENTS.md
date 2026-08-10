# AI Agent Context for Ramble

**Objective:** This document guides AI agents in assisting with questions about, usage of, and core development tasks related to the Ramble experimentation framework.

## What is Ramble?

Ramble is a multi-platform experimentation framework written in Python, designed to increase exploration productivity and improve reproducibility. It helps automate and manage tasks such as:

*   Software installation (often using Spack)
*   Acquiring input files
*   Configuring experiments (e.g., parameter sweeps, scaling studies)
*   Executing experiments
*   Extracting and analyzing results

Ramble works on Linux, macOS, and many supercomputers.

## Ramble Command Line Interface (CLI)

Ramble is primarily controlled through the `ramble` command. Key aspects of the CLI include:

*   You should always examine the command line interface before executing any `ramble` commands, as arguments might change over time.
*   **Getting Help:** You can get help on any command by using `ramble help` or `ramble help --all` for detailed information on all commands. Help is also available for subcommands (e.g., `ramble workspace --help`).
*   **Discovering Commands and Depth:** To discover the full command hierarchy, start with `ramble help --all`. For any command that shows `...` in its help text (indicating subcommands), run that command with `--help` or `-h` to explore its subcommands (e.g., `ramble workspace --help`).
*   **Key Commands:**
    *   `ramble workspace create`: Set up a new experiment workspace.
    *   `ramble workspace config`: Manage workspace configurations.
    *   `ramble on`: Execute experiments defined in the workspace.
    *   `ramble list`: List available applications, modifiers, etc.
    *   `ramble config`: Manage Ramble's configuration settings.
    *   `ramble repo`: Manage Ramble repositories.
*   **Command Reference:** For local ground-truth documentation on CLI commands, refer to [docs/command_index.rst](docs/command_index.rst).

## Ramble Configuration Files Overview

Ramble uses YAML files for configuration, drawing inspiration from Spack's configuration system. Configurations are applied in scopes, with higher precedence scopes overriding lower ones (e.g., user settings override system defaults, workspace settings override user settings).

*   **Main File:** Each workspace has a primary YAML formatted configuration file located at `$workspace/configs/ramble.yaml`.
*   **Structure:** All content within `ramble.yaml` lives under the top-level `ramble:` dictionary.
*   **Configuration Sections:** Ramble supports numerous configuration sections across workspace and system scopes:
    *   `applications`, `config`, `env_vars`, `software`, `variables`, `variants`, `modifiers`
    *   `repos`, `modifier_repos`, `package_manager_repos`, `workflow_manager_repos`
    *   `base_application_repos`, `base_class_repos`, `base_modifier_repos`, `base_package_manager_repos`, `base_workflow_manager_repos`
    *   `formatted_executables`, `internals`, `licenses`, `mirrors`, `success_criteria`, `tables`, `zips`
*   **Detailed Documentation:** For complete syntax specifications, refer to [docs/workspace_config.rst](docs/workspace_config.rst) and [docs/configuration_files.rst](docs/configuration_files.rst).

## Package Managers Overview

Ramble leverages package managers like **Spack** to manage software stacks required for experiments.

*   **Spack:** Spack is a flexible package manager supporting multiple versions, configurations, platforms, and compilers.
*   **Local Spack Documentation:** Refer to [docs/package_managers.rst](docs/package_managers.rst) for Ramble's Spack integration details.

## Key Ramble Resources

*   **Repository Examples:** Sample configuration files are located in the local [examples/](examples/) directory.
*   **Local Documentation**: Complete Sphinx documentation source files are in [docs/](docs/).

## Available Agent Skills

For specialized workflows, consult the relevant **Agent Skill** under `.agents/skills/`:

| Skill | Description | Location |
| :--- | :--- | :--- |
| **Workspace Wizard** | Interactive setup of experiment workspaces, scaling matrices, and YAML configurations | [.agents/skills/ramble-workspace-wizard/SKILL.md](.agents/skills/ramble-workspace-wizard/SKILL.md) |
| **Definition Author** | Authoring Ramble object definitions (e.g., Applications, Modifiers, Package/Workflow Managers, etc.) | [.agents/skills/ramble-definition-author/SKILL.md](.agents/skills/ramble-definition-author/SKILL.md) |
| **Experiment Runner** | Using Ramble to perform experiments - execution lifecycle (`ramble on`), dry-run validation, and execution debugging | [.agents/skills/ramble-experiment-runner/SKILL.md](.agents/skills/ramble-experiment-runner/SKILL.md) |
| **Results Analyzer** | FOM extraction, speedup & scaling efficiency metrics, and benchmark report generation | [.agents/skills/ramble-results-analyzer/SKILL.md](.agents/skills/ramble-results-analyzer/SKILL.md) |
| **Documentation Author** | Writing Sphinx/reST documentation in `docs/`, building HTML docs, and link checking | [.agents/skills/ramble-documentation-author/SKILL.md](.agents/skills/ramble-documentation-author/SKILL.md) |
| **Spack Integration** | Spack specs (`pkg@ver %compiler`), environment mapping, and concretization troubleshooting | [.agents/skills/ramble-spack-integration/SKILL.md](.agents/skills/ramble-spack-integration/SKILL.md) |
| **Workflow Managers** | Slurm batch directives (`#SBATCH`), partition settings, and launcher overrides | [.agents/skills/ramble-workflow-managers/SKILL.md](.agents/skills/ramble-workflow-managers/SKILL.md) |
| **GCP Cluster Toolkit** | Provisioning Google Cloud HPC/AI clusters (`ghpc`) to host Ramble experiment sweeps | [.agents/skills/gcp-cluster-toolkit/SKILL.md](.agents/skills/gcp-cluster-toolkit/SKILL.md) |
| **Developer Guide** | Guidelines for codebase contributors: pytest fixtures (`make_workspace_from_config`), directive lazy loading, and style checks | [.agents/skills/ramble-developer/SKILL.md](.agents/skills/ramble-developer/SKILL.md) |

## Developer Guidelines & Code Contributions

When modifying the Ramble codebase, writing unit tests, or checking style compliance:
* Consult [.agents/skills/ramble-developer/SKILL.md](.agents/skills/ramble-developer/SKILL.md) for detailed guidelines on:
  * Running tests via `ramble unit-test` and using the `make_workspace_from_config` fixture.
  * Correctly setting `__module__` on mock test classes for directive lazy-loading.
  * Running `ramble style` checks (`isort`, `black`, `flake8`, `mypy`, `ruff`).
