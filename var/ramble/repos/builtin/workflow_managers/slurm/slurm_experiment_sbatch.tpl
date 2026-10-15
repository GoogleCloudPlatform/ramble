#!/bin/bash
{workflow_pragmas}

{workflow_banner}

cd {experiment_run_dir}

{workflow_hostfile_cmd}

. "{execute_experiment}"
