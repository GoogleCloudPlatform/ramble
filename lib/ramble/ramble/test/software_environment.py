# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
import ramble.software_environments
import ramble.renderer
import ramble.expander
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path',
                                     'mutable_mock_apps_repo',
                                     )

workspace  = RambleCommand('workspace')


def test_basic_software_environment(request, mutable_mock_workspace_path):
    ws_name = request.node.name
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic'] = {
            'spack_spec': 'basic@1.1'
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': ['basic']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'basic' in software_environments._environment_templates
        assert 'basic' in software_environments._package_templates

        variables = {}
        env_expander = ramble.expander.Expander(variables, None)

        rendered_env = software_environments.render_environment('basic', env_expander)
        assert rendered_env.name == 'basic'
        pkg_found = False
        for pkg in rendered_env._packages:
            if pkg.name == 'basic':
                pkg_found = True
        assert pkg_found


def test_software_environments_no_packages(request, mutable_mock_workspace_path):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['environments'] = {
            'basic-{env_test}': {
                'packages': ['']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'basic-{env_test}' in software_environments._environment_templates

        variables = {
            'env_test': 'environment',
        }
        env_expander = ramble.expander.Expander(variables, None)

        rendered_env = software_environments.render_environment('basic-environment', env_expander)
        assert rendered_env.name == 'basic-environment'


def test_software_environments_no_rendered_packages(request, mutable_mock_workspace_path):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['environments'] = {
            'basic-{env_test}': {
                'packages': ['{var_pkg_name}']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'basic-{env_test}' in software_environments._environment_templates

        variables = {
            'env_test': 'environment',
            'var_pkg_name': ''
        }
        env_expander = ramble.expander.Expander(variables, None)

        rendered_env = software_environments.render_environment('basic-environment', env_expander)
        assert rendered_env.name == 'basic-environment'


def test_template_software_environments(request, mutable_mock_workspace_path):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{pkg_test}'] = {
            'spack_spec': 'basic@1.1'
        }
        spack_dict['environments'] = {
            'basic-{env_test}': {
                'packages': ['basic-{pkg_test}']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'basic-{env_test}' in software_environments._environment_templates
        assert 'basic-{pkg_test}' in software_environments._package_templates

        variables = {
            'env_test': 'environment',
            'pkg_test': 'package',
        }
        env_expander = ramble.expander.Expander(variables, None)

        rendered_env = software_environments.render_environment('basic-environment', env_expander)
        assert rendered_env.name == 'basic-environment'
        pkg_found = False
        for pkg in rendered_env._packages:
            if pkg.name == 'basic-package':
                pkg_found = True
        assert pkg_found


def test_multi_template_software_environments(request, mutable_mock_workspace_path):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic1-{pkg_test}'] = {
            'spack_spec': 'basic@1.1'
        }
        spack_dict['packages']['basic2-{pkg_test}'] = {
            'spack_spec': 'basic@1.1'
        }
        spack_dict['environments'] = {
            'all-basic-{env_test}': {
                'packages': ['basic1-{pkg_test}', 'basic2-{pkg_test}']
            },
            'basic1-{env_test}': {
                'packages': ['basic1-{pkg_test}']
            },
            'basic2-{env_test}': {
                'packages': ['basic2-{pkg_test}']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'all-basic-{env_test}' in software_environments._environment_templates
        assert 'basic1-{env_test}' in software_environments._environment_templates
        assert 'basic2-{env_test}' in software_environments._environment_templates
        assert 'basic1-{pkg_test}' in software_environments._package_templates
        assert 'basic2-{pkg_test}' in software_environments._package_templates

        variables = {
            'env_test': 'environment',
            'pkg_test': 'package',
        }
        env_expander = ramble.expander.Expander(variables, None)

        env_tests = {
            'all-basic-environment': ['basic1-package', 'basic2-package'],
            'basic1-environment': ['basic1-package'],
            'basic2-environment': ['basic2-package']
        }

        for env_name, env_packages in env_tests.items():
            rendered_env = software_environments.render_environment(env_name, env_expander)
            assert rendered_env.name == env_name

            assert len(rendered_env._packages) == len(env_packages)
            for pkg_name in env_packages:
                pkg_found = False
                for pkg in rendered_env._packages:
                    if pkg.name == pkg_name:
                        pkg_found = True
                assert pkg_found


def test_undefined_package_errors(request, mutable_mock_workspace_path):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{pkg_test}'] = {
            'spack_spec': 'basic@{pkg_ver}'
        }
        spack_dict['environments'] = {
            'all-basic-{env_test}': {
                'packages': ['foo-basic-{pkg_test}']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        variables = {
            'env_test': 'environment'
        }

        env_expander = ramble.expander.Expander(variables, None)

        with pytest.raises(ramble.software_environments.RambleSoftwareEnvironmentError) as pkg_err:
            _  = software_environments.render_environment('all-basic-environment', env_expander)

        err_str = \
            'Environment template all-basic-{env_test} references undefined ' \
            + 'package foo-basic-{pkg_test}'
        assert err_str in str(pkg_err)


def test_invalid_packages_error(request, mutable_mock_workspace_path):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{pkg_test}'] = {
            'spack_spec': 'basic@{pkg_ver}'
        }
        spack_dict['environments'] = {
            'all-basic-{env_test}': {
                'packages': ['basic-{pkg_test}']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'all-basic-{env_test}' in software_environments._environment_templates
        assert 'basic-{pkg_test}' in software_environments._package_templates

        variables = {
            'env_test': 'environment',
            'pkg_test': 'package',
            'pkg_ver': '1.1',
        }
        env_expander = ramble.expander.Expander(variables, None)

        _ = software_environments.render_environment('all-basic-environment', env_expander)

        with pytest.raises(ramble.software_environments.RambleSoftwareEnvironmentError) as pkg_err:
            variables = {
                'env_test': 'environment',
                'pkg_test': 'package',
                'pkg_ver': '1.4',
            }
            env_expander = ramble.expander.Expander(variables, None)

            _ = software_environments.render_environment('all-basic-environment',
                                                         env_expander)
        assert 'Package basic-package defined multiple times' in str(pkg_err)


def test_invalid_environment_error(request, mutable_mock_workspace_path):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic1-{pkg_test}'] = {
            'spack_spec': 'basic@1.1'
        }
        spack_dict['packages']['basic2-{pkg_test}'] = {
            'spack_spec': 'basic@1.1'
        }
        spack_dict['environments'] = {
            'all-basic-{env_test}': {
                'packages': ['basic1-{pkg_test}', 'basic2-{pkg_test}']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'all-basic-{env_test}' in software_environments._environment_templates
        assert 'basic1-{pkg_test}' in software_environments._package_templates
        assert 'basic2-{pkg_test}' in software_environments._package_templates

        variables = {
            'env_test': 'environment',
            'pkg_test': 'package',
        }
        env_expander = ramble.expander.Expander(variables, None)

        _ = software_environments.render_environment('all-basic-environment', env_expander)

        variables = {
            'env_test': 'environment',
            'pkg_test': 'other-package'
        }

        env_expander = ramble.expander.Expander(variables, None)

        with pytest.raises(ramble.software_environments.RambleSoftwareEnvironmentError) as env_err:
            _ = software_environments.render_environment('all-basic-environment', env_expander)

        assert 'Environment all-basic-environment defined multiple times' in str(env_err)


def test_undefined_compiler_errors(request, mutable_mock_workspace_path):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic'] = {
            'spack_spec': 'basic@1.1',
            'compiler': 'foo_comp'
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': ['basic']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'basic' in software_environments._environment_templates
        assert 'basic' in software_environments._package_templates

        variables = {}
        env_expander = ramble.expander.Expander(variables, None)

        with pytest.raises(ramble.software_environments.RambleSoftwareEnvironmentError) \
                as comp_err:
            _ = software_environments.render_environment('basic', env_expander)
        assert 'Compiler foo_comp used, but not defined' in str(comp_err)


def test_compiler_in_environment_warns(request, mutable_mock_workspace_path, capsys):
    ws_name = request.node.name

    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['test_comp'] = {
            'spack_spec': 'comp@2.1'
        }
        spack_dict['packages']['basic'] = {
            'spack_spec': 'basic@1.1',
            'compiler': 'test_comp'
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': ['basic', 'test_comp']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert 'basic' in software_environments._environment_templates
        assert 'basic' in software_environments._package_templates

        variables = {}
        env_expander = ramble.expander.Expander(variables, None)

        _ = software_environments.render_environment('basic', env_expander)
        captured = capsys.readouterr()

        assert 'Environment basic contains packages and their compilers' in captured.err
        assert 'Package: basic, Compiler: test_comp' in captured.err
