---
name: ramble-spack-integration
description: "Guide for configuring Spack package manager specs, environments, concretization, and resolving software build issues in Ramble."
---

# Ramble Spack Integration Guide

This skill provides guidelines for configuring the Spack package manager within Ramble workspaces, writing Spack specs, managing environments, and resolving concretization conflicts.

---

## 1. Overview of Spack in Ramble

Ramble leverages **Spack** to build, install, and manage software stacks required by experiment workloads. When `variants: package_manager: spack` is set:
- Ramble generates Spack environments (`spack.yaml`) for each configured software environment.
- Software specifications in application definitions or workspace configs are realized via Spack specs.

---

## 2. Inspecting Workspace Software Stack

To view the evaluated software stack and environment mappings for a workspace, run:

```bash
ramble -D <workspace_name> workspace info --software
```

This command outputs:
- Configured software packages and Spack specs.
- Environment names mapped to applications and workloads.
- Concretization status of packages and compilers.

---

## 3. Spack Spec Syntax Quick Reference

Spack specs define package configuration using a flexible syntax:

| Syntax Element | Description | Example |
| :--- | :--- | :--- |
| **Package Name** | Target package | `gromacs`, `openmpi`, `intel-oneapi-mkl` |
| **Version (`@`)** | Version string or constraint | `gromacs@2023.2`, `mpich@4.1:` |
| **Compiler (`%`)** | Compiler spec | `%gcc@12.2.0`, `%oneapi@2023.1.0` |
| **Variants (`+`/`-`/`~`)**| Enable or disable features | `+mpi +cuda -double` |
| **Dependencies (`^`)** | Specify dependency specs | `gromacs ^openmpi@4.1.5 %gcc@12` |
| **Target Architecture (`target=`)** | CPU architecture | `target=zen3`, `target=x86_64_v4` |

---

## 4. Configuring the `software:` Block in `ramble.yaml`

A workspace utilizing Spack must include a `software:` section defining `packages` and `environments`. This would be populated with application defaults during workspace concretization (see Section 6 of this skill). For example:

```yaml
ramble:
  variants:
    package_manager: spack

  software:
    packages:
      gcc12:
        spack_spec: gcc@12.2.0
      openmpi4:
        spack_spec: openmpi@4.1.5 %gcc12 +cuda
      gromacs_pkg:
        spack_spec: gromacs@2023.2 %gcc12 ^openmpi4

    environments:
      gromacs_env:
        packages:
          - openmpi4
          - gromacs_pkg
```

### External Spack Environments
If an existing Spack environment already exists on disk, link it directly without generating a new one:

```yaml
ramble:
  software:
    environments:
      custom_env:
        external_env: /path/to/existing/spack/environment/dir
```

---

## 5. Linking Applications to Spack Environments

By default, every application expects an environment named after it (e.g., `gromacs`).

To map an application to a specific environment, set `env_name` in the application's `variables:` section:

```yaml
ramble:
  applications:
    gromacs:
      variables:
        env_name: gromacs_env
      workloads:
        water_bare:
          experiments:
            test_run: {}
```

### Parameterized Environment Sweeps (A/B Testing)
To compare software stacks (e.g., GCC vs Intel OneAPI, OpenMPI vs MPICH):

```yaml
ramble:
  variables:
    mpi_type: [openmpi, mpich]

  software:
    environments:
      'gromacs-{mpi_type}':
        packages:
          - 'gromacs-{mpi_type}'

  applications:
    gromacs:
      variables:
        env_name: 'gromacs-{mpi_type}'
      matrix:
        - mpi_type
```

---

## 6. Concretization & Troubleshooting

### Automatic Concretization
To populate default software specs for application workloads automatically:

```bash
ramble -D <workspace> workspace concretize -f
```

*Crucial Warning*: If `ramble.yaml` contains empty dictionaries (e.g., `packages: {}`, `environments: {}`), `concretize` will respect them as user overrides and **will not** populate defaults. **Always delete empty dictionary blocks** or run `concretize -f` (force) to overwrite them.

### Resolving Spec Conflicts
1. Check existing defined specs across builtin applications:
   ```bash
   ramble software-definitions --summary
   ```
2. Search for spec conflicts:
   ```bash
   ramble software-definitions --conflicts
   ```
3. Ensure compiler and MPI dependency versions are compatible with the host operating system and GPU drivers.

## 7. Concretization Diagnostic Loop
If `concretize` fails, follow this loop *before* making any manual edits:

1. **Inspect:** Read the log file and the `ramble.yaml` simultaneously.
2. **Compare:** Compare the error message against the keys in `software:packages:`.
3. **Minimal Edit:** Apply a fix that *only* addresses the naming mismatch found.
4. **Re-validate:** Run `concretize`.

**Constraint:** If the fix involves adding a new package definition, you MUST confirm it by running `ramble info -v` again, or by referencing Section 4 of this skill to ensure adherence to external spec definition best practices.
