# Example Configuration Files:

This directory contains some example configuration files to play with ramble workspaces.

## Instructions:

All of the configuration files in this directory are renamed versions of ramble.yaml.

To create a workspace using any of these files, simply use:

```bash
ramble workspace create <workspace_name> [-c <path_to_config>] [-t <path_to_template_execute>] [-d <path_to_new_workspace_root>]
```

If you want to set up the workspace to simply explore what ramble would do,
(i.e. you don’t want to run any experiment) use:

```bash
ramble -w <workspace_name> workspace setup --dry-run
```

If you actually want to execute the experiments, use:

```bash
ramble -w <workspace_name> workspace setup
```

followed by either:
```bash
ramble -w <workspace_name> on
```
or
```bash
./all_experiments
```
excuted from the root of the workspace.

## Variable syntax:

Within the YAML configuration files, users can define arbitrary variables.
These variables can be referred to within the YAML file, or template files
using python keyword (`{var_name}`) syntax to perform variable expansion. This
syntax allows basic math operations (`+`, `-`, `/`, `*`, and `**`) to evaluate
math expressions using variable definitions.

## Available Configuration Files:

A description of the configuration files available is below:

### [Basic Hostname Config](./basic_hostname_config.yaml)
The basic hostname config is the simplest of the configuration files. This file
uses a pre-existing binary (hostname) to generate experiments.

One should focus on the ramble portion of the yaml file to help understand the
different portions.

For information on what applications are available in ramble, one can use:
```bash
ramble list
```

And for information on what workloads are available within an application, one can use:
```bash
ramble info <app_name>
```

### [Basic Gromacs Config](basic_gromacs_config.yaml)
The basic gromacs configuration file is a good next step in get started using
ramble. It is overly verbose, but this is to show how configurable experiments
can be.

This configuration changes from a pre-existing binary to using spack to build gromacs.

### [Basic Expansion Config](basic_expansion_config.yaml)
The basic expansion configuration file shows some examples of the experiment generation syntax.

It changes from using groamcs to using OpenFoam and WRF.

Additionally, it shows how a configuration file can contain experiments for
multiple applications and / or workloads at the same time.

### [Full Config](full_expansion_config.yaml)

The full expansion configuration file shows a more complete example of
experiment generation. It extends the basic expansion config file by showing two main aspects:

1) How to define environment variables (`env-vars`)
2) How to generate experiments using different binaries for the same application name (`spec_name`)

## Available Template Files:

Any file contained in `$workspace_root/configs` with the extension `.tpl` will
generate a corresponding file for each experiment generated.

Each of these files will generate a variable named
`{script_name_without_tpl_extensions}` which has a value of the path of the
created script within the experiment directory.

This can be used to nest scripts, or refer to one script within another if needed.

A description of the template execution files is available below:

### [slurm_execute_experiment.tpl]

The slurm execute experiment script shows an example of creating an
`execute_experiment` script for use in a slurm cluster.

To use this, place it in the configs directory for your workspace, and change
the `ramble:batch:submit` definition in your ramble.yaml to: `sbatch {slurm_execute_experiment}`.
Then when performing `ramble workspace setup`, the `all_experiments` script will submit to slurm.
