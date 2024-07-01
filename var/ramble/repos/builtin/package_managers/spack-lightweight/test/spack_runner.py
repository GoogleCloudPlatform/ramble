# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import pytest


import ramble.config
from ramble.pkg_man.builtin.spack_lightweight import (
    SpackRunner,
    RunnerError,
    InvalidExternalEnvironment,
)


def test_env_create(tmpdir):
    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner()
        sr.create_env(env_path)
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_env_activate(tmpdir):
    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner()
        sr.create_env(env_path)
        sr.activate()
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_env_deactivate(tmpdir):
    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner()
        sr.create_env(env_path)
        sr.activate()
        sr.deactivate()
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_env_add(tmpdir):
    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner()
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec("zlib")
        sr.deactivate()
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_env_concretize(tmpdir):
    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner()
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec("zlib")
        sr.concretize()
        sr.deactivate()

        assert os.path.exists(os.path.join(env_path, "spack.yaml"))
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_env_concretize_skips_already_concretized_envs(tmpdir, capsys):
    import time

    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner()
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec("zlib")
        sr.add_spec("intel-oneapi-mpi")

        # Generate an initial env file
        sr.generate_env_file()

        time.sleep(0.5)

        # Create a spack.lock file in the env
        with open(os.path.join(env_path, "spack.lock"), "w+") as f:
            f.write("")

        # Mock regenerating an env file, after the lock was created.
        sr.generate_env_file()

        sr.concretize()

        output = capsys.readouterr()
        assert f"Environment {env_path} will not be regenerated" in output.out
        assert (
            f"Environment {env_path} is already concretized. Skipping concretize..."
            in output.out
        )

        sr.deactivate()

        assert os.path.exists(os.path.join(env_path, "spack.yaml"))
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_env_install(tmpdir, capsys):
    try:
        env_path = str(tmpdir.join("spack-env"))
        # Dry run so we don't actually install zlib
        sr = SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec("zlib")
        sr.generate_env_file()
        sr.concretize()
        sr.install()

        captured = capsys.readouterr()
        assert "spack install" in captured.out

        sr.deactivate()

        env_file = os.path.join(env_path, "spack.yaml")

        assert os.path.exists(env_file)

        with open(env_file, "r") as f:
            assert "zlib" in f.read()

    except RunnerError as e:
        pytest.skip("%s" % e)


def test_env_configs_apply(tmpdir, capsys):
    try:
        env_path = str(tmpdir.join("spack-env"))
        # Dry run so we don't actually install zlib
        sr = SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec("zlib")
        sr.add_config("config:debug:true")
        sr.generate_env_file()

        captured = capsys.readouterr()
        assert (
            "with args: ['config', 'add', 'config:debug:true']" in captured.out
        )

        sr.deactivate()

        env_file = os.path.join(env_path, "spack.yaml")

        assert os.path.exists(env_file)

        with open(env_file, "r") as f:
            data = f.read()
            assert "zlib" in data
            assert "debug: true" in data

    except RunnerError as e:
        pytest.skip("%s" % e)


def test_default_concretize_flags(tmpdir, capsys):
    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec("zlib")

        sr.concretize()
        captured = capsys.readouterr()
        assert "spack concretize" in captured.out
        assert "with args: ['--reuse']" in captured.out
    except RunnerError as e:
        pytest.skip("%s" % e)


@pytest.mark.parametrize(
    "attr,value,expected_str",
    [
        ("flags", "-f --fresh", "'-f', '--fresh'"),
        ("prefix", "time", "would run time"),
    ],
)
def test_config_concretize_attribute(
    tmpdir, capsys, attr, value, expected_str
):
    try:
        env_path = tmpdir.join("spack-env")
        with ramble.config.override(
            "config:spack", {"concretize": {attr: value}}
        ):
            sr = SpackRunner(dry_run=True)
            sr.create_env(env_path)
            sr.activate()
            sr.add_spec("zlib")

            sr.concretize()
            captured = capsys.readouterr()

            assert expected_str in captured.out
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_default_install_flags(tmpdir, capsys):
    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec("zlib")

        sr.concretize()
        sr.install()
        captured = capsys.readouterr()

        install_flags = ramble.config.config.get("config:spack:install:flags")
        expected_str = "with args: ["
        str_args = []
        for flag in install_flags.split():
            str_args.append(f"'{flag}'")
        expected_str += ",".join(str_args) + "]"

        assert "spack install" in captured.out
    except RunnerError as e:
        pytest.skip("%s" % e)


@pytest.mark.parametrize(
    "attr,value,expected_str",
    [
        ("flags", "--fresh --keep-prefix", "'--fresh', '--keep-prefix'"),
        ("prefix", "time", "would run time"),
    ],
)
def test_config_install_attribute(tmpdir, capsys, attr, value, expected_str):
    try:
        env_path = tmpdir.join("spack-env")
        with ramble.config.override(
            "config:spack", {"install": {attr: value}}
        ):
            sr = SpackRunner(dry_run=True)
            sr.create_env(env_path)
            sr.activate()
            sr.add_spec("zlib")
            sr.concretize()

            sr.install()
            captured = capsys.readouterr()

            assert expected_str in captured.out
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_env_include(tmpdir, capsys):
    try:
        env_path = tmpdir.join("spack-env")
        sr = SpackRunner(dry_run=True)
        sr.create_env(env_path)
        sr.activate()
        sr.add_spec("zlib")
        good_include_path = "/path/to/include/config.yaml"
        bad_include_path = "/path/to/include/junk.yaml"
        sr.add_include_file(good_include_path)
        sr.add_include_file(bad_include_path)
        sr.generate_env_file()
        sr.concretize()

        with open(os.path.join(env_path, "spack.yaml"), "r") as f:
            data = f.read()
            assert good_include_path in data
            assert bad_include_path not in data
    except RunnerError as e:
        pytest.skip("%s" % e)


def test_new_compiler_installs(tmpdir, capsys):

    import os

    with tmpdir.as_cwd():
        compilers_config = """
compilers::
- compiler:
    spec: gcc@12.1.0
    paths:
      cc: tmpdir_path/gcc
      cxx: tmpdir_path/g++
      f77: tmpdir_path/gfortran
      fc: tmpdir_path/gfortran
    flags: {}
    operating_system: 'ramble'
    target: 'x86_64'
    modules: []
    environment: {}
    extra_rpaths: []
""".replace(
            "tmpdir_path", os.path.join(os.getcwd(), "bin")
        )

        packages_config = f"""
packages:
  gcc:
    externals:
    - spec: gcc@12.1.0 languages=c,fortran
      prefix: {os.getcwd()}
    buildable: false
"""

        os.mkdir(os.path.join(os.getcwd(), "bin"))

        packages_path = os.path.join(os.getcwd(), "packages.yaml")
        compilers_path = os.path.join(os.getcwd(), "compilers.yaml")
        # Write spack_configs
        with open(packages_path, "w+") as f:
            f.write(packages_config)

        with open(compilers_path, "w+") as f:
            f.write(compilers_config)

        config_path = os.getcwd()
        with ramble.config.override(
            "config:spack", {"global": {"flags": f"-C {config_path}"}}
        ):
            try:
                sr = SpackRunner(dry_run=True)
                sr.create_env(os.getcwd())
                sr.activate()
                sr.add_include_file(packages_path)
                sr.add_include_file(compilers_path)
                sr.install_compiler("gcc@12.1.0")
                captured = capsys.readouterr()

                assert (
                    "gcc@12.1.0 is already an available compiler"
                    in captured.out
                )
            except RunnerError as e:
                pytest.skip("%s" % e)


def test_external_env_copies(tmpdir):
    src_spack_yaml = """
spack:
  specs: [ 'zlib' ]
"""

    src_spack_lock = """
{
  "_meta": {
    "file-type": "spack-lockfile",
    "lockfile-version": 4,
    "specfile-version": 3
  },
  "roots": [
    {
      "hash": "hdw7vo7aap7mqx34ipo3nkzwshctnbnv",
      "spec": "zlib"
    }
  ],
  "concrete_specs": {
    "hdw7vo7aap7mqx34ipo3nkzwshctnbnv": {
      "name": "zlib",
      "version": "1.2.13",
      "arch": {
        "platform": "test_platform",
        "platform_os": "test_os",
        "target": {
          "name": "test_target",
          "vendor": "test_vendor",
          "features": [
            "adx",
          ],
          "generation": 0,
          "parents": [
            "broadwell"
          ]
        }
      },
      "compiler": {
        "name": "gcc",
        "version": "12.2.0"
      },
      "namespace": "builtin",
      "parameters": {
        "build_system": "makefile",
        "optimize": true,
        "pic": true,
        "shared": true,
        "cflags": [],
        "cppflags": [],
        "cxxflags": [],
        "fflags": [],
        "ldflags": [],
        "ldlibs": []
      },
      "package_hash": "y6ahhnjjjsfh5dx2y7sci7fhthq5aolyl5dgwif57qqbtjxwdwbq====",
      "hash": "hdw7vo7aap7mqx34ipo3nkzwshctnbnv"
    }
  }
}
"""

    with tmpdir.as_cwd():
        with open(os.path.join(os.getcwd(), "spack.yaml"), "w+") as f:
            f.write(src_spack_yaml)

        with open(os.path.join(os.getcwd(), "spack.lock"), "w+") as f:
            f.write(src_spack_lock)

        try:
            sr = SpackRunner(dry_run=True)
            generated_env = os.path.join(os.getcwd(), "dest_env")
            sr.create_env(os.path.join(generated_env))
            sr.activate()
            sr.copy_from_external_env(os.getcwd())

            assert os.path.exists(os.path.join(generated_env, "spack.yaml"))

            with open(os.path.join(generated_env, "spack.yaml"), "r") as f:
                assert "zlib" in f.read()
        except RunnerError as e:
            pytest.skip("%s" % e)


def test_configs_apply_to_external_env(tmpdir):
    src_spack_yaml = """
spack:
  specs: [ 'zlib' ]
"""
    with tmpdir.as_cwd():
        with open(os.path.join(os.getcwd(), "spack.yaml"), "w+") as f:
            f.write(src_spack_yaml)

        try:
            sr = SpackRunner(dry_run=True)
            generated_env = os.path.join(os.getcwd(), "dest_env")
            sr.create_env(os.path.join(generated_env))
            sr.activate()
            sr.add_config("config:debug:true")
            sr.copy_from_external_env(os.getcwd())

            assert os.path.exists(os.path.join(generated_env, "spack.yaml"))

            with open(os.path.join(generated_env, "spack.yaml"), "r") as f:
                data = f.read()
                assert "zlib" in data
                assert "config:" in data
                assert "debug: true" in data
        except RunnerError as e:
            pytest.skip("%s" % e)


def test_invalid_external_env_errors(tmpdir):
    with tmpdir.as_cwd():
        try:
            sr = SpackRunner(dry_run=True)
            generated_env = os.path.join(os.getcwd(), "dest_env")
            sr.create_env(os.path.join(generated_env))
            sr.activate()
            with pytest.raises(InvalidExternalEnvironment):
                sr.copy_from_external_env(os.getcwd())
        except RunnerError as e:
            pytest.skip("%s" % e)


@pytest.mark.parametrize(
    "attr,value,expected_str",
    [
        ("flags", "--scope site", "'--scope', 'site'"),
    ],
)
def test_config_compiler_find_attribute(
    tmpdir, capsys, attr, value, expected_str
):

    import os

    compilers_config = """
compilers::
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

    with tmpdir.as_cwd():
        compilers_path = os.path.join(os.getcwd(), "compilers.yaml")
        # Write spack_configs
        with open(compilers_path, "w+") as f:
            f.write(compilers_config)

        config_path = os.getcwd()
        with ramble.config.override(
            "config:spack", {"global": {"flags": f"-C {config_path}"}}
        ):
            with ramble.config.override(
                "config:spack", {"compiler_find": {attr: value}}
            ):
                try:
                    sr = SpackRunner(dry_run=True)
                    sr.create_env(os.getcwd())
                    sr.activate()
                    sr.add_include_file(compilers_path)
                    sr.install_compiler("gcc@12.2.0")
                    captured = capsys.readouterr()

                    assert expected_str in captured.out
                except RunnerError as e:
                    pytest.skip("%s" % e)


def test_env_create_no_view(tmpdir):

    import os

    with tmpdir.as_cwd():
        with ramble.config.override(
            "config:spack", {"env_create": {"flags": "--without-view"}}
        ):
            try:
                sr = SpackRunner()
                sr.create_env(os.getcwd())

                assert not os.path.exists(
                    os.path.join(os.getcwd(), ".spack-env", "view")
                )
            except RunnerError as e:
                pytest.skip("%s" % e)


def test_multiword_args(tmpdir, capsys):
    try:
        env_path = tmpdir.join("spack-env")
        with ramble.config.override(
            "config:spack",
            {"install": {"flags": 'install="-multiword -args"'}},
        ):
            sr = SpackRunner(dry_run=True)
            sr.create_env(env_path)
            sr.activate()
            sr.add_spec("zlib")
            sr.concretize()

            sr.install()
            sr.get_package_path('zlib package_path="-multiword -args"')
            captured = capsys.readouterr()
            print(captured.out)

            assert "install=-multiword -args" in captured.out
            assert "package_path=-multiword -args" in captured.out
    except RunnerError as e:
        pytest.skip("%s" % e)
