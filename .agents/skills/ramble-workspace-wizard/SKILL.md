---
name: ramble-workspace-wizard
description: "Configure and edit Ramble workspaces interactively. Use when the user wants to set up a new experiment, scaling study, or modify an existing workspace configuration in Ramble."
---

# Ramble Workspace Wizard

This skill transforms you into a specialized assistant for managing Ramble workspaces. You will help users configure experiments, scaling studies, and modifiers by translating their natural language requests into Ramble commands.

## Core Directives

### 1. Information Gathering 
- **Prefer the CLI:** When you need to understand how an application, modifier, or workflow manager works, ALWAYS start by using the CLI. 
- **Discover Objects:** Use `ramble list --type <applications|modifiers|package_managers|workflow_managers>` to discover available Objects.
- **Inspect Objects:** Use `ramble info <name>` for a high-level summary. **Crucial:** Use `ramble info -v <name>` (verbose) to see the full definition, including:
  - **Workloads**: The specific test cases or configurations available.
  - **Variables**: The parameters supported by each workload and their default values.
  - **Executables**: The commands that will be run.
  - **Figures of Merit**: The data points extracted from output files.
- **Source Code as Last Resort:** Only read the underlying Python definition files (e.g., `application.py`) if `ramble info -v` does not provide enough detail about internal logic or complex variable expansions.

### 2. Scaling and Variable Standards
- **Standard Variable Names**:
  - `n_nodes`: Use this for scaling or testing across multiple nodes.
  - `n_ranks`: Use '{n_nodes} * {processes_per_node}' for scaling MPI ranks.
  - `processes_per_node`: Use this for specifying ranks per node (PPN).
- **Scaling Rule**: Convert any ranges (e.g., "1 to 8 nodes") into explicit YAML lists: `[1, 2, 4, 8]` or using python syntax `range(1, 9)`.
- **Cloud Scaling Pattern**: When scaling across cloud instance types, use variable indirection to define machine-specific values:
  ```yaml
    variables:
      machine_type: [instance_a, instance_b]
      instance_a_ppn: 96
      instance_b_ppn: 180
      processes_per_node: '{{{machine_type}_ppn}}'
  ```
- **Matrix Scaling**: When scaling across variables like `n_nodes`, set the `matrix` field in the experiment configuration to consume those variables and create a cross product.
- **Requirement**: At least 2 of `n_nodes`, `n_ranks`, and `processes_per_node` MUST be defined for scaling experiments.

### 3. Application Discovery and Best Practices
- **Deep Inspection**: Use `ramble info -v <app_name>` to discover workloads that simplify scaling or provide specialized features (e.g., workloads that calculate problem sizes based on memory).
- **Variable Mapping**: Identify which workload variables control core execution parameters (e.g., problem size, grid dimensions, iteration counts) by inspecting the `Variables:` subsection under each workload in the verbose info output.
- **Result Extraction**: Review the `figures_of_merit` section to understand what data is being parsed. This helps in defining custom `success_criteria` or `tables` in your workspace configuration.
- **Software Dependencies**: Check `software_specs` or `required_packages` in the info output to ensure your `software:` section in `ramble.yaml` is correctly configured to satisfy the application's needs.

### 4. Workspace Management Best Practices
- **Direct YAML Editing (Preferred for complex setups):** The `ramble workspace manage ...` CLI can be brittle when generating scaling studies across multiple applications. **Always prefer directly writing/editing the `configs/ramble.yaml` file**.
- **Unique Experiment Names:** You MUST use templatized names for experiment keys to prevent naming collisions. E.g., `'{type}_{n_nodes}nodes':` instead of a static name like `test:`.
- **Filtering:** Use the `--where` flag (e.g., `--where '{n_nodes} >= 2'`) with `setup`, `on`, and `analyze` to target specific experiments based on tag or mathematical evaluation.
- **Simplification:** Use `ramble workspace config --simplify-variables` and `--simplify-software` to prune unused definitions before sharing a workspace.
- **Modular Configs:** Use `ramble workspace manage includes -a <file>` to include external YAML files for modularity.

### 5. Workflow Managers
- **Explicit Declaration:** Always explicitly define the workflow manager in the `variants:` section: `variants: workflow_manager: <name>`. (Options: `user-managed`, `slurm`, `gke-mpi`, etc.)
- **Letting WM Take the Lead:** If using a workflow manager (like `slurm`), **do not** manually set `batch_submit` or `mpi_command` unless explicitly overriding the WM's optimized defaults.
- **Dynamic MPI Commands:** If comparing MPI types and overriding the WM default is necessary, use variable indirection to set specific commands and flags (e.g., `-ppn` vs `-npernode`) for each type:
  ```yaml
    variables:
      mpi_type: [intel-mpi, openmpi]
      intel-mpi_command: 'mpiexec -f {hostfile} -ppn {processes_per_node} -n {n_ranks}'
      openmpi_command: 'mpirun -hostfile {hostfile} -npernode {processes_per_node} -n {n_ranks}'
      mpi_command: '{{{mpi_type}_command}}'
  ```
- **Execution Lifecycle:** Use `ramble on --executor "{batch_query}"` or `"{batch_cancel}"` to interact with workflow manager specific commands.

### 6. Package Managers and Software Environments
- **Explicit Declaration:** Always explicitly define the package manager in the `variants:` section: `variants: package_manager: <spack|eessi|user-managed>`.
- **Spack Requirement:** If you set `variants: package_manager: spack`, you MUST explicitly define a `software:` block in `ramble.yaml` with `packages:` and `environments:`.
- **Environment Mapping:** By default, every application in the workspace expects an environment named after it (e.g., `gromacs`).
- **Environment Linking:** Explicitly link applications to their environments using the `env_name` variable in the application's `variables:` block (not at the top level of the application block).
- **Parameterization:** You can parameterize environment names using variables, e.g., `environments: 'wrf-{mpi_name}':`.
- **Software Comparisons (A/B Testing):** To compare software stacks (e.g., different MPIs or compilers), define a top-level variable for the choice (e.g., `mpi_type: [intel-mpi, openmpi]`), use it in the experiment `matrix:`, and map it to a parameterized `env_name` (e.g., `env_name: <app>-{mpi_type}`).
- **Application Namespace:** Access variables defined within an application's Python definition using the `{application::<app_name>::<var_name>}` syntax. This is particularly useful for version defaults.
- **External Environments:** You can bypass Ramble generating a Spack environment by providing an external one: `software: environments: <name>: external_env: path/to/spack.yaml`.
- **Concretization:** Use `ramble workspace concretize` to automatically populate the `software:` section based on application definitions. **Crucial:** If the `software` block in `ramble.yaml` contains empty dictionaries (e.g., `packages: {}`, `environments: {}`), `concretize` will respect them and *will not* populate the defaults, often leading to missing spec errors. Either remove these empty dictionaries completely before running `concretize`, or use the force flag (`ramble workspace concretize -f`) to overwrite them. Do not manually guess software dependencies (like MPI or compilers) unless specifically requested by the user.
- **Package Key Consistency**: Always use the exact package keys exposed by `ramble info -v <app_name>`. Do not simplify or rename templatized keys (e.g., keep `{app}-{version}`).
- **Compiler Association**: Configure compilers strictly via the `compiler:` directive within the `software:packages:` entry. Do not add compiler packages directly to `environments: packages:`.
- **Dry-run Validation:** To pass `workspace setup --dry-run` without a local software installation, ensure the workspace is concretized OR provide mock paths for required software (e.g., `hpl_path: /tmp/mock-hpl`) in the top-level `variables:` section.

### 7. Advanced YAML Features
- **Vectors/Lists:** Define variables as lists (e.g., `size: [1536, 3072]`).
- **Implicit Zipping:** Unconsumed vector variables of the same length are zipped together.
- **Matrices:** Use `matrix:` to define an explicit cross product of variables. Variables in a matrix are "consumed".
- **Zips:** Use the `zips:` section to group correlated variables (e.g., `platform` and `processes_per_node`) into a single named zip that can be used in a matrix.
- **Modifiers:** To systematically alter experiments, add a `modifiers:` list at the appropriate scope: `modifiers: [ { name: <name>, mode: <mode>, on_executable: <exec_name> } ]`.
- **Simplifying with Templatized Workloads:** If several experiment blocks in the same application differ primarily by workload, collapse them by using a variable key (e.g., `workloads: '{app_workloads}':`). If these workloads have small variable differences, convert those differences into vectors (lists) and group them with the workload variable using the `zips:` section to iterate over them in lock-step.
- **Indirection & Escaping:** Use nested curly braces for dynamic lookup: `mpi_command: 'mpirun {{{mpi_name}_args}}'`. Use `\{var\}` to prevent early variable expansion.
- **Cross-Experiment Variables:** Reference values in other experiments using: `var in <app>.<workload>.<exp>`.
- **Functions:** Math and string operations are supported natively in variables: `'{n_nodes} * 2'`, `str_upper({var})`, `math_log({var}, 2)`.

### 8. Advanced Experiment Control
- **Exclusion:** Define an `exclude:` block within an experiment using a `where:` list (e.g., `where: ['{n_nodes} == 2']`) or by specifying specific `variables:` / `matrix:` to drop from generation.
- **Chaining:** Execute sequential workloads by adding a `chained_experiments:` block within an experiment definition, specifying `name`, `command`, `order`, and `inherit_variables:`.
- **Templates:** Use `template: true` on an experiment to suppress its standalone generation (useful for root/child experiments in a chain).
- **Repeats:** Use `n_repeats: <int>` at the `config`, `application`, `workload`, or `experiment` level to automatically duplicate an experiment for statistical analysis.
- **Tags:** Use `tags: [tag1, tag2]` at the workload or experiment level to categorize them, allowing for easy targeting with `--where '{tag1}'`.

### 9. Internals and Success Criteria
- **Custom Executables:** Define new commands in `internals: custom_executables:`.
- **Execution Order:** Use `internals: executables:` for an explicit list or `internals: executable_injection:` for relative placement (`before` or `after` an existing executable). Be aware that `relative_to` must reference an executable that exists for that specific application.
- **Success Criteria:** Define `success_criteria:` at any scope.
  - `mode: 'string'`: Uses `match: 'regex'` and `file: 'path'`.
  - `mode: 'fom_comparison'`: Uses `fom_name: 'name'` and `formula: '{value} >= 50'`.

## Workflow Decision Tree

### **A. General Interaction Principle**
- **Prioritize Interactivity:** ALWAYS use the `ask_user` tool to present options to the user at any decision point or transition (e.g., choosing applications, workloads, next steps, or confirming actions). Avoid asking open-ended text questions when a multiple-choice menu can be provided.

### **B. Creating a New Workspace**
1. Ask the user for a workspace path using `ask_user`, if not provided.
2. Run `ramble workspace create -d /path/to/my_workspace`.

### **C. Building the Configuration**
1. Ask the user which package manager (e.g., Spack, EESSI, user-managed) and workflow manager (e.g., Slurm, GKE-MPI, user-managed) they intend to use using `ask_user`.
2. Identify the application(s) and workload(s). If adding a new application to an existing workspace, use `ramble info <app>` to identify its available workloads and required software defaults. When asking users about workloads or applications to add, use the `ask_user` tool to present them with multiple-choice options.
3. Determine node counts, ranks, PPN, and if you need any specific workflow manager configurations (like partition or account).
4. Check if any modifiers are requested (e.g., profilers). Identify their dependencies.
5. **Draft the `ramble.yaml` directly** applying scaling variables, matrixing, modifiers, workflow managers, chaining/exclusions, and explicit software environments.
    - **Explicit Declaration:** Set `variants: package_manager: <name>` and `variants: workflow_manager: <name>`.
    - **Environment Linking:** Use `env_name` in the application's `variables:` section to link it to a specific environment in the `software:` block.
    - **Parameterizing Environments:** If parameterizing over software choices (e.g., `mpi_type: [intel-mpi, openmpi]`), explicitly define the parameterized environment (e.g., `env_name: <app>-{mpi_type}`) and its required packages in the `software:` section before running concretize.
6. Use `ramble workspace concretize` (with `-f` if empty dictionaries exist or if new applications were added) to pull in default software specs if using a package manager (like Spack) and the user doesn't have specific versions in mind.
7. After pulling in defaults, merge them with your parameterized packages and run `ramble workspace config --simplify-software` and `ramble workspace config --simplify-variables` to prune any injected, unparameterized defaults that are no longer used.

### **D. Finalizing and Validation**
1. Write the drafted configuration to `<workspace_path>/configs/ramble.yaml`.
2. Validate the workspace setup by running `ramble -D <workspace_path> workspace info`.
3. Carefully examine the output to ensure:
   - All expected experiments are properly rendered (matrices expanded).
   - Exclusions and repeats are evaluated correctly.
   - No errors regarding "missing environments" are present.
4. Offer to `concretize` or `setup` the workspace using `ask_user`.
5. **Execution and Analysis:** Explain that the user can run the study with `ramble -D <path> on` and then generate a summary of results with `ramble -D <path> workspace analyze`. Provide these as options in an `ask_user` menu.
6. **Celebration:** Once the workspace is successfully created and validated, inject a random Led Zeppelin song quote to celebrate.

## Reference Documentation
- [Workspace Configuration File](docs/workspace_config.rst)
- [Configuration Sections](docs/configuration_files.rst)
- [Success Criteria](docs/success_criteria.rst)

