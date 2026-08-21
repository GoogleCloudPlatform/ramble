---
name: ramble-experiment-runner
description: "Guide for setting up, executing, monitoring, and debugging experiment runs in Ramble workspaces."
---

# Ramble Experiment Runner Guide

This skill provides procedural guidelines for setting up, executing, monitoring, and troubleshooting experiments in Ramble workspaces.

---

## 1. Standard Experiment Execution Lifecycle

To run a test experiment or benchmark study from start to finish, follow these standard steps:

### Step 1: Create an Empty Workspace
```bash
ramble workspace create -d <workspace_name>
```
*Note*: The `-d` flag creates a workspace directory under the specified path or current working directory.

### Step 2: Configure Experiments using CLI (Preferred)
**Prioritize using the CLI** `ramble workspace manage experiments` command to add and configure experiments in the workspace:

```bash
ramble -D <workspace_name> workspace manage experiments <application_name> --workload-filter <workload_name>
```

#### Direct YAML Editing as Secondary Fallback
For configuration features that do not have dedicated `workspace manage experiments` CLI subcommands (such as adding custom `success_criteria`, advanced `zips:`, complex matrix indirection, or custom `internals:`), edit `$workspace/configs/ramble.yaml` directly.

### Step 3: Verify Configuration & Experiment Expansion
```bash
ramble -D <workspace_name> workspace info
```
Verify that all expected experiment instances (e.g., `<app>.<workload>.<exp_name>`) are generated and matrix variables expand properly.

### Step 4: Generate Workspace Setup & Execution Scripts
```bash
ramble -D <workspace_name> workspace setup
```
This generates required script files, directory trees, and environment configurations for all experiments.

### Step 5: Execute Experiments
```bash
ramble -D <workspace_name> on
```
Launches experiment execution sequentially or via the configured workflow manager.

### Step 6: Analyze Results
```bash
ramble -D <workspace_name> workspace analyze
```
Parses output logs, extracts Figures of Merit (FOMs), and evaluates success criteria.

### Step 7: Inspect Summary Results
```bash
cat <workspace_name>/results.latest.txt
```

---

## 2. Targeting Workspaces without Global Activation

Always use the `-D <workspace_name>` flag with `ramble` to target a specific workspace directory without activating it globally in the shell environment:

```bash
ramble -D ./my-workspace workspace info
ramble -D ./my-workspace workspace setup
ramble -D ./my-workspace on
```

---

## 3. Targeted Experiment Filtering (`--where`)

To run, set up, or analyze specific subsets of experiments within a large workspace matrix, use the `--where` flag:

```bash
# Target experiments based on node counts
ramble -D <workspace> workspace setup --where '{n_nodes} >= 4'

# Target experiments with a specific tag
ramble -D <workspace> on --where '{tag_name}'

# Target specific variable combinations
ramble -D <workspace> workspace analyze --where '{compiler} == "gcc"'
```

---

## 4. Dry-Run Validation

Before performing full execution, run a setup dry-run to validate scripts and templates without building software or executing long jobs:

```bash
ramble -D <workspace> workspace setup --dry-run
```

*Tip*: If software dependencies are not locally installed, ensure the workspace is concretized (`ramble workspace concretize -f`) or mock variable paths (e.g., `app_path: /tmp/mock-bin`) are defined in the workspace `variables:` section.

---

## 5. Troubleshooting Execution Failures

1. **Missing Environments / Concretization Errors**:
   - Run `ramble -D <workspace> workspace concretize -f` to populate default software specs.
   - Check if empty `packages: {}` or `environments: {}` blocks exist in `ramble.yaml`.
2. **Missing Software Specs**:
   - Ensure the application `env_name` variable maps cleanly to a defined environment in the `software:` block.
3. **Execution Failure Logs**:
   - Inspect individual experiment log files located inside `<workspace>/experiments/<app>/<workload>/<exp_name>/` for standard output and error logs (`*.out`, `*.err`).
