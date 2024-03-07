# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import glob

import pytest

import llnl.util.filesystem as fs

import ramble.application
import ramble.workspace
from ramble.main import RambleCommand, RambleCommandError
from ramble.test.dry_run_helpers import search_files_for_string
import ramble.config
import ramble.filters
import ramble.pipeline

import spack.util.spack_yaml as syaml

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path',
                                     'mutable_mock_apps_repo')

config = RambleCommand('config')
workspace = RambleCommand('workspace')


@pytest.fixture()
def workspace_deactivate():
    yield
    ramble.workspace._active_workspace = None
    os.environ.pop('RAMBLE_WORKSPACE', None)


def add_basic(ws):
    ramble.config.add('applications:basic:workloads:test_wl:experiments:' + '{}',
                      scope=ws.ws_file_config_scope_name())
    ramble.config.add('applications:basic:workloads:test_wl2:experiments:' + '{}',
                      scope=ws.ws_file_config_scope_name())
    ws.write()
    ws._re_read()


def remove_basic(ws):
    ramble.config.set('applications', syaml.syaml_dict(), scope=ws.ws_file_config_scope_name())

    ws.write()
    ws._re_read()


def check_basic(ws):
    found_basic = False
    found_test_wl = False
    found_test_wl2 = False

    for workloads, application_context in ws.all_applications():
        if application_context.context_name == 'basic':
            found_basic = True
        for experiments, workload_context in ws.all_workloads(workloads):
            if workload_context.context_name == 'test_wl':
                found_test_wl = True
            elif workload_context.context_name == 'test_wl2':
                found_test_wl2 = True

    assert found_basic
    assert found_test_wl
    assert found_test_wl2


def check_no_basic(ws):
    found_basic = False
    found_test_wl = False
    found_test_wl2 = False

    for workloads, application_context in ws.all_applications():
        if application_context.context_name == 'basic':
            found_basic = True
        for experiments, workload_context in ws.all_workloads(workloads):
            if workload_context.context_name == 'test_wl':
                found_test_wl = True
            elif workload_context.context_name == 'test_wl2':
                found_test_wl2 = True

    assert not found_basic
    assert not found_test_wl
    assert not found_test_wl2


def check_info_basic(output):
    assert 'basic' in output
    assert 'test_wl' in output
    assert 'test_wl2' in output

    assert 'Application' in output
    assert 'Workload' in output
    assert 'Experiment' in output
    assert 'Software Stack' in output


def check_info_zlib(output):
    assert 'zlib' in output
    assert 'ensure_installed' in output

    assert 'Application' in output
    assert 'Workload' in output
    assert 'Experiment' in output
    assert 'Software Stack' in output
    assert 'Template Package' in output
    assert 'Template Environment' in output


def check_results(ws):
    fn = ws.dump_results(output_formats=['text', 'json', 'yaml'])
    assert os.path.exists(os.path.join(ws.root, fn + '.txt'))
    assert os.path.exists(os.path.join(ws.root, fn + '.json'))
    assert os.path.exists(os.path.join(ws.root, fn + '.yaml'))


def test_workspace_create_links(mutable_mock_workspace_path, tmpdir):
    import pathlib
    expected_links = ['software', 'inputs']
    with tmpdir.as_cwd():
        workspace('create', '-d', 'foo')
        workspace('create', '-d', 'bar', '--inputs-dir', 'foo/inputs',
                  '--software-dir', 'foo/software')

        for expected_link in expected_links:
            assert os.path.exists(os.path.join('bar', expected_link))
            assert os.path.islink(os.path.join('bar', expected_link))
            resolved_path = pathlib.PosixPath(os.path.join('bar', expected_link)).resolve()
            assert str(resolved_path) == os.path.abspath(os.path.join('foo', expected_link))


def test_workspace_activate_fails(mutable_mock_workspace_path):
    workspace('create', 'foo')
    out = workspace('activate', 'foo')
    assert "To set up shell support" in out


def test_workspace_list(mutable_mock_workspace_path):
    workspace('create', 'foo')
    workspace('create', 'bar')
    workspace('create', 'baz')

    out = workspace('list')

    assert 'foo' in out
    assert 'bar' in out
    assert 'baz' in out

    # make sure `ramble workspace list` skips invalid things in
    # var/ramble/workspaces
    mutable_mock_workspace_path.join('.DS_Store').ensure(file=True)
    out = workspace('list')

    assert 'foo' in out
    assert 'bar' in out
    assert 'baz' in out
    assert '.DS_Store' not in out


def test_workspace_info():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
        test_wl2:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
    zlib:
      workloads:
        ensure_installed:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages:
      zlib:
        spack_spec: 'zlib'
    environments:
      zlib:
        packages:
        - zlib
"""

    workspace_name = 'test_info'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    output = workspace('info', '--software', global_args=['-w', workspace_name])

    check_info_basic(output)


def test_workspace_info_prints_all_levels():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      variables:
        application_level: '1'
      workloads:
        test_wl:
          variables:
            workload_level: '1'
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
    zlib:
      workloads:
        ensure_installed:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages:
      zlib:
        spack_spec: 'zlib'
    environments:
      zlib:
        packages:
        - zlib
"""

    config_file = """
config:
  variables:
    conf_level: 1
"""

    workspace_name = 'test_workspace_info_prints_all_levels'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    ramble_config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)
    config_scope_path = os.path.join(ws1.config_dir, 'config.yaml')

    with open(ramble_config_path, 'w+') as f:
        f.write(test_config)

    with open(config_scope_path, 'w+') as f:
        f.write(config_file)

    ws1._re_read()

    output = workspace('info', '--expansions', global_args=['-w', workspace_name])
    assert 'Variables from Config:' in output
    assert 'Variables from Workspace:' in output
    assert 'Variables from Application:' in output
    assert 'Variables from Workload:' in output
    assert 'Variables from Experiment:' in output


def test_workspace_info_with_experiment_chain():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              template: true
              variables:
                n_nodes: '2'
        test_wl2:
          experiments:
            test_experiment:
              chained_experiments:
              - name: basic.test_wl.test_experiment
                order: 'after_root'
                command: '{execute_experiment}'
              variables:
                n_nodes: '2'

  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_workspace_info_with_experiment_chain'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    output = workspace('info', '-vv', global_args=['-w', workspace_name])

    assert "Experiment Chain:" in output
    assert "- basic.test_wl2.test_experiment.chain.0.basic.test_wl.test_experiment" in output


def test_workspace_dir(tmpdir):
    with tmpdir.as_cwd():
        workspace('create', '-d', '.')
        assert os.path.exists(tmpdir + '/configs/ramble.yaml')
        num_templates = 0
        for filename in os.listdir(tmpdir + '/configs'):
            if filename.endswith('.tpl'):
                num_templates += 1

        assert num_templates > 0


def test_workspace_from_template(tmpdir):
    with tmpdir.as_cwd():
        tpl_in = """
cd "{experiment_run_dir}"

cmake -DTEST=1 -h
{spack_setup}

{command}
        """
        tpl_path = os.path.join(tmpdir, 'tmp_test.tpl')
        with open(tpl_path, 'w+') as f:
            f.write(tpl_in)

        assert os.path.exists(tpl_path)

        workspace('create', '-d', '-t', tpl_path, '.')

        assert os.path.exists(tmpdir + '/configs/tmp_test.tpl')
        assert os.path.exists(tmpdir + '/configs/ramble.yaml')
        num_templates = 0
        for filename in os.listdir(tmpdir + '/configs'):
            if filename.endswith('.tpl'):
                num_templates += 1

        assert num_templates > 0


def test_workspace_dirs(tmpdir, mutable_mock_workspace_path):
    with tmpdir.as_cwd():
        # Make a temp directory,
        # Set it up as the workspace_dirs path,
        # make a test workspace there, and
        # verify the workspace was created where
        # it would be expected
        wsdir1 = os.path.join(os.getcwd(), 'ws1')
        os.makedirs(wsdir1)
        with ramble.config.override('config:workspace_dirs', wsdir1):
            workspace('create', 'test1')
            out = workspace('list')
        assert 'test1' in out

        # Now make a second temp directory,
        # follow same process to make another test
        # workspace, and verify that the first
        # test workspace is not found while the
        # second is
        wsdir2 = os.path.join(os.getcwd(), 'ws2')
        os.makedirs(wsdir2)
        with ramble.config.override('config:workspace_dirs', wsdir2):
            workspace('create', 'test2')
            out = workspace('list')
        assert 'test2' in out
        assert 'test1' not in out


def test_remove_workspace():
    workspace('create', 'foo')
    workspace('create', 'bar')

    out = workspace('list')
    assert 'foo' in out
    assert 'bar' in out

    workspace('remove', '-y', 'foo')
    out = workspace('list')
    assert 'foo' not in out
    assert 'bar' in out

    workspace('remove', '-y', 'bar')
    out = workspace('list')
    assert 'foo' not in out
    assert 'bar' not in out


def test_concretize_command():
    ws_name = 'test'
    workspace('create', ws_name)

    with ramble.workspace.read('test') as ws:
        add_basic(ws)
        check_basic(ws)
        workspace('concretize')
        assert ws.is_concretized()


def test_concretize_nothing():
    ws_name = 'test'
    workspace('create', ws_name)
    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        add_basic(ws)
        check_basic(ws)

        ws.concretize()
        assert ws.is_concretized()


def test_setup_command():
    ws_name = 'test'
    workspace('create', ws_name)

    with ramble.workspace.read('test') as ws:
        add_basic(ws)
        check_basic(ws)

        workspace('concretize')
        assert ws.is_concretized()

        workspace('setup')
        assert os.path.exists(ws.root + '/all_experiments')


def test_setup_nothing():
    ws_name = 'test'
    workspace('create', ws_name)
    assert ws_name in workspace('list')
    pipeline_type = ramble.pipeline.pipelines.setup
    pipeline_cls = ramble.pipeline.pipeline_class(pipeline_type)
    filters = ramble.filters.Filters()

    with ramble.workspace.read(ws_name) as ws:
        add_basic(ws)
        check_basic(ws)

        ws.concretize()
        assert ws.is_concretized()

        setup_pipeline = pipeline_cls(ws, filters)
        setup_pipeline.run()
        assert os.path.exists(ws.root + '/all_experiments')


def test_anlyze_command():
    ws_name = 'test'
    workspace('create', ws_name)

    with ramble.workspace.read('test') as ws:
        add_basic(ws)
        check_basic(ws)

        workspace('concretize')
        assert ws.is_concretized()

        workspace('setup')
        assert os.path.exists(ws.root + '/all_experiments')

        workspace('analyze')
        check_results(ws)


def test_analyze_nothing():
    ws_name = 'test'
    workspace('create', ws_name)
    assert ws_name in workspace('list')
    setup_type = ramble.pipeline.pipelines.setup
    setup_cls = ramble.pipeline.pipeline_class(setup_type)
    analyze_type = ramble.pipeline.pipelines.analyze
    analyze_cls = ramble.pipeline.pipeline_class(analyze_type)
    filters = ramble.filters.Filters()

    with ramble.workspace.read(ws_name) as ws:
        add_basic(ws)
        check_basic(ws)

        ws.concretize()
        assert ws.is_concretized()

        setup_pipeline = setup_cls(ws, filters)
        setup_pipeline.run()
        assert os.path.exists(ws.root + '/all_experiments')

        analyze_pipeline = analyze_cls(ws, filters)
        analyze_pipeline.run()
        check_results(ws)


def test_workspace_flag_named():
    ws_name = 'test_ws_flag'
    workspace('create', ws_name)
    assert ws_name in workspace('list')

    flag_args = ['-w', ws_name]

    with ramble.workspace.read(ws_name) as ws:
        add_basic(ws)
        check_basic(ws)

    workspace('concretize', global_args=flag_args)
    with ramble.workspace.read(ws_name) as ws:
        assert ws.is_concretized()

    workspace('setup', global_args=flag_args)
    with ramble.workspace.read(ws_name) as ws:
        assert os.path.exists(ws.root + '/all_experiments')

    workspace('analyze', global_args=flag_args)
    with ramble.workspace.read(ws_name) as ws:
        check_results(ws)

    with ramble.workspace.read(ws_name) as ws:
        remove_basic(ws)
        check_no_basic(ws)


def test_workspace_flag_anon(tmpdir):
    ws_path = str(tmpdir.join('test_ws_dir_flag'))
    workspace('create', '-d', ws_path)
    assert ramble.workspace.is_workspace_dir(ws_path)

    flag_args = ['-D', ws_path]

    with ramble.workspace.Workspace(ws_path) as ws:
        add_basic(ws)
        check_basic(ws)

    workspace('concretize', global_args=flag_args)
    with ramble.workspace.Workspace(ws_path) as ws:
        assert ws.is_concretized()

    workspace('setup', global_args=flag_args)
    with ramble.workspace.Workspace(ws_path) as ws:
        assert os.path.exists(ws.root + '/all_experiments')

    workspace('analyze', global_args=flag_args)
    with ramble.workspace.Workspace(ws_path) as ws:
        check_results(ws)

    with ramble.workspace.Workspace(ws_path) as ws:
        remove_basic(ws)
        check_no_basic(ws)


def test_no_workspace_flag():
    ws_name = 'test_no_ws_flag'
    workspace('create', ws_name)
    assert ws_name in workspace('list')

    flag_args = ['-W']
    with ramble.workspace.read(ws_name) as ws:
        ramble.workspace.activate(ws)
        add_basic(ws)
        check_basic(ws)

        with pytest.raises(RambleCommandError):
            workspace('concretize', global_args=flag_args)
        ramble.workspace.activate(ws)
        workspace('concretize')
        assert ws.is_concretized()

        with pytest.raises(RambleCommandError):
            workspace('setup', global_args=flag_args)
        ramble.workspace.activate(ws)
        workspace('setup')
        assert os.path.exists(ws.root + '/all_experiments')

        with pytest.raises(RambleCommandError):
            workspace('analyze', global_args=flag_args)
        ramble.workspace.activate(ws)
        workspace('analyze')
        check_results(ws)

        ramble.workspace.activate(ws)
        remove_basic(ws)
        check_no_basic(ws)


def test_edit_edits_correct_paths():
    ws = ramble.workspace.create('test')
    ws.write()

    config_file = ramble.workspace.config_file(ws.root)
    default_template_path = ws.template_path('execute_experiment')

    ws_args = ['-w', 'test']
    assert workspace('edit', '-c', '--print-file', global_args=ws_args).strip() == config_file
    assert workspace('edit', '-t', '--print-file', global_args=ws_args).strip() \
        == default_template_path


def test_edit_fails_without_workspace():
    output = workspace('edit', global_args=['-W'], fail_on_error=False)
    assert "ramble workspace edit requires either a " \
           + "command line workspace or an active workspace" \
           in output


def test_edit_override_gets_correct_path():
    ws1 = ramble.workspace.create('test1')
    ws2 = ramble.workspace.create('test2')

    ws1.write()
    ws2.write()

    config_path = ramble.workspace.config_file(ws2.root)

    with ws1:
        ws_args = ['-D', ws2.root]
        output = workspace('edit', '-c', '--print-file', global_args=ws_args).strip()
        assert output == config_path


def test_dryrun_setup():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_dryrun'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    workspace('setup', '--dry-run', global_args=['-w', workspace_name])

    out_files = glob.glob(os.path.join(ws1.log_dir, '**', '*.out'), recursive=True)

    assert search_files_for_string(out_files, 'Would download file:///tmp/test_file.log')
    assert os.path.exists(os.path.join(ws1.root, 'experiments',
                                       'basic', 'test_wl',
                                       'test_experiment',
                                       'execute_experiment'))


def test_matrix_vector_workspace_full():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: [2, 4]
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      variables:
        cells: [5, 10]
      workloads:
        test_wl:
          experiments:
            exp_series_{idx}_{n_nodes}_{cells}_{processes_per_node}:
              variables:
                n_nodes: [1, 2, 4]
                idx: [1, 2, 3, 4, 5, 6]
              matrices:
               - - cells
                 - n_nodes
               - - idx
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    # Should be ppn * ( cells * n_nodes, idx ) = 12
    expected_experiments = set()
    expected_experiments.add('exp_series_1_1_5_2')
    expected_experiments.add('exp_series_1_1_5_4')
    expected_experiments.add('exp_series_4_1_10_2')
    expected_experiments.add('exp_series_4_1_10_4')
    expected_experiments.add('exp_series_2_2_5_2')
    expected_experiments.add('exp_series_2_2_5_4')
    expected_experiments.add('exp_series_5_2_10_2')
    expected_experiments.add('exp_series_5_2_10_4')
    expected_experiments.add('exp_series_3_4_5_2')
    expected_experiments.add('exp_series_3_4_5_4')
    expected_experiments.add('exp_series_6_4_10_2')
    expected_experiments.add('exp_series_6_4_10_4')

    workspace_name = 'test_vec_mat_expansion'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    workspace_flags = ['-w', workspace_name]

    output = workspace('info', global_args=workspace_flags)

    for exp in expected_experiments:
        assert exp in output

    workspace('setup', '--dry-run', global_args=workspace_flags)

    out_files = glob.glob(os.path.join(ws1.log_dir, '**', '*.out'), recursive=True)

    assert search_files_for_string(out_files, 'Would download file:///tmp/test_file.log')

    exp_base = os.path.join(ws1.experiment_dir, 'basic', 'test_wl')
    for exp in expected_experiments:
        assert os.path.exists(os.path.join(exp_base, exp))


def test_invalid_vector_workspace():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: [2, 4]
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      variables:
        cells: [5, 10]
      workloads:
        test_wl:
          experiments:
            exp_series_{idx}_{n_nodes}_{cells}_{processes_per_node}:
              variables:
                n_nodes: [1, 2, 4]
                idx: [1, 2, 3, 4, 5, 6]
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_invalid_vectors'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    workspace_flags = ['-w', workspace_name]

    output = workspace('info', global_args=workspace_flags, fail_on_error=False)
    assert "Length mismatch in vector variables in " + \
        "experiment exp_series_{idx}_{n_nodes}_{cells}_{processes_per_node}" in output

    output = workspace('setup', '--dry-run',
                       global_args=workspace_flags,
                       fail_on_error=False)

    assert "Length mismatch in vector variables in " + \
        "experiment exp_series_{idx}_{n_nodes}_{cells}_{processes_per_node}" in output


def test_invalid_size_matrices_workspace():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            exp_series_{idx}_{n_nodes}_{cells}_{processes_per_node}:
              variables:
                n_nodes: [1, 2, 4]
                idx: [1, 2, 3, 4, 5, 6]
              matrices:
                - - n_nodes
                - - idx
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_invalid_size_matrices'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    workspace_flags = ['-w', workspace_name]

    output = workspace('info', global_args=workspace_flags, fail_on_error=False)
    assert "Matrices defined in experiment" in output
    assert "do not result in the same number of elements." in output

    output = workspace('setup', '--dry-run',
                       global_args=workspace_flags,
                       fail_on_error=False)

    assert "Matrices defined in experiment" in output
    assert "do not result in the same number of elements." in output


def test_undefined_var_matrices_workspace():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            exp_series_{foo}:
              matrices:
                - - foo
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_invalid_input_matrices'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    workspace_flags = ['-w', workspace_name]

    output = workspace('info', global_args=workspace_flags, fail_on_error=False)
    assert "variable or zip foo has not been defined yet" in output

    output = workspace('setup', '--dry-run',
                       global_args=workspace_flags,
                       fail_on_error=False)
    assert "variable or zip foo has not been defined yet" in output


def test_non_vector_var_matrices_workspace():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            exp_series_{foo}:
              variables:
                foo: '1'
              matrices:
                - - foo
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_non_vector_input_matrices'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    workspace_flags = ['-w', workspace_name]

    output = workspace('info', global_args=workspace_flags, fail_on_error=False)
    assert "variable foo does not refer to a vector" in output

    output = workspace('setup', '--dry-run',
                       global_args=workspace_flags,
                       fail_on_error=False)
    assert "variable foo does not refer to a vector" in output


def test_multi_use_vector_var_matrices_workspace():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            exp_series_{foo}:
              variables:
                foo: [1, 2, 3, 4]
              matrices:
                - - foo
                - - foo
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_non_vector_input_matrices'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    workspace_flags = ['-w', workspace_name]

    output = workspace('info', global_args=workspace_flags, fail_on_error=False)
    assert "Variable foo has been used in multiple matrices" in output

    output = workspace('setup', '--dry-run',
                       global_args=workspace_flags,
                       fail_on_error=False)
    assert "Variable foo has been used in multiple matrices" in output


def test_reconcretize_in_configs_dir(tmpdir):
    """
    Test multiple concretizations while the configs dir is the cwd do not fail.
    This catches a bug that existed when lock files were written incorrectly.
    """
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun'
    batch_submit: '{execute_experiment}'
    n_ranks: '1'
    n_nodes: '1'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            exp_series_{foo}:
              variables:
                foo: 1
  spack:
    concretized: false
    packages: {}
    environments: {}
"""

    import py

    def write_config(ws_path, config):
        with ramble.workspace.Workspace(ws_path) as ws:
            config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)
            with open(config_path, 'w+') as f:
                f.write(config)
            ws._re_read()

    ws_path = str(tmpdir.join('test_reconcretize_in_configs_dir'))
    workspace('create', '-d', ws_path)
    assert ramble.workspace.is_workspace_dir(ws_path)

    workspace_flags = ['-D', ws_path]

    config_path = py.path.local(os.path.join(ws_path, 'configs'))
    with config_path.as_cwd():
        write_config(ws_path, test_config)

        workspace('concretize', global_args=workspace_flags)
        with ramble.workspace.Workspace(ws_path) as ws:
            assert ws.is_concretized()

        write_config(ws_path, test_config)

        workspace('concretize', global_args=workspace_flags)
        with ramble.workspace.Workspace(ws_path) as ws:
            assert ws.is_concretized()


def test_workspace_archive():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    test_licenses = """
licenses:
  basic:
    set:
      TEST_LIC: 'value'
"""

    workspace_name = 'test_basic_archive'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)
    lic_path = os.path.join(ws1.config_dir, 'licenses.yaml')

    with open(config_path, 'w+') as f:
        f.write(test_config)

    with open(lic_path, 'w+') as f:
        f.write(test_licenses)

    # Create more templates
    new_templates = []
    for i in range(0, 5):
        new_template = os.path.join(ws1.config_dir, 'test_template.%s' % i)
        new_templates.append(new_template)
        f = open(new_template, 'w+')
        f.close()

    ws1._re_read()

    workspace('setup', '--dry-run', global_args=['-w', workspace_name])
    experiment_dir = os.path.join(ws1.root, 'experiments',
                                  'basic', 'test_wl',
                                  'test_experiment')
    out_files = glob.glob(os.path.join(ws1.log_dir, '**', '*.out'), recursive=True)

    assert search_files_for_string(out_files, 'Would download file:///tmp/test_file.log')
    assert os.path.exists(os.path.join(experiment_dir,
                                       'execute_experiment'))

    # Create files that match archive pattern
    new_files = []
    for i in range(0, 5):
        new_name = 'archive_test.%s' % i
        new_file = os.path.join(experiment_dir, new_name)

        new_files.append(new_file)
        f = open(new_file, 'w+')
        f.close()

    workspace('archive', global_args=['-w', workspace_name])

    assert ws1.latest_archive
    assert os.path.exists(ws1.latest_archive_path)
    assert os.path.exists(os.path.join(ws1.archive_dir, 'archive.latest'))

    for template in new_templates:
        archived_path = template.replace(ws1.root, ws1.latest_archive_path)
        assert os.path.exists(archived_path)

    for file in new_files:
        archived_path = file.replace(ws1.root, ws1.latest_archive_path)
        assert os.path.exists(archived_path)

    assert not os.path.exists(os.path.join(ws1.latest_archive_path, 'shared', 'licenses', 'basic',
                                           ramble.application.ApplicationBase.license_inc_name))


def test_workspace_archive_include_secrets():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    test_licenses = """
licenses:
  basic:
    set:
      TEST_LIC: 'value'
"""

    workspace_name = 'test_basic_archive'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)
    lic_path = os.path.join(ws1.config_dir, 'licenses.yaml')

    with open(config_path, 'w+') as f:
        f.write(test_config)

    with open(lic_path, 'w+') as f:
        f.write(test_licenses)

    # Create more templates
    new_templates = []
    for i in range(0, 5):
        new_template = os.path.join(ws1.config_dir, 'test_template.%s' % i)
        new_templates.append(new_template)
        f = open(new_template, 'w+')
        f.close()

    ws1._re_read()

    workspace('setup', '--dry-run', global_args=['-w', workspace_name])

    workspace('archive', '--include-secrets', global_args=['-w', workspace_name])

    assert os.path.exists(os.path.join(ws1.latest_archive_path, 'shared', 'licenses', 'basic',
                                       ramble.application.ApplicationBase.license_inc_name))


def test_workspace_tar_archive():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_basic_archive'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    # Create more temlates
    new_templates = []
    for i in range(0, 5):
        new_template = os.path.join(ws1.config_dir, 'test_template.%s' % i)
        new_templates.append(new_template)
        f = open(new_template, 'w+')
        f.close()

    ws1._re_read()

    workspace('setup', '--dry-run', global_args=['-w', workspace_name])
    experiment_dir = os.path.join(ws1.root, 'experiments',
                                  'basic', 'test_wl',
                                  'test_experiment')
    out_files = glob.glob(os.path.join(ws1.log_dir, '**', '*.out'), recursive=True)

    assert search_files_for_string(out_files, 'Would download file:///tmp/test_file.log')
    assert os.path.exists(os.path.join(experiment_dir,
                                       'execute_experiment'))

    # Create files that match archive pattern
    new_files = []
    for i in range(0, 5):
        new_name = 'archive_test.%s' % i
        new_file = os.path.join(experiment_dir, new_name)

        new_files.append(new_file)
        f = open(new_file, 'w+')
        f.close()

    workspace('archive', '-t', global_args=['-w', workspace_name])

    assert ws1.latest_archive
    assert os.path.exists(ws1.latest_archive_path)

    for template in new_templates:
        archived_path = template.replace(ws1.root, ws1.latest_archive_path)
        assert os.path.exists(archived_path)

    for file in new_files:
        archived_path = file.replace(ws1.root, ws1.latest_archive_path)
        assert os.path.exists(archived_path)

    assert os.path.exists(ws1.latest_archive_path + '.tar.gz')
    assert os.path.exists(os.path.join(ws1.archive_dir, 'archive.latest.tar.gz'))


def test_workspace_tar_upload_archive():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_basic_archive'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    # Create more templates
    new_templates = []
    for i in range(0, 5):
        new_template = os.path.join(ws1.config_dir, 'test_template.%s' % i)
        new_templates.append(new_template)
        f = open(new_template, 'w+')
        f.close()

    ws1._re_read()

    workspace('setup', '--dry-run', global_args=['-w', workspace_name])
    experiment_dir = os.path.join(ws1.root, 'experiments',
                                  'basic', 'test_wl',
                                  'test_experiment')
    out_files = glob.glob(os.path.join(ws1.log_dir, '**', '*.out'), recursive=True)

    assert search_files_for_string(out_files, 'Would download file:///tmp/test_file.log')
    assert os.path.exists(os.path.join(experiment_dir,
                                       'execute_experiment'))

    # Create files that match archive pattern
    new_files = []
    for i in range(0, 5):
        new_name = 'archive_test.%s' % i
        new_file = os.path.join(experiment_dir, new_name)

        new_files.append(new_file)
        f = open(new_file, 'w+')
        f.close()

    remote_archive_path = os.path.join(ws1.root, 'archive_backup')
    fs.mkdirp(remote_archive_path)

    workspace('archive', '-t', '-u', 'file://' + remote_archive_path,
              global_args=['-w', workspace_name])

    assert ws1.latest_archive
    assert os.path.exists(ws1.latest_archive_path)

    for template in new_templates:
        archived_path = template.replace(ws1.root, ws1.latest_archive_path)
        assert os.path.exists(archived_path)

    for file in new_files:
        archived_path = file.replace(ws1.root, ws1.latest_archive_path)
        assert os.path.exists(archived_path)

    assert os.path.exists(ws1.latest_archive_path + '.tar.gz')

    assert os.path.exists(os.path.join(remote_archive_path, ws1.latest_archive + '.tar.gz'))


def test_workspace_tar_upload_archive_config_url():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_basic_archive'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    # Create more templates
    new_templates = []
    for i in range(0, 5):
        new_template = os.path.join(ws1.config_dir, 'test_template.%s' % i)
        new_templates.append(new_template)
        f = open(new_template, 'w+')
        f.close()

    ws1._re_read()

    workspace('setup', '--dry-run', global_args=['-w', workspace_name])
    experiment_dir = os.path.join(ws1.root, 'experiments',
                                  'basic', 'test_wl',
                                  'test_experiment')
    out_files = glob.glob(os.path.join(ws1.log_dir, '**', '*.out'), recursive=True)

    assert search_files_for_string(out_files, 'Would download file:///tmp/test_file.log')
    assert os.path.exists(os.path.join(experiment_dir,
                                       'execute_experiment'))

    # Create files that match archive pattern
    new_files = []
    for i in range(0, 5):
        new_name = 'archive_test.%s' % i
        new_file = os.path.join(experiment_dir, new_name)

        new_files.append(new_file)
        f = open(new_file, 'w+')
        f.close()

    remote_archive_path = os.path.join(ws1.root, 'archive_backup')
    fs.mkdirp(remote_archive_path)

    config('add', 'config:archive_url:%s/' % remote_archive_path,
           global_args=['-w', workspace_name])

    workspace('archive', '-t', global_args=['-w', workspace_name])

    assert ws1.latest_archive
    assert os.path.exists(ws1.latest_archive_path)

    for template in new_templates:
        archived_path = template.replace(ws1.root, ws1.latest_archive_path)
        assert os.path.exists(archived_path)

    for file in new_files:
        archived_path = file.replace(ws1.root, ws1.latest_archive_path)
        assert os.path.exists(archived_path)

    assert os.path.exists(ws1.latest_archive_path + '.tar.gz')

    assert os.path.exists(os.path.join(remote_archive_path, ws1.latest_archive + '.tar.gz'))


def test_dryrun_noexpvars_setup():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment: {}
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_dryrun'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    workspace('setup', '--dry-run', global_args=['-w', workspace_name])

    out_files = glob.glob(os.path.join(ws1.log_dir, '**', '*.out'), recursive=True)

    assert search_files_for_string(out_files, 'Would download file:///tmp/test_file.log')
    assert os.path.exists(os.path.join(ws1.root, 'experiments',
                                       'basic', 'test_wl',
                                       'test_experiment',
                                       'execute_experiment'))


def test_workspace_include():

    workspace_name = 'test_info'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_file = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)
    inc_file = os.path.join(ws1.config_dir, "test_include.yaml")

    test_include = """
config:
  variables:
    test_var: '1'
"""

    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
        test_wl2:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'
  include:
     - '%s'
  spack:
    concretized: true
    packages: {}
    environments: {}
""" % inc_file

    with open(inc_file, 'w+') as f:
        f.write(test_include)

    with open(config_file, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    output = workspace('info', '--software', global_args=['-w', workspace_name])

    check_info_basic(output)


@pytest.mark.parametrize('tpl_name', [
    'env_path'
])
def test_invalid_template_name_errors(tpl_name, capsys):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment: {}
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_invalid_template_name'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)
    template_path = os.path.join(ws1.config_dir, f'{tpl_name}.tpl')

    with open(config_path, 'w+') as f:
        f.write(test_config)

    with open(template_path, 'w+') as f:
        f.write('{command}')

    with pytest.raises(ramble.workspace.RambleInvalidTemplateNameError):
        ws1._re_read()
        captured = capsys.readouterr()
        err_str = f"Template file {tpl_name}.tpl results in a template name of" + \
                  f"{tpl_name} which is reserved by ramble"
        assert err_str in captured


def test_custom_executables_info():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}'
  applications:
    basic:
      internals:
        custom_executables:
          app_level_cmd:
            template:
            - 'app_level_cmd'
            use_mpi: false
            redirect: '{log_file}'
      workloads:
        test_wl:
          internals:
            custom_executables:
              wl_level_cmd:
                template:
                - 'wl_level_cmd'
                use_mpi: false
                redirect: '{log_file}'
          experiments:
            test_experiment:
              internals:
                custom_executables:
                  exp_level_cmd:
                    template:
                    - 'exp_level_cmd'
                    use_mpi: false
                    redirect: '{log_file}'
                    output_capture: '&>'
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_custom_executables_info'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    output = workspace('info', '-vv', global_args=['-w', workspace_name])

    assert 'app_level_cmd' in output
    assert 'wl_level_cmd' in output
    assert 'exp_level_cmd' in output


def test_custom_executables_order_info():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}'
  applications:
    basic:
      internals:
        custom_executables:
          app_level_cmd:
            template:
            - 'app_level_cmd'
            use_mpi: false
            redirect: '{log_file}'
      workloads:
        test_wl:
          internals:
            custom_executables:
              wl_level_cmd:
                template:
                - 'wl_level_cmd'
                use_mpi: false
                redirect: '{log_file}'
          experiments:
            test_experiment:
              internals:
                custom_executables:
                  exp_level_cmd:
                    template:
                    - 'exp_level_cmd'
                    use_mpi: false
                    redirect: '{log_file}'
                executables:
                - exp_level_cmd
                - wl_level_cmd
                - app_level_cmd
  spack:
    concretized: true
    packages: {}
    environments: {}
"""

    workspace_name = 'test_custom_executables_info'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    output = workspace('info', '-vv', global_args=['-w', workspace_name])

    assert "['exp_level_cmd', 'wl_level_cmd', 'app_level_cmd']" in output
