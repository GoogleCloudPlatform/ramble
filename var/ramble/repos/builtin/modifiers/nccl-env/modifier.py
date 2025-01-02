# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *
import ramble.util.env
import ramble.util.executable


class NcclEnv(BasicModifier):
    """Define a modifier for configuring NCCL based environment variables

    NCCL is the NVIDIA Collective Communications Library, which provides
    inter-GPU communication primitives that are topology-aware and can easily
    be integrated into applications.

    This modifier presents variables that can be use to configure and
    parameterize aspects of NCCL's behavior. The available parameters are
    documented in more details here:
    https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html

    Any variable who's value is an empty string will not be define in the
    resulting execution script.
    """

    name = "nccl-env"

    tags("gpu", "communication-performance")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode")
    default_mode("standard")

    modifier_variable(
        "nccl_socket_ifname",
        default="",
        description="Specification of which IP interfaces to use for communication",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_socket_family",
        default="",
        description="Allows users to force IPv4 or IPv6 interfaces",
        values=["AF_INET", "AF_INET6"],
        modes=["standard"],
    )

    modifier_variable(
        "nccl_socket_nthreads",
        default="",
        description="Specification of number of CPU helper threads used per network connection.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_nsocks_perthread",
        default="",
        description="Specification of number of sockets opened by each helper thread.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_cross_nic",
        default="",
        values=[0, 1, 2],
        description="Controls whether NCCL should allow rings/trees to use different NICs.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_hca",
        default="",
        description="Specifies which RDMA interfaces to use for communication.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_timeout",
        default="",
        description="Controls the InfiniBand verbs timeout.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_retry_cnt",
        default="",
        description="Controls the InfiniBand retry count.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_gid_index",
        default="",
        description="Defines the Global ID index used in RoCE mode.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_addr_family",
        default="",
        values=["AF_INET", "AF_INET6"],
        description="Defines the IP address family associated to the InfiniBand GID.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_addr_range",
        default="",
        description="Defines the range of valid GIDs dynamically selected by NCCL.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_roce_version_num",
        default="",
        description="Defines the range of valid GIDs dynamically selected by NCCL.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_sl",
        default="",
        description="Defines the InfiniBand service level.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_tc",
        default="",
        description="Defines the InfiniBand traffic class field.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_return_async_events",
        default="",
        values=["0", "1"],
        description="IB Events are reported to the user as warnings. If enabled NCCL will also stop IB communications upon fatal IB async events.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_oob_net_enable",
        default="",
        values=["0", "1"],
        description="Enables the use of NCCL net for out-of-band communications.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_oob_net_ifname",
        default="",
        description="Filters interfaces to be used by NCCL for out-of-band communications.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_uid_stagger_threshold",
        default="",
        description="Triggers staggering of communications between NCCL ranks and the ncclUniqueId in order to avoid overflowing the ncclUniqueId.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_uid_stagger_rate",
        default="",
        description="Defines the message rate targeted when staggering the communications between NCCL ranks and the ncclUniqueId.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_uid_stagger_rate",
        default="",
        description="Defines the message rate targeted when staggering the communications between NCCL ranks and the ncclUniqueId.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_net",
        default="",
        description="Forces NCCL to use a specific network.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_net_plugin",
        default="",
        description="Set to suffix string, or a library name to choose among multiple NCCL net plugins.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_tuner_plugin",
        default="",
        description="Set to suffix string, or a library name to choose among multiple NCCL tuner plugins.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_profiler_plugin",
        default="",
        description="Set to suffix string, or a library name to choose among multiple NCCL profiler plugins.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ignore_cpu_affinity",
        default="",
        values=["0", "1"],
        description="Causes NCCL to ignore the job's CPU affinity, and use the GPU affinity only.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_conf_file",
        default="",
        description="Allows user to specify a file with the static configuration.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_debug",
        default="",
        values=["VERSION", "WARN", "INFO", "TRACE"],
        description="Controls the debug information that is displayed from NCCL",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_debug_file",
        default="",
        description="Causes NCCL debugging information to be written to this file.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_debug_subsys",
        default="",
        description="Allows filtering of NCCL_DEBUG=INFO output based on subsystems.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_collnet_enable",
        default="",
        values=["0", "1"],
        description="Enable the use of the CollNet plugin",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_collnet_node_threshold",
        default="",
        description="Define the minimum number of nodes before CollNet will be enabled.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_topo_file",
        default="",
        description="Path to an XML file to load before detecting the topology.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_topo_dump_file",
        default="",
        description="Path to a file to dump the XML topology after detection.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_set_thread_name",
        default="",
        values=["0", "1"],
        description="Give more meaningful names to NCCL CPU threads to ease debugging and analysis.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_p2p_disable",
        default="",
        values=["0", "1"],
        description="Disables the peer to peer transport, which uses CUDA direct access between GPUs, using NVLink or PCI.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_p2p_level",
        default="",
        values=["LOC", "NVL", "PIX", "PXB", "PHB", "SYS"],
        description="Allows fine control when using the peer to peer transport between GPUs.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_p2p_direct_disable",
        default="",
        values=["0", "1"],
        description="Forbids NCCL to directly access user buffers through P2P between GPUs.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_shm_disable",
        default="",
        values=["0", "1"],
        description="Disables the Shared Memory transports.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_buffsize",
        default="",
        description="Controls the size (in bytes) of the buffer used by NCCL when communicated data between pairs of GPUs.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_nthreads",
        default="",
        description="Sets the number of CUDA threads per CUDA block. NCCL will launch one CUDA block per communicate channel.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_max_nchannels",
        default="",
        description="Limits the number of channels NCCL can use",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_min_nchannels",
        default="",
        description="Controls the minimum number of channels NCCL can use.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_checks_disable",
        default="",
        values=["0", "1"],
        description="Used to disable argument checks on each collective call",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_check_pointers",
        default="",
        values=["0", "1"],
        description="Enables checking of the CUDA memory pointers on each collective call.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_launch_mode",
        default="",
        values=["PARALLEL", "GROUP"],
        description="(Deprecated) Controls how NCCL launches CUDA kernels.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_disable",
        default="",
        values=["0", "1"],
        description="Prevents the IB/RoCE transport from being used by NCCL. Forces IP sockets.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_ar_threshold",
        default="",
        description="Threshold above which NCCL sends IB data in a separate message which can use adaptive routing.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_qps_per_connections",
        default="",
        description="Number of IB queue pairs to use for each connection between two ranks.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_split_data_on_qps",
        default="",
        values=["0", "1"],
        description="Controls how queue pairs are used when more than one are created.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_cuda_support",
        default="",
        values=["0", "1"],
        description="Force or disable the use of GPU Direct RDMA. 0 disables GPU Direct RDMA, 1 forces GPU Direct RDMA.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_pci_relaxed_ordering",
        default="",
        values=["0", "1"],
        description="Enables the use of Relaxed Ordering for IB Verbs.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_adaptive_routing",
        default="",
        values=["0", "1"],
        description="Enables the use of Adaptive Routing for IB Verbs.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_mem_sync_domain",
        default="",
        description="Sets the default memory sync domain for NCCL kernels.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_cumem_enable",
        default="",
        values=["0", "1"],
        description="NCCL uses CUDA cuMem* functions to allocate memory",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_cumem_host_enable",
        default="",
        values=["0", "1"],
        description="NCCL uses CUDA cuMem* functions to allocate host memory",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_net_gdr_level",
        default="",
        values=["LOC", "PIX", "PXB", "PHB", "SYS"],
        description="Allows fine control over when to use GPU Direct RDMA between a NIC and a GPU.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_net_gdr_read",
        default="",
        values=["0", "1"],
        description="Enables GPU Direct RDMA when sending data as long as the distance is wtihin the GDR Level distance.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_net_shared_buffers",
        default="",
        values=["0", "1"],
        description="Allows the use of shared buffers for inter-node point-to-point communication.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_net_shared_comms",
        default="",
        values=["0", "1"],
        description="Reuse the same connections in the context of PXN.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_single_ring_threshold",
        default="",
        description="Defines limit under which NCCL will only use one ring",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ll_threshold",
        default="",
        description="Defines limit under which NCCL will only use low-latency algorithms.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_tree_threshold",
        default="",
        description="Defines limit under which NCCL will only use tree algorithms instead of rings.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_algo",
        default="",
        values=[
            "Tree",
            "Ring",
            "Collnet",
            "CollnetDirect",
            "CollnetChain",
            "NVLS",
        ],
        description="Comma-separated list of algorithms NCCL should use",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_proto",
        default="",
        values=["LL", "LL128", "Simple"],
        description="(Use is Discouraged) Defines which protocol NCCL will use.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_nvb_disable",
        default="",
        values=["0", "1"],
        description="Disable intra-node communication through NVLink via an intermediate GPU.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_pxn_disable",
        default="",
        values=["0", "1"],
        description="Disable inter-node communication using a non-local NIC, using NVLink and an intermediate GPU.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_p2p_pxn_level",
        default="",
        description="Control in which cases PXN is used for send/receive operations.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_runtime_connect",
        default="",
        values=["0", "1"],
        description="Dynamically connect peers during runtime instead of init stage.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_local_register",
        default="",
        values=["0", "1"],
        description="Enable user local buffer registration when users explicitly call ncclCommRegister.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_set_stack_size",
        default="",
        values=["0", "1"],
        description="Set CUDA kernel stack size to the maximum stack size amongst all NCCL kernels.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_graph_mixing_support",
        default="",
        values=["0", "1"],
        description="Controls support for multiple outstanding NCCL calls.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_dmabuf_enable",
        default="",
        values=["0", "1"],
        description="Enable GPU Direct RDMA buffer registration using the Linux dma-buf subsystem.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_p2p_net_chunksize",
        default="",
        description="Controls the size of messages sent through the network for ncclSend/ncclRecv operations.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_p2p_ll_threshold",
        default="",
        description="Set the maximum message size that NCCL will use the LL protocol for P2P operations.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_alloc_p2p_net_ll_buffers",
        default="",
        values=["0", "1"],
        description="Instructs communicators to allocated dedicated LL buffers for all P2P network connections.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_comm_blocking",
        default="",
        values=["0", "1"],
        description="Controls whether NCCL calls are allowed to block or not.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_cga_cluster_size",
        default="",
        values=["0", "1", "2", "3", "4", "5", "6", "7", "8"],
        description="Set CUDA Cooperative Group Array cluster size.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_max_ctas",
        default="",
        description="Set the maximum number of CTAs that NCCL should use.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_min_ctas",
        default="",
        description="Set the minimal number of CTAs that NCCL should use.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_nvls_enable",
        default="",
        description="Enable the use of NVLink SHARP.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_ib_merge_nics",
        default="",
        values=["0", "1"],
        description="Enable NCCL to combine dual-port IB NICs into a single logical network device.",
        modes=["standard"],
    )

    modifier_variable(
        "nccl_mnnvl_enable",
        default="",
        values=["0", "1"],
        description="Enable NCCL to use Multi-Node NVLink when available.",
        modes=["standard"],
    )

    def __init__(self, file_path):
        super().__init__(file_path)
        self._applied = False

    def generate_env_var_dict(self, app_inst):
        env_var_set = {}
        set_env_vars = {}

        for var_name in self.mode_variables().keys():
            val = app_inst.expander.expand_var_name(var_name)
            if val:
                set_env_vars[var_name.upper()] = val

        if set_env_vars:
            env_var_set["set"] = set_env_vars

        return env_var_set

    executable_modifier("define_nccl_env_vars")

    def define_nccl_env_vars(self, executable_name, executable, app_inst=None):
        pre_cmds = []
        post_cmds = []
        if self._applied:
            return pre_cmds, post_cmds

        workload = app_inst.workloads[app_inst.expander.workload_name]

        # Apply before the first executable from the workload
        if executable_name == workload.executables[0]:
            self._applied = True

            action_funcs = ramble.util.env.action_funcs
            shell = ramble.config.get("config:shell")
            env_var_dict = self.generate_env_var_dict(app_inst)
            env_var_cmds = []
            for action, conf in env_var_dict.items():
                (env_cmds, _) = action_funcs[action](conf, set(), shell=shell)

                for cmd in env_cmds:
                    if cmd:
                        env_var_cmds.append(cmd)

            pre_cmds.append(
                ramble.util.executable.CommandExecutable(
                    "nccl_env_vars",
                    template=env_var_cmds,
                    mpi=False,
                    redirect="",
                    output_capture="",
                )
            )

        return pre_cmds, post_cmds
