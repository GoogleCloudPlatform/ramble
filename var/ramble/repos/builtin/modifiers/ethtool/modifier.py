# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class Ethtool(BasicModifier):
    """Define a modifier for network configuration.

    This modifier queries for common settings as well as
    supporting configuration of the network interface.

    Example usage:

    ```yaml
    ramble:
      variables:
        mpi_command: ''
        batch_submit: 'sbatch {execute_experiment}'
        hostlist: "${SLURM_JOB_NODELIST}"
        processes_per_node: 1
      applications:
        hostname:
          workloads:
            local:
              experiments:
                test:
                  variables:
                    n_nodes: 2
                    new_mtu: 4096
                    channel_setting: 'rx 8 tx 8'
                    coalesce_setting: 'rx-usecs 20 tx-usecs 20'
      modifiers:
      - name: ethtool
    ```
    """

    name = "ethtool"

    tags("system-info", "sysinfo", "platform-info")

    maintainers("rfbgo", "linsword13")

    mode("standard", description="Standard execution mode")

    modifier_variable(
        "new_mtu",
        default="",
        description="When set, this mtu will be applied to all defined in {hostlist}",
        mode="standard",
    )

    modifier_variable(
        "channel_setting",
        default="",
        description="When set, this will be applied to `ethtool -L`",
        mode="standard",
    )

    modifier_variable(
        "coalesce_setting",
        default="",
        description="When set, this will be applied to `ethtool -C`",
        mode="standard",
    )

    software_spec("pdsh", pkg_spec="pdsh", package_manager="spack*")

    register_builtin("run_ethtool")

    def run_ethtool(self):
        cmds = [
            # TODO: extend to support multiple vNICs
            "eth_dev=$(ip --br l | awk '$1 !~ /^lo/ { print $1 }' | head -n1)",
        ]

        def check_hostlist():
            if self.expander.expand_var("{hostlist}") == "{hostlist}":
                logger.die('Required variable "hostlist" is not defined.')

        new_mtu = self.expander.expand_var_name("new_mtu", typed=True)
        if isinstance(new_mtu, int) and new_mtu > 0:
            check_hostlist()
            cmds.append(
                "pdsh -R ssh -N -w {hostlist} "
                "sudo ip link set mtu {new_mtu} ${eth_dev} >> {log_file} 2>&1"
            )
        channel_setting = self.expander.expand_var_name("channel_setting")
        if channel_setting:
            check_hostlist()
            cmds.append(
                "pdsh -R ssh -N -w {hostlist} "
                f"sudo ethtool -L ${{eth_dev}} {channel_setting} >> {{log_file}} 2>&1"
            )
        coalesce_setting = self.expander.expand_var_name("coalesce_setting")
        if coalesce_setting:
            check_hostlist()
            cmds.append(
                "pdsh -R ssh -N -w {hostlist} "
                f"sudo ethtool -C ${{eth_dev}} {coalesce_setting} >> {{log_file}} 2>&1"
            )
        queries = [
            'echo "net_dev: $eth_dev" > {experiment_run_dir}/ethtool_out',
            # driver
            "ethtool -i $eth_dev >> {experiment_run_dir}/ethtool_out",
            # channel settings
            "ethtool -l $eth_dev >> {experiment_run_dir}/ethtool_out",
            # coalesce settings
            "ethtool -c $eth_dev >> {experiment_run_dir}/ethtool_out",
            "eth_mtu=$(cat /sys/class/net/${eth_dev}/mtu)",
            'echo "net_dev_mtu: $eth_mtu" >> {experiment_run_dir}/ethtool_out',
        ]
        cmds.extend(queries)
        return cmds

    # Sample output:
    # driver: gve
    # version: 1.3.1
    # firmware-version:
    # expansion-rom-version:
    # bus-info: 0000:00:04.0
    # supports-statistics: yes
    # supports-test: no
    # supports-eeprom-access: no
    # supports-register-dump: no
    # supports-priv-flags: yes
    figure_of_merit(
        "driver",
        fom_regex=r"driver: (?P<driver>.*)",
        log_file="{experiment_run_dir}/ethtool_out",
        group_name="driver",
        units="",
    )
    figure_of_merit(
        "version",
        fom_regex=r"version: (?P<version>.*)",
        log_file="{experiment_run_dir}/ethtool_out",
        group_name="version",
        units="",
    )

    figure_of_merit(
        "net_dev",
        fom_regex=r"net_dev: (?P<net_dev>.*)",
        log_file="{experiment_run_dir}/ethtool_out",
        group_name="net_dev",
        units="",
    )

    figure_of_merit(
        "net_dev_mtu",
        fom_regex=r"net_dev_mtu: (?P<net_dev_mtu>\d+)",
        log_file="{experiment_run_dir}/ethtool_out",
        group_name="net_dev_mtu",
        units="bytes",
    )

    figure_of_merit_context(
        "config",
        regex=r"(?P<config_name>(Pre-set|Current).*):",
        output_format="{config_name}",
    )

    for metric in ["RX", "TX", "Combined"]:
        figure_of_merit(
            metric,
            # When a channel setting is not available, it gives out "n/a".
            # Match only digits to avoid capturing the unsupported metrics.
            fom_regex=rf"{metric}:\s*(?P<count>\d+)",
            log_file="{experiment_run_dir}/ethtool_out",
            group_name="count",
            units="",
            contexts=["config"],
        )

    # FOMs on coalesce options
    figure_of_merit(
        "adaptive_rx",
        # both adaptive rx and tx can only be on/off
        fom_regex=r"Adaptive RX:\s*(?P<adaptive_rx>off|on)",
        log_file="{experiment_run_dir}/ethtool_out",
        group_name="adaptive_rx",
        units="",
    )

    figure_of_merit(
        "adaptive_tx",
        fom_regex=r"Adaptive RX:.*TX:\s*(?P<adaptive_tx>off|on)",
        log_file="{experiment_run_dir}/ethtool_out",
        group_name="adaptive_tx",
        units="",
    )

    # All these options should output either number or n/a, the latter is ignored.
    coalesce_options = [
        "stats-block-usecs",
        "sample-interval",
        "pkt-rate-low",
        "pkt-rate-high",
        "rx-usecs",
        "rx-frames",
        "rx-usecs-irq",
        "rx-frames-irq",
        "tx-usecs",
        "tx-frames",
        "tx-usecs-irq",
        "tx-frames-irq",
        "rx-usecs-low",
        "rx-frame-low",
        "tx-usecs-low",
        "tx-frame-low",
        "rx-usecs-high",
        "rx-frame-high",
        "tx-usecs-high",
        "tx-frame-high",
    ]

    for opt in coalesce_options:
        figure_of_merit(
            opt,
            fom_regex=rf"{opt}:\s*(?P<metric>\d+)",
            log_file="{experiment_run_dir}/ethtool_out",
            group_name="metric",
            units="",
        )
