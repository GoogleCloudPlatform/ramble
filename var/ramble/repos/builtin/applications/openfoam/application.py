# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

from ramble.app.builtin.openfoam_org import OpenfoamOrg


class Openfoam(OpenfoamOrg):
    """Define the Openfoam application"""

    name = "openfoam"

    maintainers("douglasjacobsen")

    software_spec("openfoam", spack_spec="openfoam@2312", compiler="gcc9")

    required_package("openfoam")

    executable(
        "surfaceFeatures",
        "surfaceFeatureExtract",
        use_mpi=False,
        redirect="{experiment_run_dir}/log.surfaceFeatures",
    )

    executable(
        "get_inputs",
        template=[
            "cp -Lr {input_path}/* {experiment_run_dir}/.",
            "mkdir -p constant/triSurface",
            "mkdir -p constant/geometry",
            "cp {geometry_path} constant/triSurface/.",
            "cp {geometry_path} constant/geometry/.",
            "cp system/decomposeParDict.* system/decomposeParDict",
            "ln -sf {experiment_run_dir}/0.orig {experiment_run_dir}/0",
        ],
        use_mpi=False,
    )

    workload_variable(
        "dict_delim",
        description="Delimiter for dictionary entries",
        default=".",
        workloads=["motorbike*"],
    )

    workload_variable(
        "coeffs_dict",
        description="Coeffs dictionary name",
        default="coeffs",
        workloads=["motorbike*"],
    )

    workload_variable(
        "export_variables",
        description="Comma separated list of all env-var names that need to be exported",
        default="PATH,LD_LIBRARY_PATH,FOAM_API,FOAM_APP,FOAM_APPBIN,FOAM_ETC,"
        + "FOAM_LIBBIN,FOAM_MPI,FOAM_RUN,FOAM_SITE_APPBIN,FOAM_SITE_LIBBIN,"
        + "FOAM_SOLVERS,FOAM_SRC,FOAM_TUTORIALS,FOAM_USER_APPBIN,"
        + "FOAM_USER_LIBBIN,FOAM_UTILITIES,LD_LIBRARY_PATH,PATH,"
        + "WM_ARCH,WM_COMPILER,WM_COMPILER_LIB_ARCH,WM_COMPILER_TYPE,"
        + "WM_COMPILE_OPTION,WM_DIR,WM_LABEL_OPTION,WM_LABEL_SIZE,"
        + "WM_MPLIB,WM_OPTIONS,WM_PRECISION_OPTION,WM_PROJECT,WM_PROJECT_DIR,"
        + "WM_PROJECT_USER_DIR,WM_PROJECT_VERSION,WM_THIRD_PARTY_DIR",
        workloads=["*"],
    )

    # TODO: Remove when base classes exist
    # Remove incorrect definitions from `openfoam-org`
    def __init__(self, file_path):
        super().__init__(file_path)
        del self.software_specs["openfoam-org"]
        del self.required_packages["openfoam-org"]
