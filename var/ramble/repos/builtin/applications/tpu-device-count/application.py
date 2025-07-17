from ramble.appkit import *


class TpuDeviceCount(ExecutableApplication):
    """This is an example application that runs on TPUs"""

    name = "tpu-device-count"

    tags("test-app")

    parameter("device_count", default=1, description="Expected number of TPU devices")

    software_spec(
        "libtpu",
        pkg_spec="-f https://storage.googleapis.com/jax-releases/libtpu_releases.html",
        package_manager="pip",
    )

    software_spec(
        "jax",
        pkg_spec="jax[tpu]",
        package_manager="pip",
    )

    required_package("jax", package_manager="pip")

    executable(
        "count_devices",
        'python -c \'import jax; print("TPU cores:", jax.device_count())\'',
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    workload("count_devices", executable="count_devices")

    figure_of_merit(
        "TPU Cores",
        fom_regex=r"TPU cores: (?P<cores>[0-9]+)\s*",
        group_name="cores",
        units="",
    )

    success_criteria(
        "TPU_cores_found",
        mode="fom_comparison",
        fom_name="TPU Cores",
        formula="{value} == {device_count}",
    )
