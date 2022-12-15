# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import argparse
import os
import sys

import pytest

from llnl.util.filesystem import copy_tree

import spack.cmd.install
import spack.config
import spack.package
import spack.paths
import spack.store
from spack.main import SpackCommand

install = SpackCommand('install')
spack_test = SpackCommand('test')

pytestmark = pytest.mark.skipif(sys.platform == "win32",
                                reason="does not run on windows")


def test_test_package_not_installed(
        tmpdir, mock_packages, mock_archive, mock_fetch, config,
        install_mockery_mutable_config, mock_test_stage):

    output = spack_test('run', 'libdwarf')

    assert "No installed packages match spec libdwarf" in output


@pytest.mark.parametrize('arguments,expected', [
    (['run'], spack.config.get('config:dirty')),  # default from config file
    (['run', '--clean'], False),
    (['run', '--dirty'], True),
])
def test_test_dirty_flag(arguments, expected):
    parser = argparse.ArgumentParser()
    spack.cmd.test.setup_parser(parser)
    args = parser.parse_args(arguments)
    assert args.dirty == expected


def test_test_dup_alias(
        mock_test_stage, mock_packages, mock_archive, mock_fetch,
        install_mockery_mutable_config, capfd):
    """Ensure re-using an alias fails with suggestion to change."""
    install('libdwarf')

    # Run the tests with the alias once
    out = spack_test('run', '--alias', 'libdwarf', 'libdwarf')
    assert "Spack test libdwarf" in out

    # Try again with the alias but don't let it fail on the error
    with capfd.disabled():
        out = spack_test(
            'run', '--alias', 'libdwarf', 'libdwarf', fail_on_error=False)

    assert "already exists" in out


def test_test_output(mock_test_stage, mock_packages, mock_archive, mock_fetch,
                     install_mockery_mutable_config):
    """Ensure output printed from pkgs is captured by output redirection."""
    install('printing-package')
    spack_test('run', '--alias', 'printpkg', 'printing-package')

    stage_files = os.listdir(mock_test_stage)
    assert len(stage_files) == 1

    # Grab test stage directory contents
    testdir = os.path.join(mock_test_stage, stage_files[0])
    testdir_files = os.listdir(testdir)

    # Grab the output from the test log
    import fnmatch
    testlog = list(filter(lambda x: x.endswith('out.txt') and
                          not fnmatch.fnmatch(x, 'results.*.txt'),
                          testdir_files))

    outfile = os.path.join(testdir, testlog[0])
    with open(outfile, 'r') as f:
        output = f.read()
    assert "BEFORE TEST" in output
    assert "true: expect command status in [" in output
    assert "AFTER TEST" in output
    assert "FAILED" not in output


def test_test_output_on_error(
    mock_packages, mock_archive, mock_fetch, install_mockery_mutable_config,
    capfd, mock_test_stage
):
    install('test-error')
    # capfd interferes with Spack's capturing
    with capfd.disabled():
        out = spack_test('run', 'test-error', fail_on_error=False)

    assert "TestFailure" in out
    assert "Command exited with status 1" in out


def test_test_output_on_failure(
    mock_packages, mock_archive, mock_fetch, install_mockery_mutable_config,
    capfd, mock_test_stage
):
    install('test-fail')
    with capfd.disabled():
        out = spack_test('run', 'test-fail', fail_on_error=False)

    assert "Expected 'not in the output' to match output of `true`" in out
    assert "TestFailure" in out


def test_show_log_on_error(
    mock_packages, mock_archive, mock_fetch,
    install_mockery_mutable_config, capfd, mock_test_stage
):
    """Make sure spack prints location of test log on failure."""
    install('test-error')
    with capfd.disabled():
        out = spack_test('run', 'test-error', fail_on_error=False)

    assert 'See test log' in out
    assert mock_test_stage in out


@pytest.mark.usefixtures(
    'mock_packages', 'mock_archive', 'mock_fetch',
    'install_mockery_mutable_config'
)
@pytest.mark.parametrize('pkg_name,msgs', [
    ('test-error', ['FAILED: Command exited', 'TestFailure']),
    ('test-fail', ['FAILED: Expected', 'TestFailure'])
])
def test_junit_output_with_failures(tmpdir, mock_test_stage, pkg_name, msgs):
    install(pkg_name)
    with tmpdir.as_cwd():
        spack_test('run',
                   '--log-format=junit', '--log-file=test.xml',
                   pkg_name,
                   fail_on_error=False)

    files = tmpdir.listdir()
    filename = tmpdir.join('test.xml')
    assert filename in files

    content = filename.open().read()

    # Count failures and errors correctly
    assert 'tests="1"' in content
    assert 'failures="1"' in content
    assert 'errors="0"' in content

    # We want to have both stdout and stderr
    assert '<system-out>' in content
    for msg in msgs:
        assert msg in content


def test_cdash_output_test_error(
        tmpdir, mock_fetch, install_mockery_mutable_config, mock_packages,
        mock_archive, mock_test_stage, capfd):
    install('test-error')
    with tmpdir.as_cwd():
        spack_test('run',
                   '--log-format=cdash',
                   '--log-file=cdash_reports',
                   'test-error',
                   fail_on_error=False)
        report_dir = tmpdir.join('cdash_reports')
        print(tmpdir.listdir())
        assert report_dir in tmpdir.listdir()
        report_file = report_dir.join('test-error_Test.xml')
        assert report_file in report_dir.listdir()
        content = report_file.open().read()
        assert 'FAILED: Command exited with status 1' in content


def test_cdash_upload_clean_test(
        tmpdir, mock_fetch, install_mockery_mutable_config, mock_packages,
        mock_archive, mock_test_stage):
    install('printing-package')
    with tmpdir.as_cwd():
        spack_test('run',
                   '--log-file=cdash_reports',
                   '--log-format=cdash',
                   'printing-package')
        report_dir = tmpdir.join('cdash_reports')
        assert report_dir in tmpdir.listdir()
        report_file = report_dir.join('printing-package_Test.xml')
        assert report_file in report_dir.listdir()
        content = report_file.open().read()
        assert '</Test>' in content
        assert '<Text>' not in content


def test_test_help_does_not_show_cdash_options(mock_test_stage, capsys):
    """Make sure `spack test --help` does not describe CDash arguments"""
    with pytest.raises(SystemExit):
        spack_test('run', '--help')
        captured = capsys.readouterr()
        assert 'CDash URL' not in captured.out


def test_test_help_cdash(mock_test_stage):
    """Make sure `spack test --help-cdash` describes CDash arguments"""
    out = spack_test('run', '--help-cdash')
    assert 'CDash URL' in out


def test_test_list_all(mock_packages):
    """make sure `spack test list --all` returns all packages with tests"""
    pkgs = spack_test("list", "--all").strip().split()
    assert set(pkgs) == set([
        "printing-package",
        "py-extension1",
        "py-extension2",
        "simple-standalone-test",
        "test-error",
        "test-fail",
        "test-build-callbacks",
        "test-install-callbacks"
    ])


def test_test_list(
    mock_packages, mock_archive, mock_fetch, install_mockery_mutable_config
):
    pkg_with_tests = 'printing-package'
    install(pkg_with_tests)
    output = spack_test("list")
    assert pkg_with_tests in output


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="Not supported on Windows (yet)")
def test_has_test_method_fails(capsys):
    with pytest.raises(SystemExit):
        spack.package.has_test_method('printing-package')

    captured = capsys.readouterr()[1]
    assert 'is not a class' in captured


def test_read_old_results(mock_test_stage):
    """Take test data generated before the switch to full hash everywhere
    and make sure we can still read it in"""
    # Test data was generated with:
    #   spack install printing-package
    #   spack test run --alias printpkg printing-package

    test_data_src = os.path.join(
        spack.paths.test_path, 'data', 'test', 'test_stage')

    # Copy the old test data into the mock stage directory
    copy_tree(test_data_src, mock_test_stage)

    # The find command should print info about the old test, under
    # the alias used at test generation time
    find_output = spack_test('find')
    assert 'printpkg' in find_output

    # The results command should still print the old test results
    results_output = spack_test('results')
    assert 'PASSED' in results_output


def test_test_results_none(mock_packages, mock_test_stage):
    name = 'trivial'
    spec = spack.spec.Spec('trivial-smoke-test').concretized()
    suite = spack.install_test.TestSuite([spec], name)
    suite.ensure_stage()
    spack.install_test.write_test_suite_file(suite)
    results = spack_test('results', name)
    assert 'has no results' in results
    assert 'if it is running' in results


@pytest.mark.parametrize('status,expected', [
    ('FAILED', '1 failed'),
    ('NO-TESTS', '1 no-tests'),
    ('SKIPPED', '1 skipped'),
    ('PASSED', '1 passed'),
])
def test_test_results_status(mock_packages, mock_test_stage, status, expected):
    name = 'trivial'
    spec = spack.spec.Spec('trivial-smoke-test').concretized()
    suite = spack.install_test.TestSuite([spec], name)
    suite.ensure_stage()
    spack.install_test.write_test_suite_file(suite)
    suite.write_test_result(spec, status)

    for opt in ['', '--failed', '--log']:
        args = ['results', name]
        if opt:
            args.insert(1, opt)

        results = spack_test(*args)
        if opt == '--failed' and status != 'FAILED':
            assert status not in results
        else:
            assert status in results
        assert expected in results
