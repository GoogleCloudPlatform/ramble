# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import pytest


import ramble.config
import ramble.spack_runner


def test_env_create(tmpdir):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner()
        sr.create_env(env_path)
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_env_activate(tmpdir):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner()
        sr.create_env(env_path)
        sr.activate()
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_env_deactivate(tmpdir):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner()
        sr.create_env(env_path)
        sr.activate()
        sr.deactivate()
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_env_add(tmpdir):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner()
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')
        sr.deactivate()
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_env_concretize(tmpdir):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner()
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')
        sr.concretize()
        sr.deactivate()

        assert os.path.exists(os.path.join(env_path, 'spack.yaml'))
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_env_install(tmpdir):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner()
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')
        sr.concretize()
        sr.install()
        sr.deactivate()

        assert os.path.exists(os.path.join(env_path, 'spack.yaml'))
        assert os.path.exists(os.path.join(env_path, 'loads'))
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_default_concretize_flags(tmpdir, capsys):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')

        sr.concretize()
        captured = capsys.readouterr()
        assert "with args: ['concretize', '--reuse']" in captured.out
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_config_concretize_flags(tmpdir, capsys):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')

        with ramble.config.override('config:spack_flags', {'concretize': '-f --fresh'}):
            sr.concretize()
            captured = capsys.readouterr()

            assert "with args: ['concretize', '-f', '--fresh']" in captured.out
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_default_install_flags(tmpdir, capsys):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')

        sr.concretize()
        sr.install()
        captured = capsys.readouterr()

        install_flags = ramble.config.config.get('config:spack_flags:install')
        expected_str = "with args: ['install'"
        for flag in install_flags.split():
            expected_str += f", '{flag}'"
        expected_str += "]"

        assert expected_str in captured.out
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_config_install_flags(tmpdir, capsys):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')
        sr.concretize()

        with ramble.config.override('config:spack_flags', {'install': '--fresh --keep-prefix'}):
            sr.install()
            captured = capsys.readouterr()

            install_flags = ramble.config.config.get('config:spack_flags:install')
            expected_str = "with args: ['install'"
            for flag in install_flags.split():
                expected_str += f", '{flag}'"
            expected_str += "]"

            assert expected_str in captured.out
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_env_include(tmpdir, capsys):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')
        good_include_path = '/path/to/include/config.yaml'
        bad_include_path = '/path/to/include/junk.yaml'
        sr.add_include_file(good_include_path)
        sr.add_include_file(bad_include_path)
        sr.concretize()

        with open(os.path.join(env_path, 'spack.yaml'), 'r') as f:
            data = f.read()
            assert good_include_path in data
            assert bad_include_path not in data
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_new_compiler_installs(tmpdir, capsys):

    import os

    compilers_config = """
compilers:
- compiler:
    spec: gcc@12.1.0
    paths:
      cc: /path/to/gcc
      cxx: /path/to/g++
      f77: /path/to/gfortran
      fc: /path/to/gfortran
    flags: {}
    operating_system: 'ramble'
    target: 'x86_64'
    modules: []
    environment: {}
    extra_rpaths: []
"""

    packages_config = """
packages:
  gcc:
    externals:
    - spec: gcc@12.1.0 languages=c,fortran
      prefix: /path/to
    buildable: false
"""

    with tmpdir.as_cwd():
        packages_path = os.path.join(os.getcwd(), 'packages.yaml')
        compilers_path = os.path.join(os.getcwd(), 'compilers.yaml')
        # Write spack_configs
        with open(packages_path, 'w+') as f:
            f.write(packages_config)

        with open(compilers_path, 'w+') as f:
            f.write(compilers_config)

        config_path = os.getcwd()
        with ramble.config.override('config:spack_flags', {'global_args': f'-C {config_path}'}):
            try:
                sr = ramble.spack_runner.SpackRunner(dry_run=True)
                sr.create_env(os.getcwd())
                sr.activate()
                sr.add_include_file(packages_path)
                sr.add_include_file(compilers_path)
                sr.install_compiler('gcc@12.1.0')
                captured = capsys.readouterr()

                assert "gcc@12.1.0 is already an available compiler" in captured.out
            except ramble.spack_runner.RunnerError as e:
                pytest.skip('%s' % e)
