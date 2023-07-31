# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import pytest

import ramble.workspace
import ramble.software_environments
import ramble.renderer
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path',
                                     'mutable_mock_apps_repo',
                                     )

workspace  = RambleCommand('workspace')


def test_basic_software_environment(mutable_mock_workspace_path):
    ws_name = 'test_basic_software_environment'
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

        assert len(software_environments._packages.keys()) == 1
        assert 'basic' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic' in software_environments._environments['basic']['packages']


def test_package_vector_expansion(mutable_mock_workspace_path):
    ws_name = 'test_package_vector_expansion'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}'] = {
            'spack_spec': 'basic@1.1 target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4']
            }
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': ['basic-x86_64', 'basic-x86_64_v4']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert 'basic-x86_64' in software_environments._packages.keys()
        assert 'basic-x86_64_v4' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-x86_64_v4' in software_environments._environments['basic']['packages']


def test_package_matrix_expansion(mutable_mock_workspace_path):
    ws_name = 'test_package_matrix_expansion'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{ver}-{arch}'] = {
            'spack_spec': 'basic@{ver} target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4'],
                'ver': ['1.1', '2.0']
            },
            'matrix': ['arch', 'ver']
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': [
                    'basic-1.1-x86_64',
                    'basic-2.0-x86_64',
                    'basic-1.1-x86_64_v4',
                    'basic-2.0-x86_64_v4',
                ]
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 4
        assert 'basic-1.1-x86_64' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-2.0-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-1.1-x86_64_v4' in software_environments._environments['basic']['packages']
        assert 'basic-2.0-x86_64_v4' in software_environments._environments['basic']['packages']


def test_package_matrices_expansion(mutable_mock_workspace_path):
    ws_name = 'test_package_matrices_expansion'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{ver}-{arch}'] = {
            'spack_spec': 'basic@{ver} target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4'],
                'ver': ['1.1', '2.0']
            },
            'matrices': [['arch'], ['ver']]
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': [
                    'basic-1.1-x86_64',
                    'basic-2.0-x86_64_v4',
                ]
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert 'basic-1.1-x86_64' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-2.0-x86_64_v4' in software_environments._environments['basic']['packages']


def test_package_matrix_vector_expansion(mutable_mock_workspace_path):
    ws_name = 'test_package_matrix_vector_expansion'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{ver}-{arch}'] = {
            'spack_spec': 'basic@{ver} target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4'],
                'ver': ['1.1', '2.0']
            },
            'matrices': [['arch']]
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': [
                    'basic-1.1-x86_64',
                    'basic-2.0-x86_64',
                    'basic-1.1-x86_64_v4',
                    'basic-2.0-x86_64_v4',
                ]
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 4
        assert 'basic-1.1-x86_64' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-2.0-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-1.1-x86_64_v4' in software_environments._environments['basic']['packages']
        assert 'basic-2.0-x86_64_v4' in software_environments._environments['basic']['packages']


def test_environment_vector_expansion(mutable_mock_workspace_path):
    ws_name = 'test_environment_vector_expansion'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}'] = {
            'spack_spec': 'basic@1.1 target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4']
            }
        }
        spack_dict['environments'] = {
            'basic-{arch}': {
                'packages': ['basic-{arch}'],
                'variables': {
                    'arch': ['x86_64', 'x86_64_v4']
                }
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert len(software_environments._environments.keys()) == 2
        assert 'basic-x86_64' in software_environments._packages.keys()
        assert 'basic-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-x86_64' in software_environments._environments.keys()
        assert 'basic-x86_64_v4' in software_environments._environments.keys()
        assert len(software_environments._environments['basic-x86_64']['packages']) == 1
        assert 'basic-x86_64' in software_environments._environments['basic-x86_64']['packages']
        assert len(software_environments._environments['basic-x86_64_v4']['packages']) == 1
        assert 'basic-x86_64_v4' in \
            software_environments._environments['basic-x86_64_v4']['packages']


def test_environment_matrix_expansion(mutable_mock_workspace_path):
    ws_name = 'test_environment_matrix_expansion'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{ver}-{arch}'] = {
            'spack_spec': 'basic@{ver} target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4'],
                'ver': ['1.1', '2.0']
            },
            'matrix': ['arch', 'ver']
        }
        spack_dict['environments'] = {
            'basic-{ver}-{arch}': {
                'packages': [
                    'basic-{ver}-{arch}'
                ],
                'variables': {
                    'arch': ['x86_64', 'x86_64_v4'],
                    'ver': ['1.1', '2.0']
                },
                'matrix': ['arch', 'ver']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 4
        assert len(software_environments._environments.keys()) == 4
        assert 'basic-1.1-x86_64' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64' in software_environments._environments.keys()
        assert 'basic-2.0-x86_64' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64_v4' in software_environments._environments.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64' in \
            software_environments._environments['basic-1.1-x86_64']['packages']
        assert 'basic-2.0-x86_64' in \
            software_environments._environments['basic-2.0-x86_64']['packages']
        assert 'basic-1.1-x86_64_v4' in \
            software_environments._environments['basic-1.1-x86_64_v4']['packages']
        assert 'basic-2.0-x86_64_v4' in \
            software_environments._environments['basic-2.0-x86_64_v4']['packages']


def test_environment_matrices_expansion(mutable_mock_workspace_path):
    ws_name = 'test_environment_matrices_expansion'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{ver}-{arch}'] = {
            'spack_spec': 'basic@{ver} target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4'],
                'ver': ['1.1', '2.0']
            },
            'matrix': ['arch', 'ver']
        }
        spack_dict['environments'] = {
            'basic-{ver}-{arch}': {
                'packages': [
                    'basic-{ver}-{arch}'
                ],
                'variables': {
                    'arch': ['x86_64', 'x86_64_v4'],
                    'ver': ['1.1', '2.0']
                },
                'matrices': [['arch'], ['ver']]
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 4
        assert len(software_environments._environments.keys()) == 2
        assert 'basic-1.1-x86_64' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64' in software_environments._environments.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64' in \
            software_environments._environments['basic-1.1-x86_64']['packages']
        assert 'basic-2.0-x86_64_v4' in \
            software_environments._environments['basic-2.0-x86_64_v4']['packages']


def test_environment_vector_matrix_expansion(mutable_mock_workspace_path):
    ws_name = 'test_environment_vector_matrix_expansion'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{ver}-{arch}'] = {
            'spack_spec': 'basic@{ver} target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4'],
                'ver': ['1.1', '2.0']
            },
            'matrices': [['ver']]
        }
        spack_dict['environments'] = {
            'basic-{ver}-{arch}': {
                'packages': [
                    'basic-{ver}-{arch}'
                ],
                'variables': {
                    'arch': ['x86_64', 'x86_64_v4'],
                    'ver': ['1.1', '2.0']
                },
                'matrices': [['ver']]
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 4
        assert len(software_environments._environments.keys()) == 4
        assert 'basic-1.1-x86_64' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64' in software_environments._environments.keys()
        assert 'basic-2.0-x86_64' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64_v4' in software_environments._environments.keys()
        assert 'basic-2.0-x86_64_v4' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64' in \
            software_environments._environments['basic-1.1-x86_64']['packages']
        assert 'basic-2.0-x86_64' in \
            software_environments._environments['basic-2.0-x86_64']['packages']
        assert 'basic-1.1-x86_64_v4' in \
            software_environments._environments['basic-1.1-x86_64_v4']['packages']
        assert 'basic-2.0-x86_64_v4' in \
            software_environments._environments['basic-2.0-x86_64_v4']['packages']


def test_package_vector_expansion_spack_level(mutable_mock_workspace_path):
    ws_name = 'test_package_vector_expansion_spack_level'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['variables'] = {}
        spack_dict['variables']['arch'] = ['x86_64', 'x86_64_v4']
        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}'] = {
            'spack_spec': 'basic@1.1 target={arch}'
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': ['basic-x86_64', 'basic-x86_64_v4']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert 'basic-x86_64' in software_environments._packages.keys()
        assert 'basic-x86_64_v4' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-x86_64_v4' in software_environments._environments['basic']['packages']


def test_package_vector_expansion_workspace_level(mutable_mock_workspace_path):
    ws_name = 'test_package_vector_expansion_spack_level'
    workspace('create', ws_name)

    test_config = """
ramble:
  variables:
    arch: ['x86_64', 'x86_64_v4']
  applications: {}
  spack: {}
"""

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        with open(os.path.join(ws.config_dir, 'ramble.yaml'), 'w+') as f:
            f.write(test_config)

        ws._re_read()
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}'] = {
            'spack_spec': 'basic@1.1 target={arch}'
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': ['basic-x86_64', 'basic-x86_64_v4']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert 'basic-x86_64' in software_environments._packages.keys()
        assert 'basic-x86_64_v4' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-x86_64_v4' in software_environments._environments['basic']['packages']


def test_package_vector_expansion_multi_level(mutable_mock_workspace_path):
    ws_name = 'test_package_vector_expansion_multi_level'
    workspace('create', ws_name)

    test_config = """
ramble:
  variables:
    arch: ['x86_64', 'x86_64_v4']
  applications: {}
  spack: {}
"""

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        with open(os.path.join(ws.config_dir, 'ramble.yaml'), 'w+') as f:
            f.write(test_config)

        ws._re_read()
        spack_dict = ws.get_spack_dict()

        spack_dict['variables'] = {}
        spack_dict['variables']['test'] = ['test1', 'test2']
        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}-{test}-{pkg_level}'] = {
            'spack_spec': 'basic@1.1 target={arch}',
            'variables': {
                'pkg_level': ['ll1', 'll2'],
            }
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': ['basic-x86_64-test1-ll1', 'basic-x86_64_v4-test2-ll2']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert 'basic-x86_64-test1-ll1' in software_environments._packages.keys()
        assert 'basic-x86_64_v4-test2-ll2' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-x86_64-test1-ll1' in software_environments._environments['basic']['packages']
        assert 'basic-x86_64_v4-test2-ll2' in \
            software_environments._environments['basic']['packages']


def test_environment_vector_expansion_spack_level(mutable_mock_workspace_path):
    ws_name = 'test_environment_vector_expansion_spack_level'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['variables'] = {}
        spack_dict['variables']['arch'] = ['x86_64', 'x86_64_v4']
        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}'] = {
            'spack_spec': 'basic@1.1 target={arch}',
        }
        spack_dict['environments'] = {
            'basic-{arch}': {
                'packages': ['basic-{arch}'],
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert len(software_environments._environments.keys()) == 2
        assert 'basic-x86_64' in software_environments._packages.keys()
        assert 'basic-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-x86_64' in software_environments._environments.keys()
        assert 'basic-x86_64_v4' in software_environments._environments.keys()
        assert len(software_environments._environments['basic-x86_64']['packages']) == 1
        assert 'basic-x86_64' in software_environments._environments['basic-x86_64']['packages']
        assert len(software_environments._environments['basic-x86_64_v4']['packages']) == 1
        assert 'basic-x86_64_v4' in \
            software_environments._environments['basic-x86_64_v4']['packages']


def test_environment_vector_expansion_workspace_level(mutable_mock_workspace_path):
    ws_name = 'test_environment_vector_expansion_workspace_level'
    workspace('create', ws_name)

    test_config = """
ramble:
  variables:
    arch: ['x86_64', 'x86_64_v4']
  applications: {}
  spack: {}
"""

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        with open(os.path.join(ws.config_dir, 'ramble.yaml'), 'w+') as f:
            f.write(test_config)

        ws._re_read()
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}'] = {
            'spack_spec': 'basic@1.1 target={arch}',
        }
        spack_dict['environments'] = {
            'basic-{arch}': {
                'packages': ['basic-{arch}'],
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert len(software_environments._environments.keys()) == 2
        assert 'basic-x86_64' in software_environments._packages.keys()
        assert 'basic-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-x86_64' in software_environments._environments.keys()
        assert 'basic-x86_64_v4' in software_environments._environments.keys()
        assert len(software_environments._environments['basic-x86_64']['packages']) == 1
        assert 'basic-x86_64' in software_environments._environments['basic-x86_64']['packages']
        assert len(software_environments._environments['basic-x86_64_v4']['packages']) == 1
        assert 'basic-x86_64_v4' in \
            software_environments._environments['basic-x86_64_v4']['packages']


def test_environment_warns_with_pkg_compiler(mutable_mock_workspace_path, capsys):
    ws_name = 'test_environment_warns_with_pkg_compiler'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['test_comp'] = {
            'spack_spec': 'test_comp@1.1'
        }
        spack_dict['packages']['basic'] = {
            'spack_spec': 'basic@1.1',
            'compiler': 'test_comp'
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': [
                    'basic',
                    'test_comp'
                ],
            }
        }

        ramble.software_environments.SoftwareEnvironments(ws)
        captured = capsys.readouterr()

        assert 'Environment basic contains packages and their compilers ' + \
               'in the package list. These include:' in captured.err

        assert 'Package: basic, Compiler: test_comp' in captured.err


def test_package_vector_expansion_exclusions(mutable_mock_workspace_path):
    ws_name = 'test_package_vector_expansion_exclusions'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}'] = {
            'spack_spec': 'basic@1.1 target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4']
            },
            'exclude': {
                'variables': {
                    'arch': 'x86_64_v4'
                }
            }
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': ['basic-x86_64']
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 1
        assert 'basic-x86_64' in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-x86_64_v4' not in software_environments._packages.keys()
        assert 'basic-x86_64_v4' not in software_environments._environments['basic']['packages']


def test_package_matrix_expansion_exclusions(mutable_mock_workspace_path):
    ws_name = 'test_package_matrix_expansion_exclusions'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{ver}-{arch}'] = {
            'spack_spec': 'basic@{ver} target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4'],
                'ver': ['1.1', '2.0']
            },
            'matrix': ['arch', 'ver'],
            'exclude': {
                'variables': {
                    'arch': ['x86_64_v4'],
                    'ver': ['2.0'],
                },
                'matrix': ['arch', 'ver'],
            }
        }
        spack_dict['environments'] = {
            'basic': {
                'packages': [
                    'basic-1.1-x86_64',
                    'basic-2.0-x86_64',
                    'basic-1.1-x86_64_v4',
                ]
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 3
        assert 'basic-1.1-x86_64' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64' in software_environments._packages.keys()
        assert 'basic-1.1-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-2.0-x86_64_v4' not in software_environments._packages.keys()
        assert 'basic' in software_environments._environments.keys()
        assert 'basic-1.1-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-2.0-x86_64' in software_environments._environments['basic']['packages']
        assert 'basic-1.1-x86_64_v4' in software_environments._environments['basic']['packages']
        assert 'basic-2.0-x86_64_v4' not in \
            software_environments._environments['basic']['packages']


def test_environment_vector_expansion_exclusion(mutable_mock_workspace_path):
    ws_name = 'test_package_vector_expansion_exclusions'
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        spack_dict = ws.get_spack_dict()

        spack_dict['packages'] = {}
        spack_dict['packages']['basic-{arch}'] = {
            'spack_spec': 'basic@1.1 target={arch}',
            'variables': {
                'arch': ['x86_64', 'x86_64_v4']
            },
        }
        spack_dict['environments'] = {
            'basic-{arch}': {
                'packages': ['basic-{arch}'],
                'variables': {
                    'arch': ['x86_64', 'x86_64_v4']
                },
                'exclude': {
                    'variables': {
                        'arch': 'x86_64_v4'
                    }
                }
            }
        }

        software_environments = ramble.software_environments.SoftwareEnvironments(ws)

        assert len(software_environments._packages.keys()) == 2
        assert len(software_environments._environments.keys()) == 1
        assert 'basic-x86_64' in software_environments._packages.keys()
        assert 'basic-x86_64_v4' in software_environments._packages.keys()
        assert 'basic-x86_64' in software_environments._environments.keys()
        assert 'basic-x86_64_v4' not in software_environments._environments.keys()
        assert 'basic-x86_64' in software_environments._environments['basic-x86_64']['packages']
