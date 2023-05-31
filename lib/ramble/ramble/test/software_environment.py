# Copyright 2022-2023 Google LLC
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
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path',
                                     'mutable_mock_repo',
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
