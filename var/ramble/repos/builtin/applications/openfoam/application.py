# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Openfoam(SpackApplication):
    '''Define the Openfoam application'''
    name = 'openfoam'

    maintainers('douglasjacobsen')

    tags('cfd', 'fluid', 'dynamics')

    default_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('ompi412',
                  spack_spec='openmpi@4.1.2 +legacylaunchers +pmi +thread_multiple +cxx',
                  compiler='gcc9')

    software_spec('flex',
                  spack_spec='flex@2.6.4',
                  compiler='gcc9')
    software_spec('openfoam',
                  spack_spec='openfoam-org@7',
                  compiler='gcc9')

    required_package('openfoam-org')

    workload('motorbike', executables=['get_inputs', 'configure', 'serial_decompose',
                                       'snappyHexMesh', 'patchSummary', 'potentialFoam',
                                       'simpleFoam', 'reconstructParMesh', 'reconstructPar'])

    workload('motorbike_20m', executables=['get_inputs', 'configure', 'serial_decompose',
                                           'snappyHexMesh', 'patchSummary', 'potentialFoam',
                                           'simpleFoam', 'reconstructParMesh', 'reconstructPar'])

    workload('motorbike_42m', executables=['get_inputs', 'configure', 'serial_decompose',
                                           'snappyHexMesh', 'patchSummary', 'potentialFoam',
                                           'simpleFoam', 'reconstructParMesh', 'reconstructPar'])

    workload_variable('input_path', default='$FOAM_TUTORIALS/incompressible/simpleFoam/motorBike',
                      description='Path to the tutorial input',
                      workloads=['motorbike', 'motorbike_20m', 'motorbike_42'])
    workload_variable('geometry_path', default='$FOAM_TUTORIALS/resources/geometry/motorBike.obj.gz',
                      description='Path to the geometry resource',
                      workloads=['motorbike', 'motorbike_20m', 'motorbike_42'])
    workload_variable('decomposition_path', default='system/decomposeParDict*',
                      description='Path to decomposition files',
                      workloads=['hpc_motorbike', 'motorbike'])
    workload_variable('control_path', default='system/controlDict',
                      description='Path to control file',
                      workloads=['hpc_motorbike', 'motorbike'])
    workload_variable('block_mesh_path', default='system/blockMeshDict',
                      description='Path to block mesh file',
                      workloads=['hpc_motorike', 'motorbike'])
    workload_variable('hex_mesh_path', default='system/snappyHexMeshDict',
                      description='Path to hexh mesh file',
                      workloads=['hpc_motorbike', 'motorbike'])

    workload_variable('end_time', default='500',
                      description='End time for simulation',
                      workloads=['motorbike'])
    workload_variable('end_time', default='250',
                      description='End time for simulation',
                      workloads=['motorbike_20m', 'motorbike_42'])
    workload_variable('mesh_size', default='(20 8 8)',
                      description='Mesh size for simulation',
                      workload='motorbike')
    workload_variable('mesh_size', default='(100 40 40)',
                      description='Mesh size for simulation',
                      workload='motorbike')
    workload_variable('mesh_size', default='(130 52 52)',
                      description='Mesh size for simulation',
                      workload='hpc_motorbike')
    workload_variable('max_local_cells', default='100000',
                      description='Max local cells for simulation',
                      workloads=['motorbike', 'motorbike_20m', 'motorbike_42m'])
    workload_variable('max_local_cells', default='10000000',
                      description='Max local cells for simulation',
                      workload='hpc_motorbike')
    workload_variable('max_global_cells', default='200000',
                      description='Max global cells for simulation',
                      workload='motorbike')
    workload_variable('max_global_cells', default='50000000',
                      description='Max global cells for simulation',
                      workloads=['motorbike_20m', 'motorbike_42m'])
    workload_variable('max_global_cells', default='200000000',
                      description='Max global cells for simulation',
                      workload='hpc_motorbike')

    workload_variable('x_decomp', default='{n_ranks}',
                      description='Workload X decomposition',
                      workloads=['motorbike', 'motorbike_20m', 'motorbike_42'])
    workload_variable('y_decomp', default='1',
                      description='Workload Y decomposition',
                      workloads=['motorbike', 'motorbike_20m', 'motorbike_42'])
    workload_variable('z_decomp', default='1',
                      description='Workload Z decomposition',
                      workloads=['motorbike', 'motorbike_20m', 'motorbike_42'])

    workload_variable('decomp', default='({x_decomp} {y_decomp} {z_decomp})',
                      description='Workload decomposition',
                      workloads=['motorbike', 'motorbike_20m', 'motorbike_42'])

    workload_variable('hex_flags', default='-overwrite -parallel',
                      description='Flags for snappyHexMesh',
                      workloads=['hpc_motorbike', 'motorbike', 'motorbike_20m', 'motorbike_42m'])
    workload_variable('potential_flags', default='-parallel',
                      description='Flags for potentialFoam',
                      workloads=['hpc_motorbike', 'motorbike', 'motorbike_20m', 'motorbike_42m'])
    workload_variable('simple_flags', default='-parallel',
                      description='Flags for simpleFoam',
                      workloads=['hpc_motorbike', 'motorbike', 'motorbike_20m', 'motorbike_42m'])

    workload('hpc_motorbike', executables=['build_mesh', 'allRun'],
             input='hpc_motorbike')
    workload_variable('size', default='Large',
                      description='Size of HPC motorbike workload. Can be Large, Medium, or Small.',
                      workload='hpc_motorbike')
    workload_variable('input_version', default='v1912',
                      description='Version of Openfoam the input was made for. Options are v8 and v1912.',
                      workload='hpc_motorbike')
    workload_variable('input_path', default='{hpc_motorbike}/HPC_motorbike/{size}/{input_version}',
                      description='Path to the HPC_motorbike input',
                      workload='hpc_motorbike')

    input_file('hpc_motorbike',
               url='https://develop.openfoam.com/committees/hpc/-/archive/develop/hpc-develop.tar.gz',
               description='HPC Benchmarking version of the Motorbike input')

    executable('get_inputs', template=['cp -R {input_path}/* {experiment_run_dir}/.',
                                       'mkdir -p constant/triSurface',
                                       'mkdir -p constant/geometry',
                                       'cp {geometry_path} constant/triSurface/.',
                                       'cp {geometry_path} constant/geometry/.'],
               use_mpi=False)

    executable('build_mesh', template=['cp -R {input_path}/* {experiment_run_dir}/.',
                                       r'sed "/^numberOfSubdomains/ c\\numberOfSubdomains {n_ranks};" -i {decomposition_path}',
                                       'chmod a+x All*',
                                       'mv Allmesh* Allmesh',
                                       './Allmesh'],
               use_mpi=False)

    executable('configure', template=[r'sed "/^numberOfSubdomains/ c\\numberOfSubdomains {n_ranks};" -i {decomposition_path}',
                                      r'sed "/^method/c\\method          scotch;" -i {decomposition_path}',
                                      'sed "s/(3 2 1)/{decomp}/" -i {decomposition_path}',
                                      r'sed "/^endTime/c\\endTime {end_time};" -i {control_path}',
                                      r'sed "/^writeInterval/c\\writeInterval {end_time};" -i {control_path}',
                                      'sed "s/(20 8 8)/{mesh_size}/" -i {block_mesh_path}',
                                      'sed "s/maxLocalCells 100000/maxLocalCells {max_local_cells}/" -i {hex_mesh_path}',
                                      'sed "s/maxGlobalCells 2000000/maxGlobalCells {max_global_cells}/" -i {hex_mesh_path}',
                                      'ln -s 0.orig 0'],
               use_mpi=False)

    executable('serial_decompose', template=['surfaceFeatures',
                                             'blockMesh',
                                             'decomposePar -copyZero'],
               use_mpi=False)

    executable('snappyHexMesh', 'snappyHexMesh {hex_flags}', use_mpi=True,
               redirect='{experiment_run_dir}/log.snappyHexMesh')
    executable('patchSummary', 'patchSummary', use_mpi=True,
               redirect='{experiment_run_dir}/log.patchSummary')
    executable('potentialFoam', 'potentialFoam {potential_flags}', use_mpi=True,
               redirect='{experiment_run_dir}/log.potentialFoam')
    executable('simpleFoam', 'simpleFoam {simple_flags}', use_mpi=True,
               redirect='{experiment_run_dir}/log.simpleFoam')

    executable('reconstructParMesh', 'reconstructParMesh -constant', use_mpi=False,
               redirect='{experiment_run_dir}/log.reconstructParMesh')
    executable('reconstructPar', 'reconstructPar -latestTime', use_mpi=False,
               redirect='{experiment_run_dir}/log.reconstructPar')

    executable('allRun', template=[r'sed "s/writephi/writePhi/g" -i Allrun',
                                   r'sed "s/rm.*log./#/g" -i Allclean',
                                   r'chmod a+x Allrun',
                                   './Allrun'],
               use_mpi=False)

    figure_of_merit('snappyHexMesh Time', log_file='{experiment_run_dir}/log.snappyHexMesh',
                    fom_regex=r'Finished meshing in = (?P<mesh_time>[0-9]+\.?[0-9]*).*',
                    group_name='mesh_time', units='s')

    figure_of_merit('simpleFoam Time', log_file='{experiment_run_dir}/log.simpleFoam',
                    fom_regex=r'\s*ExecutionTime = (?P<foam_time>[0-9]+\.?[0-9]*).*',
                    group_name='foam_time', units='s')

    figure_of_merit('potentialFoam Time', log_file='{experiment_run_dir}/log.potentialFoam',
                    fom_regex=r'\s*ExecutionTime = (?P<foam_time>[0-9]+\.?[0-9]*).*',
                    group_name='foam_time', units='s')
