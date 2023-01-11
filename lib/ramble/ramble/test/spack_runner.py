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


def test_config_concretize_flags(tmpdir, capsys, mutable_config):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')

        ramble.config.config.set('config:spack_flags:concretize', '-f --fresh')
        sr.concretize()
        captured = capsys.readouterr()

        assert "with args: ['concretize', '-f', '--fresh']" in captured.out
    except ramble.spack_runner.RunnerError as e:
        pytest.skip('%s' % e)


def test_default_install_flags(tmpdir, capsys):
    import sys
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


def test_config_install_flags(tmpdir, capsys, mutable_config):
    try:
        env_path = tmpdir.join('spack-env')
        sr = ramble.spack_runner.SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec('zlib')
        sr.concretize()

        ramble.config.config.set('config:spack_flags:install', '--fresh --keep-prefix')
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
