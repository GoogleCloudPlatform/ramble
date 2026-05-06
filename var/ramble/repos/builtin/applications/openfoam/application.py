# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.openfoam import Openfoam as OpenfoamBase


class Openfoam(OpenfoamBase):
    """Define the Openfoam application"""

    name = "openfoam"

    maintainers("douglasjacobsen")

    version("2312", "Version 2312 of Openfoam", preferred=True)

    with when("package_manager_family=spack"):
        define_compiler("gcc14", pkg_spec="gcc@14.2.0")

        software_spec(
            "intel-mpi",
            pkg_spec="intel-oneapi-mpi@2021.17.2",
            compiler="gcc14",
        )

        software_spec(
            "openfoam-{application::openfoam::version}",
            pkg_spec="openfoam@{application::openfoam::version}",
            compiler="gcc14",
        )

        required_package("openfoam")

    executable(
        "surfaceFeatures",
        "surfaceFeatureExtract",
        use_mpi=False,
        redirect="{experiment_run_dir}/log.surfaceFeatures",
    )

    stage_files(name="stage_0", src="0.orig", dst="0")
    stage_files(
        name="stage_0",
        src="system/decomposeParDict.*",
        dst="system/decomposeParDict",
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
