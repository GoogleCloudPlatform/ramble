# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *
from ramble.expander import Expander


class UfsWeatherModel(ExecutableApplication):
    """Define FV3 application via ufs-weather-model"""

    name = "ufs-weather-model"

    maintainers("rfbgo")

    tags("weather", "nwp", "climate-modeling")

    with when("package_manager_family=spack"):
        define_compiler("gcc9", pkg_spec="gcc@9.3.0")

        software_spec(
            "ompi415",
            pkg_spec="openmpi@4.1.5",
            compiler="gcc9",
        )

        software_spec(
            "python39",
            pkg_spec="python@3.9.15",
            compiler="gcc9",
        )
        software_spec(
            "esmf",
            pkg_spec="esmf@8.0.1",
            compiler="gcc9",
        )

        software_spec(
            "ufs-weather-model",
            pkg_spec="ufs-weather-model@2.0.0 +openmp",
            compiler="gcc9",
        )

        required_package("ufs-weather-model")

    input_file(
        "simple_test_case",
        url="https://ftp.emc.ncep.noaa.gov/EIB/UFS/simple-test-case.tar.gz",
        sha256="c713ecb208abcff9a7ec74d7991915d842f85a53b5771afa6b9c57c27651aaeb",
        description="Simple test case for ufs-weather-model",
    )

    executable("execute", "ufs_weather_model", use_mpi=True)

    stage_files(
        name="stage-input",
        src="{input_path}/*",
        dst="{experiment_run_dir}",
    )

    workload(
        "simple_test_case",
        executables=["stage-input", "execute"],
        input="simple_test_case",
    )

    base_url = "https://noaa-ufs-regtests-pds.s3.amazonaws.com"
    version = "develop-20250701"
    wl_name = "control_c48_intel"
    restart_prefix = "RESTART"
    main_url = base_url + "/" + version + "/" + wl_name
    restart_url = main_url + "/" + restart_prefix

    main_files = ["atmf000.nc", "atmf024.nc", "sfcf000.nc", "sfcf024.nc"]
    main_files_sha = [
        "fa32b804de5200bc7f6052b57ee4d03352e6c9e2d4cbb22dbd919212cccbf061",
        "c59b16956dd1aea752663198f497525a355d439a6e898adac0aaea73f5012eef",
        "2fa515fe0e77185208b9ad2574bd08b0d8b79f201275c9296208908073a5ec84",
        "d17c318797bb26d09f0b041e0f460003e3e8384c0a52a6941321fbafa7d84f46",
    ]

    restart_files = [
        (
            "20210323.060000.coupler.res",
            "2f73114a990b602c202efc9fe71a020d34a67e61e4c40ae28920a632c29ca26c",
        ),
        (
            "20210323.060000.fv_core.res.nc",
            "98714d2513045f357487ad12980b2ccd74bf57df3dc1d8c74495d33494bee8be",
        ),
        (
            "20210323.060000.fv_core.res.tile1.nc",
            "013f8ec74963c5ea4921235d4ec05316d8606c7c2001c897113f45997325f0ad",
        ),
        (
            "20210323.060000.fv_core.res.tile2.nc",
            "a9849f908fa862c5c16bc70fe7b57826199e0d32f157e24241ed4bf11442d3ea",
        ),
        (
            "20210323.060000.fv_core.res.tile3.nc",
            "3d8b8225cfcf8897424acf1ce039e277409d190a3f3da50b6aaafc194dff46dc",
        ),
        (
            "20210323.060000.fv_core.res.tile4.nc",
            "eb048878e75dd2d2f83b65b79788603010fd54717cc174fc956a499445db9dfb",
        ),
        (
            "20210323.060000.fv_core.res.tile5.nc",
            "692963c5b3daf2ea19e39d4bec763afbd129d07aaf140c2087b4dd6ecaf91430",
        ),
        (
            "20210323.060000.fv_core.res.tile6.nc",
            "19748b5231dc01166c53928344cc87e457d669259a3d0a78f94e61183323f5c2",
        ),
        (
            "20210323.060000.fv_srf_wnd.res.tile1.nc",
            "4f35ed990e93ac9a70ad07aa606c4f8c6adfc957d63674b15fb08760dd6308d4",
        ),
        (
            "20210323.060000.fv_srf_wnd.res.tile2.nc",
            "14229906f6c9094d0721ccd2641ae306fdc9b10cb9ba2dd3ccbed360ceb736cc",
        ),
        (
            "20210323.060000.fv_srf_wnd.res.tile3.nc",
            "a05ac8fe72d07f3d994566e56f46068e5adb4f238257e2f1cb04f39a07e42d8b",
        ),
        (
            "20210323.060000.fv_srf_wnd.res.tile4.nc",
            "57215f37b9ba10c036f8f49b0cdc6bd85bf648eba7416fe46b2a72171b3ef744",
        ),
        (
            "20210323.060000.fv_srf_wnd.res.tile5.nc",
            "3b10e57e0080a14c50ef8c3c49b2a199acb16c3ff0b4a1248c521c66e9c4efd4",
        ),
        (
            "20210323.060000.fv_srf_wnd.res.tile6.nc",
            "8b9b9ef37f577862ff92316292504b4d055978aef1650d30e4eabeb252becf0e",
        ),
        (
            "20210323.060000.fv_tracer.res.tile1.nc",
            "ce145c7810fd9ce7a489b533a1462162c6432e2ef8e60e462bd17d16b0a1a74b",
        ),
        (
            "20210323.060000.fv_tracer.res.tile2.nc",
            "e099759772ce64a0d5ac472046d286d1181b902a5ce135789d6a7335d04985eb",
        ),
        (
            "20210323.060000.fv_tracer.res.tile3.nc",
            "2cd0470a4f5545cc51df86241f407032404ddfc83d8589c40820d77c731c64ef",
        ),
        (
            "20210323.060000.fv_tracer.res.tile4.nc",
            "e8f5238a902d89bbfc3ad00f939673749b754bacf58389f28947cacb6a2bf882",
        ),
        (
            "20210323.060000.fv_tracer.res.tile5.nc",
            "5f38e8564fa43464ddadad3864e6121c60fc2077961ad9974157d6a91216b0cc",
        ),
        (
            "20210323.060000.fv_tracer.res.tile6.nc",
            "5bc3748c2f72b4b2d940228a98f970495de7af898b5c2253a1ee422b6880368a",
        ),
        (
            "20210323.060000.phy_data.tile1.nc",
            "fde6b8674e05c364be4c1c8086df234bf480873643be92a17962c39c07e12d11",
        ),
        (
            "20210323.060000.phy_data.tile2.nc",
            "766d7561ec70a678588432d447467d2b82aee0eb42ef7bba681246ff51def84a",
        ),
        (
            "20210323.060000.phy_data.tile3.nc",
            "36aa34ac23ef07f96791f8748589cac456bbbeb55efca8fd6a9da82e06b7110b",
        ),
        (
            "20210323.060000.phy_data.tile4.nc",
            "d9dd3fd6515d8bd4ea92349913e8f01d85611732ad32d578d7ec9108143de552",
        ),
        (
            "20210323.060000.phy_data.tile5.nc",
            "40a91ce667a79daef8721450b3640fec1fcb4d177885af1647dd30dddf44fe7a",
        ),
        (
            "20210323.060000.phy_data.tile6.nc",
            "f659825e2478893aa4104bbf3d661684250470928a2f5103f11c01aa3ce3d317",
        ),
        (
            "20210323.060000.sfc_data.tile1.nc",
            "3d3d008a30ac5ed70e275eb93f829bbc5d315ab9c93f074fa3a6be5ad9ce2643",
        ),
        (
            "20210323.060000.sfc_data.tile2.nc",
            "6398413548a294cad286d2a6c9e776662916d059475b8cfbd963c2e565af62f9",
        ),
        (
            "20210323.060000.sfc_data.tile3.nc",
            "7a84c61085d303f6c952b416c5dfa9e5565f3740bcd32b524b305128960f0362",
        ),
        (
            "20210323.060000.sfc_data.tile4.nc",
            "924461ebf533516638a79b5ee9c7135b246f58d91ed15b88bfd51008e953e7f7",
        ),
        (
            "20210323.060000.sfc_data.tile5.nc",
            "3aab6d3834c491636d22af9aa684aa0b237ef4eea4d59c10145dff105c5dd5ba",
        ),
        (
            "20210323.060000.sfc_data.tile6.nc",
            "c79e742c53f05291a036543c54dc54c5bacdb44d0412f76085e896813bcb68bd",
        ),
    ]
    restart_file_names = [f for f, sha in restart_files]

    for f, sha in zip(main_files, main_files_sha):
        input_file(
            f,
            url=main_url + "/" + f,
            sha256=sha,
            description="Part for c48_intel",
            expand=False,
        )
    for f, sha in restart_files:
        input_file(
            f,
            url=main_url + "/" + restart_prefix + "/" + f,
            target_dir="{workload_input_dir}" + os.sep + restart_prefix,
            sha256=sha,
            description="Restart Part for c48_intel",
            expand=False,
        )

    workload(
        "control_c48_intel",
        executables=["stage-input", "execute"],
        inputs=restart_file_names,
    )

    workload_variable(
        "input_path",
        default="{simple_test_case}",
        description="extracted simple-test-case tarfile path",
        workloads=["simple_test_case"],
    )
    workload_variable(
        "input_path",
        default="{workload_input_dir}",
        description="c48 input path",
        workloads=["control_c48_intel"],
    )

    log_str = os.path.join(
        Expander.expansion_str("experiment_run_dir"),
        Expander.expansion_str("experiment_name") + ".out",
    )

    figure_of_merit(
        "Total wall clock time",
        fom_regex=(
            r"^\s*The total amount of wall time\s+=\s+"
            r"(?P<walltime>[0-9]+\.[0-9]+)"
        ),
        group_name="walltime",
        log_file=log_str,
        units="s",
    )

    figure_of_merit(
        "Total user mode time",
        fom_regex=(
            r"^\s*The total amount of time in user mode\s+=\s+"
            r"(?P<usertime>[0-9]+\.[0-9]+)"
        ),
        group_name="usertime",
        log_file=log_str,
        units="s",
    )

    figure_of_merit(
        "Total sys mode time",
        fom_regex=(
            r"^\s*The total amount of time in sys mode\s+=\s+"
            r"(?P<systime>[0-9]+\.[0-9]+)"
        ),
        group_name="systime",
        log_file=log_str,
        units="s",
    )

    figure_of_merit(
        "Maximum resident set size",
        fom_regex=(
            r"^\s*The maximum resident set size.*?\s+=\s+"
            r"(?P<res_set_size>[0-9]+)"
        ),
        group_name="res_set_size",
        log_file=log_str,
        units="KB",
    )

    figure_of_merit(
        "Mean specific humidity above 75mb",
        fom_regex=(
            r"^\s*Mean specific humidity.*?=\s+"
            r"(?P<mean_sp_hum>[0-9]+\.[0-9]+)"
        ),
        group_name="mean_sp_hum",
        log_file=log_str,
        units="mg/kg",
    )

    figure_of_merit(
        "Total surface pressure",
        fom_regex=(
            r"^\s*Total surface pressure.*?=\s+"
            r"(?P<tot_surf_press>[0-9]+\.[0-9]+)"
        ),
        group_name="tot_surf_press",
        log_file=log_str,
        units="mb",
    )

    figure_of_merit(
        "mean dry surface pressure",
        fom_regex=(
            r"^\s*mean dry surface pressure.*?=\s+"
            r"(?P<mean_dry_surf_press>"
            r"[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*"
            r")"
        ),
        group_name="mean_dry_surf_press",
        log_file=log_str,
        units="mb",
    )

    figure_of_merit(
        "Total water vapor",
        fom_regex=(
            r"^\s*Total Water Vapor.*?=\s+"
            r"(?P<tot_h2o_vapor>"
            r"[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*"
            r")"
        ),
        group_name="tot_h2o_vapor",
        log_file=log_str,
        units="kg/m**2",
    )

    figure_of_merit(
        "Total cloud water",
        fom_regex=(
            r"^\s*Total cloud water.*?=\s+"
            r"(?P<tot_cloud_h2o>"
            r"[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*"
            r")"
        ),
        group_name="tot_cloud_h2o",
        log_file=log_str,
        units="kg/m**2",
    )

    figure_of_merit(
        "Total rain water",
        fom_regex=(
            r"^\s*Total rain water.*?=\s+"
            r"(?P<tot_rain_h2o>"
            r"[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*"
            r")"
        ),
        group_name="tot_rain_h2o",
        log_file=log_str,
        units="kg/m**2",
    )

    figure_of_merit(
        "Total snow",
        fom_regex=(
            r"^\s*Total snow.*?=\s+"
            r"(?P<tot_snow>"
            r"[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*"
            r")"
        ),
        group_name="tot_snow",
        log_file=log_str,
        units="kg/m**2",
    )

    figure_of_merit(
        "Total graupel",
        fom_regex=(
            r"^\s*Total graupel.*?=\s+"
            r"(?P<tot_graupel>"
            r"[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*"
            r")"
        ),
        group_name="tot_graupel",
        log_file=log_str,
        units="kg/m**2",
    )

    success_criteria(
        "program_ended",
        mode="string",
        match=r"^\s+PROGRAM.*?HAS ENDED\.",
        file=log_str,
    )
