# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *
from ramble.expander import Expander


class Openfoam(ExecutableApplication):
    """Base application definition for OpenFoam"""

    name = "openfoamorg"

    maintainers("douglasjacobsen")

    tags("cfd", "fluid", "dynamics")

    workload(
        "motorbike",
        executables=[
            "clean",
            "get_inputs",
            "configure_mesh",
            "surfaceFeatures",
            "blockMesh",
            "decomposePar1",
            "snappyHexMesh",
            "configure_simplefoam",
            "redistributePar",
            "decomposePar2",
            "patchSummary",
            "potentialFoam",
            "checkMesh",
            "simpleFoam",
        ],
    )

    workload(
        "motorbike_20m",
        executables=[
            "clean",
            "get_inputs",
            "configure_mesh",
            "surfaceFeatures",
            "blockMesh",
            "decomposePar1",
            "snappyHexMesh",
            "configure_simplefoam",
            "redistributePar",
            "decomposePar2",
            "patchSummary",
            "potentialFoam",
            "checkMesh",
            "simpleFoam",
        ],
    )

    workload(
        "motorbike_42m",
        executables=[
            "clean",
            "get_inputs",
            "configure_mesh",
            "surfaceFeatures",
            "blockMesh",
            "decomposePar1",
            "snappyHexMesh",
            "configure_simplefoam",
            "redistributePar",
            "decomposePar2",
            "patchSummary",
            "potentialFoam",
            "checkMesh",
            "simpleFoam",
        ],
    )

    workload_variable(
        "input_path",
        default="$FOAM_TUTORIALS/incompressible/simpleFoam/motorBike",
        description="Path to the tutorial input",
        workloads=["motorbike*"],
    )
    workload_variable(
        "geometry_path",
        default="$FOAM_TUTORIALS/resources/geometry/motorBike.obj.gz",
        description="Path to the geometry resource",
        workloads=["motorbike*"],
    )
    workload_variable(
        "decomposition_path",
        default="system/decomposeParDict",
        description="Path to decomposition files",
        workloads=["motorbike*"],
    )
    workload_variable(
        "control_path",
        default="system/controlDict",
        description="Path to control file",
        workloads=["motorbike*"],
    )
    workload_variable(
        "block_mesh_path",
        default="system/blockMeshDict",
        description="Path to block mesh file",
        workloads=["motorbike*"],
    )
    workload_variable(
        "hex_mesh_path",
        default="system/snappyHexMeshDict",
        description="Path to hexh mesh file",
        workloads=["motorbike*"],
    )

    workload_variable(
        "end_time",
        default="250",
        description="End time for simulation",
        workloads=["motorbike*"],
    )
    workload_variable(
        "write_interval",
        default="500",
        description="Interval to write output files",
        workloads=["motorbike*"],
    )
    workload_variable(
        "start_from",
        default="startTime",
        description="How to start a new simulation",
        workloads=["motorbike*"],
    )
    workload_variable(
        "mesh_size",
        default="(20 8 8)",
        description="Mesh size for simulation",
        workload="motorbike",
    )
    workload_variable(
        "mesh_size",
        default="(100 40 40)",
        description="Mesh size for simulation",
        workload="motorbike_20m",
    )
    workload_variable(
        "mesh_size",
        default="(130 52 52)",
        description="Mesh size for simulation",
        workload="motorbike_42m",
    )
    workload_variable(
        "max_local_cells",
        default="100000",
        description="Max local cells for simulation",
        workloads=["motorbike*"],
    )
    workload_variable(
        "max_global_cells",
        default="50000000",
        description="Max global cells for simulation",
        workloads=["motorbike*"],
    )

    workload_variable(
        "n_ranks_hex",
        default="16",
        description="Number of ranks to use for snappyHexMesh",
        workloads=["motorbike*"],
    )
    workload_variable(
        "hex_flags",
        default="-overwrite",
        description="Flags for snappyHexMesh",
        workloads=["motorbike*"],
    )
    workload_variable(
        "potential_flags",
        default="-writePhi",
        description="Flags for potentialFoam",
        workloads=["motorbike*"],
    )
    workload_variable(
        "simple_flags",
        default="",
        description="Flags for simpleFoam",
        workloads=["motorbike*"],
    )

    workload_variable(
        "dict_delim",
        description="Delimiter for dictionary entries",
        default="/",
        workloads=["motorbike*"],
    )

    workload_variable(
        "coeffs_dict",
        description="Coeffs dictionary name",
        default="hierarchicalCoeffs",
        workloads=["motorbike*"],
    )

    executable("clean", template=["rm -rf processor* constant system log.*"])

    executable(
        "get_inputs",
        template=[
            "cp -Lr {input_path}/* {experiment_run_dir}/.",
            "mkdir -p constant/triSurface",
            "mkdir -p constant/geometry",
            "cp {geometry_path} constant/triSurface/.",
            "cp {geometry_path} constant/geometry/.",
            "ln -sf {experiment_run_dir}0/U.orig {experiment_run_dir}/0/U",
        ],
        use_mpi=False,
    )

    executable(
        "configure_mesh",
        template=[
            ". $WM_PROJECT_DIR/bin/tools/RunFunctions",
            'foamDictionary -entry "numberOfSubdomains" -set "{n_ranks_hex}" {decomposition_path}',
            'foamDictionary -entry "{coeffs_dict}{dict_delim}n" -set "({min({n_ranks_hex}, {processes_per_node})} {ceil({n_ranks_hex}/{processes_per_node})} 1)" {decomposition_path}',
            'foamDictionary -entry "castellatedMeshControls{dict_delim}maxLocalCells" -set "{max_local_cells}" {hex_mesh_path}',
            'foamDictionary -entry "castellatedMeshControls{dict_delim}maxGlobalCells" -set "{max_global_cells}" {hex_mesh_path}',
            'sed "s/(20 8 8)/{mesh_size}/" -i {block_mesh_path}',
        ],
        use_mpi=False,
    )

    executable(
        "configure_simplefoam",
        template=[
            ". $WM_PROJECT_DIR/bin/tools/RunFunctions",
            'foamDictionary -entry "numberOfSubdomains" -set "{n_ranks}" {decomposition_path}',
            'foamDictionary -entry "{coeffs_dict}{dict_delim}n" -set "({processes_per_node} {n_nodes} 1)" {decomposition_path}',
            'foamDictionary -entry "endTime" -set "{end_time}" {control_path}',
            'foamDictionary -entry "writeInterval" -set "{write_interval}" {control_path}',
            'foamDictionary -entry "startFrom" -set "{start_from}" {control_path}',
            'foamDictionary system/fvSolution -entry relaxationFactors{dict_delim}fields -add "{}"',
            'foamDictionary system/fvSolution -entry relaxationFactors{dict_delim}fields{dict_delim}p -set "0.3"',
            'foamDictionary system/fvSolution -entry solvers{dict_delim}p{dict_delim}nPreSweeps -set "0"',
            'foamDictionary system/fvSolution -entry solvers{dict_delim}p{dict_delim}nPostSweeps -set "2"',
            'foamDictionary system/fvSolution -entry solvers{dict_delim}p{dict_delim}cacheAgglomeration -set "on"',
            'foamDictionary system/fvSolution -entry solvers{dict_delim}p{dict_delim}agglomerator -set "faceAreaPair"',
            'foamDictionary system/fvSolution -entry solvers{dict_delim}p{dict_delim}nCellsInCoarsestLevel -set "10"',
            'foamDictionary system/fvSolution -entry solvers{dict_delim}p{dict_delim}mergeLevels -set "1"',
            'foamDictionary system/fvSolution -entry SIMPLE{dict_delim}consistent -set "yes"',
        ],
        use_mpi=False,
    )

    executable(
        "surfaceFeatures",
        template=["surfaceFeatures", "surfaceFeatureExtract"],
        use_mpi=False,
        redirect="{experiment_run_dir}/log.surfaceFeatures",
    )

    executable(
        "blockMesh",
        "blockMesh",
        use_mpi=False,
        redirect="{experiment_run_dir}/log.blockMesh",
    )

    executable(
        "decomposePar1",
        template=["decomposePar -noZero -force"],
        use_mpi=False,
        redirect="{experiment_run_dir}/log.decomposePar1",
    )

    executable(
        "decomposePar2",
        template=["rm -rf processor*/0", "decomposePar -copyZero -fields"],
        use_mpi=False,
        redirect="{experiment_run_dir}/log.decomposePar2",
    )

    executable(
        "snappyHexMesh",
        template=["snappyHexMesh -parallel {hex_flags}"],
        use_mpi=True,
        variables={"n_ranks": "{n_ranks_hex}"},
        redirect="{experiment_run_dir}/log.snappyHexMesh",
    )

    executable(
        "redistributePar",
        "redistributePar -noZero -overwrite -parallel",
        use_mpi=True,
        redirect="{experiment_run_dir}/log.redistributePar",
    )

    executable(
        "patchSummary",
        "patchSummary -parallel",
        use_mpi=True,
        redirect="{experiment_run_dir}/log.patchSummary",
    )
    executable(
        "checkMesh",
        "checkMesh -parallel -constant",
        use_mpi=True,
        redirect="{experiment_run_dir}/log.checkMesh",
    )
    executable(
        "potentialFoam",
        "potentialFoam -parallel {potential_flags}",
        use_mpi=True,
        redirect="{experiment_run_dir}/log.potentialFoam",
    )
    executable(
        "simpleFoam",
        "simpleFoam -parallel {simple_flags}",
        use_mpi=True,
        redirect="{experiment_run_dir}/log.simpleFoam",
    )

    workload_variable(
        "export_prefix",
        default="-x",
        description="Prefix for exporting an environment variable with mpirun",
        workloads=["*"],
    )

    workload_variable(
        "workload_exports",
        default="",
        description="Placeholder variable which holds all variable exports. Defined during setup.",
        workloads=["*"],
    )

    workload_variable(
        "export_variables",
        description="Comma separated list of all env-var names that need to be exported",
        default="PATH,LD_LIBRARY_PATH,FOAM_APP,FOAM_APPBIN,FOAM_ETC,"
        + "FOAM_EXT_LIBBIN,FOAM_INST_DIR,FOAM_JOB_DIR,FOAM_LIBBIN,"
        + "FOAM_MPI,FOAM_RUN,FOAM_SETTINGS,FOAM_SIGFPE,FOAM_SITE_APPBIN,"
        + "FOAM_SITE_LIBBIN,FOAM_SOLVERS,FOAM_SRC,FOAM_TUTORIALS,"
        + "FOAM_USER_APPBIN,FOAM_USER_LIBBIN,FOAM_UTILITIES,WM_ARCH,"
        + "WM_ARCH_OPTION,WM_CC,WM_CFLAGS,WM_COMPILER,WM_COMPILER_LIB_ARCH,"
        + "WM_COMPILER_TYPE,WM_COMPILE_OPTION,WM_CXX,WM_CXXFLAGS,WM_DIR,"
        + "WM_LABEL_OPTION,WM_LABEL_SIZE,WM_LDFLAGS,WM_LINK_LANGUAGE,WM_MPLIB,"
        + "WM_OPTIONS,WM_OSTYPE,WM_PRECISION_OPTION,WM_PROJECT,WM_PROJECT_DIR,"
        + "WM_PROJECT_INST_DIR,WM_PROJECT_USER_DIR,WM_PROJECT_VERSION,"
        + "WM_THIRD_PARTY_DIR,MPI_ARCH_FLAGS,MPI_ARCH_INC,MPI_ARCH_LIBS,"
        + "MPI_ARCH_PATH,MPI_BUFFER_SIZE,MPI_ROOT",
        workloads=["*"],
    )

    log_prefix = os.path.join(
        Expander.expansion_str("experiment_run_dir"), "log."
    )

    config_file = "{experiment_run_dir}/openfoam_config"

    figure_of_merit(
        "Number of cells",
        log_file=(log_prefix + "snappyHexMesh"),
        fom_regex=r"Layer mesh\s+:\s+cells:(?P<ncells>[0-9]+)\s+.*",
        group_name="ncells",
        units="",
    )

    figure_of_merit(
        "snappyHexMesh Time",
        log_file=(log_prefix + "snappyHexMesh"),
        fom_regex=r"Finished meshing in = (?P<mesh_time>[0-9]+\.?[0-9]*).*",
        group_name="mesh_time",
        units="s",
    )

    figure_of_merit(
        "snappyHexMesh Ranks",
        log_file=config_file,
        fom_regex=r"snappyHexMesh ranks: (?P<ranks>[0-9]+)",
        group_name="ranks",
        units="",
    )

    figure_of_merit(
        "simpleFoam Time",
        log_file=(log_prefix + "simpleFoam"),
        fom_regex=r"\s*ExecutionTime = (?P<foam_time>[0-9]+\.?[0-9]*).*",
        group_name="foam_time",
        units="s",
    )

    figure_of_merit(
        "simpleFoam Time",
        log_file=(log_prefix + "simpleFoam"),
        fom_regex=r"\s*ExecutionTime = (?P<foam_time>[0-9]+\.?[0-9]*).*",
        group_name="foam_time",
        units="s",
    )

    figure_of_merit(
        "simpleFoam Ranks",
        log_file=config_file,
        fom_regex=r"simpleFoam ranks: (?P<ranks>[0-9]+)",
        group_name="ranks",
        units="",
    )

    figure_of_merit(
        "potentialFoam Time",
        log_file=(log_prefix + "potentialFoam"),
        fom_regex=r"\s*ExecutionTime = (?P<foam_time>[0-9]+\.?[0-9]*).*",
        group_name="foam_time",
        units="s",
    )

    figure_of_merit(
        "potentialFoam Ranks",
        log_file=config_file,
        fom_regex=r"potentialFoam ranks: (?P<ranks>[0-9]+)",
        group_name="ranks",
        units="",
    )

    success_criteria(
        "snappyHexMesh_completed",
        mode="string",
        match="Finalising parallel run",
        file="{experiment_run_dir}/log.snappyHexMesh",
    )

    success_criteria(
        "simpleFoam_completed",
        mode="string",
        match="Finalising parallel run",
        file="{experiment_run_dir}/log.simpleFoam",
    )

    def _prepare_analysis(self, workspace, app_inst=None):
        conf_path = self.expander.expand_var(self.config_file)

        with open(conf_path, "w+") as f:
            hex_ranks = self.expander.expand_var("{n_ranks_hex}")
            simple_ranks = self.expander.expand_var("{n_ranks}")
            f.write(f"snappyHexMesh ranks: {hex_ranks}\n")
            f.write(f"simpleFoam ranks: {simple_ranks}\n")
            f.write(f"potentialFoam ranks: {simple_ranks}\n")

    def _define_commands(self, exec_graph, success_list):
        export_prefix = self.expander.expand_var_name("export_prefix")
        export_vars = self.expander.expand_var_name("export_variables").split(
            ","
        )

        export_args = []
        for var in export_vars:
            export_args.append(f"{export_prefix} {var}")

        export_str = " ".join(export_args)

        self.define_variable("workload_exports", export_str)

        super()._define_commands(exec_graph, success_list)
