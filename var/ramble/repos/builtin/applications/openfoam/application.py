# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *
from ramble.expander import Expander


class Openfoam(SpackApplication):
    '''Define the Openfoam application'''
    name = 'openfoam'

    maintainers('douglasjacobsen')

    tags('cfd', 'fluid', 'dynamics')

    define_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('ompi412',
                  spack_spec='openmpi@4.1.2 +legacylaunchers +cxx',
                  compiler='gcc9')

    software_spec('flex',
                  spack_spec='flex@2.6.4',
                  compiler='gcc9')
    software_spec('openfoam',
                  spack_spec='openfoam-org@7',
                  compiler='gcc9')

    required_package('openfoam-org')

    workload('motorbike', executables=['get_inputs', 'configure_mesh', 'surfaceFeatures',
                                       'blockMesh', 'decomposePar1', 'snappyHexMesh',
                                       'reconstructParMesh', 'renumberMesh', 'configure_simplefoam',
                                       'decomposePar2', 'patchSummary', 'checkMesh', 'potentialFoam',
                                       'simpleFoam'])

    workload_variable('input_path', default='$FOAM_TUTORIALS/incompressible/simpleFoam/motorBike',
                      description='Path to the tutorial input',
                      workload='motorbike')
    workload_variable('geometry_path', default='$FOAM_TUTORIALS/resources/geometry/motorBike.obj.gz',
                      description='Path to the geometry resource',
                      workload='motorbike')
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

    workload_variable('end_time', default='250',
                      description='End time for simulation',
                      workload='motorbike')
    workload_variable('write_interval', default='500',
                      description='Interval to write output files',
                      workload='motorbike')
    workload_variable('start_from', default='startTime',
                      description='How to start a new simulation',
                      workload='motorbike')
    workload_variable('mesh_size', default='(20 8 8)',
                      description='Mesh size for simulation',
                      workload='motorbike')
    workload_variable('mesh_size', default='(50 20 20)',
                      description='Mesh size for simulation',
                      workload='hpc_motorbike')
    workload_variable('max_local_cells', default='100000',
                      description='Max local cells for simulation',
                      workload='motorbike')
    workload_variable('max_local_cells', default='10000000',
                      description='Max local cells for simulation',
                      workload='hpc_motorbike')
    workload_variable('max_global_cells', default='50000000',
                      description='Max global cells for simulation',
                      workload='motorbike')
    workload_variable('max_global_cells', default='200000000',
                      description='Max global cells for simulation',
                      workload='hpc_motorbike')

    workload_variable('n_ranks_hex', default='16',
                      description='Number of ranks to use for snappyHexMesh',
                      workloads=['motorbike'])
    workload_variable('n_ranks_hex', default='{n_rank}',
                      description='Number of ranks to use for snappyHexMesh',
                      workloads=['hpc_motorbike'])
    workload_variable('hex_flags', default='-overwrite',
                      description='Flags for snappyHexMesh',
                      workloads=['hpc_motorbike', 'motorbike'])
    workload_variable('potential_flags', default='-parallel',
                      description='Flags for potentialFoam',
                      workloads=['hpc_motorbike', 'motorbike'])
    workload_variable('simple_flags', default='-parallel',
                      description='Flags for simpleFoam',
                      workloads=['hpc_motorbike', 'motorbike'])

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
               sha256='b285a18332fd718dbdc6b6c90dd7f134c9745cb7eb479d93b394160bbef97390',
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

    executable('configure_mesh', template=['. $WM_PROJECT_DIR/bin/tools/RunFunctions',
                                           'rm log.*',
                                           'foamDictionary -entry "numberOfSubdomains" -set "{n_ranks_hex}" {decomposition_path}',
                                           'foamDictionary -entry "method" -set "hierarchical" {decomposition_path}',
                                           'foamDictionary -entry "hierarchicalCoeffs.n" -set "(4 2 2)" {decomposition_path}',
                                           'foamDictionary -entry "castellatedMeshControls.maxLocalCells" -set "{max_local_cells}" {hex_mesh_path}',
                                           'foamDictionary -entry "castellatedMeshControls.maxGlobalCells" -set "{max_global_cells}" {hex_mesh_path}',
                                           'sed "s/(20 8 8)/{mesh_size}/" -i {block_mesh_path}',
                                           'ln -s 0 0.orig'],
               use_mpi=False)

    executable('configure_simplefoam', template=['. $WM_PROJECT_DIR/bin/tools/RunFunctions',
                                                 'foamDictionary -entry "numberOfSubdomains" -set "{n_ranks}" {decomposition_path}',
                                                 'foamDictionary -entry "endTime" -set "{end_time}" {control_path}',
                                                 'foamDictionary -entry "writeInterval" -set "{write_interval}" {control_path}',
                                                 'foamDictionary -entry "startFrom" -set "{start_from}" {control_path}',
                                                 'foamDictionary -entry "hierarchicalCoeffs.n" -set "(3 2 1)" {decomposition_path}',
                                                 'foamDictionary -entry "method" -set "scotch" {decomposition_path}',
                                                 'foamDictionary system/fvSolution -entry relaxationFactors.equations.U -set "0.7"',
                                                 'foamDictionary system/fvSolution -entry relaxationFactors.fields -add "{}"',
                                                 'foamDictionary system/fvSolution -entry relaxationFactors.fields.p -set "0.3"',
                                                 'foamDictionary system/fvSolution -entry solvers.p.nPreSweeps -set "0"',
                                                 'foamDictionary system/fvSolution -entry solvers.p.nPostSweeps -set "2"',
                                                 'foamDictionary system/fvSolution -entry solvers.p.cacheAgglomeration -set "on"',
                                                 'foamDictionary system/fvSolution -entry solvers.p.agglomerator -set "faceAreaPair"',
                                                 'foamDictionary system/fvSolution -entry solvers.p.nCellsInCoarsestLevel -set "10"',
                                                 'foamDictionary system/fvSolution -entry solvers.p.mergeLevels -set "1"',
                                                 'foamDictionary system/fvSolution -entry SIMPLE.consistent -set "yes"'],
               use_mpi=False)

    executable('surfaceFeatures', 'runApplication surfaceFeatures',
               use_mpi=False)

    executable('blockMesh', 'runApplication blockMesh',
               use_mpi=False)

    executable('decomposePar1', template=['rm log.decomposePar', 'runApplication decomposePar'],
               use_mpi=False)

    executable('decomposePar2', template=['rm log.decomposePar', 'runApplication decomposePar'],
               use_mpi=False)

    executable('snappyHexMesh', 'runParallel snappyHexMesh {hex_flags}', use_mpi=False)
    executable('patchSummary', 'patchSummary', use_mpi=True,
               redirect='{experiment_run_dir}/log.patchSummary')
    executable('checkMesh', 'checkMesh', use_mpi=True,
               redirect='{experiment_run_dir}/log.checkMesh')
    executable('potentialFoam', 'potentialFoam {potential_flags}', use_mpi=True,
               redirect='{experiment_run_dir}/log.potentialFoam')
    executable('simpleFoam', 'simpleFoam {simple_flags}', use_mpi=True,
               redirect='{experiment_run_dir}/log.simpleFoam')

    executable('reconstructParMesh', 'reconstructParMesh -constant', use_mpi=False,
               redirect='{experiment_run_dir}/log.reconstructParMesh')

    executable('renumberMesh', template=['rm -rf processor*',
                                         'renumberMesh -constant -overwrite'],
               use_mpi=False,
               redirect='{experiment_run_dir}/log.renumberMesh')

    executable('allRun', template=[r'sed "s/writephi/writePhi/g" -i Allrun',
                                   r'sed "s/rm.*log./#/g" -i Allclean',
                                   r'chmod a+x Allrun',
                                   './Allrun'],
               use_mpi=False)

    log_prefix = os.path.join(Expander.expansion_str('experiment_run_dir'), 'log.')

    figure_of_merit('Number of cells', log_file=(log_prefix + 'snappyHexMesh'),
                    fom_regex=r'Layer mesh\s+:\s+cells:(?P<ncells>[0-9]+)\s+.*',
                    group_name='ncells', units='')

    figure_of_merit('snappyHexMesh Time ({n_ranks_hex} ranks)', log_file=(log_prefix + 'snappyHexMesh'),
                    fom_regex=r'Finished meshing in = (?P<mesh_time>[0-9]+\.?[0-9]*).*',
                    group_name='mesh_time', units='s')

    figure_of_merit('simpleFoam Time ({n_ranks} ranks)', log_file=(log_prefix + 'simpleFoam'),
                    fom_regex=r'\s*ExecutionTime = (?P<foam_time>[0-9]+\.?[0-9]*).*',
                    group_name='foam_time', units='s')

    figure_of_merit('potentialFoam Time ({n_ranks} ranks)', log_file=(log_prefix + 'potentialFoam'),
                    fom_regex=r'\s*ExecutionTime = (?P<foam_time>[0-9]+\.?[0-9]*).*',
                    group_name='foam_time', units='s')

    success_criteria('snappyHexMesh_completed', mode='string', match='Finalising parallel run',
                     file='{experiment_run_dir}/log.snappyHexMesh')

    success_criteria('simpleFoam_completed', mode='string', match='Finalising parallel run',
                     file='{experiment_run_dir}/log.simpleFoam')
