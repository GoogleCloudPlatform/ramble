# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

from ramble.base_app.builtin.openfoam import Openfoam as OpenfoamBase


class OpenfoamOrg(OpenfoamBase):
    """Define the Openfoam-org application"""

    name = "openfoam-org"

    maintainers("douglasjacobsen")

    tags("cfd", "fluid", "dynamics")

    define_compiler("gcc9", pkg_spec="gcc@9.3.0", package_manager="spack*")

    software_spec(
        "impi2018", pkg_spec="intel-mpi@2018.4.274", package_manager="spack*"
    )

    software_spec(
        "openfoam-org",
        pkg_spec="openfoam-org@10",
        compiler="gcc9",
        package_manager="spack*",
    )

    required_package("openfoam-org", package_manager="spack*")

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
