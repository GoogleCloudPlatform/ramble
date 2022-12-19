# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import pytest


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
