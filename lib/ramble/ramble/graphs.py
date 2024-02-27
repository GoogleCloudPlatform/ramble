# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import enum
import graphlib

import ramble.error
import ramble.util.graph

from ramble.util.logger import logger


class AttributeGraph(object):

    node_type = 'object'

    def __init__(self, obj_inst):
        self._obj_inst = obj_inst
        self.node_definitions = {}
        self.adj_list = {}
        self._prepared = False
        self._sorted = None

    def _make_editable(self):
        """Make this graph editable, and remove any defined ordering"""
        if self._prepared:
            del self._sorted
            self._sorted = None
            self._prepared = False

    def update_graph(self, node, dep_nodes=[], internal_order=False):
        """Update the graph with a new node and / or new dependencies.

        Given a node, and list of dependencies, define new edges in the
        graph. If the node is new, also construct a new phase node.

        Args:
            node (GraphNode): Node to inject or modify
            dep_nodes (list(GraphNode)): List of nodes that are dependencies
            internal_order (Boolean): True to process internal dependencies,
                                      False to skip

        """

        self._make_editable()
        self.add_node(node)
        self.define_edges(node, dep_nodes, internal_order=internal_order)

    def add_node(self, node):
        """Add a node to the graph

        Args:
            node (GraphNode): Node to add into graph
        """

        self._make_editable()

        if node.key not in self.node_definitions:
            self.node_definitions[node.key] = node

        if node not in self.adj_list:
            self.adj_list[node] = set()

    def define_edges(self, node, dep_nodes=[], internal_order=False):
        """Define graph edges

        Process dependencies, and internal orderings (inside the node object)
        to define new graph edges.

        Args:
            node (GraphNode): Node to inject or modify
            dep_nodes (list(GraphNode)): List of nodes that are dependencies
            internal_order (Boolean): True to process internal dependencies,
                                     False to skip
        """

        for dep in dep_nodes:
            if dep.key not in self.node_definitions:
                self.node_definitions[dep.key] = dep
                self.adj_list[dep] = set()
            self.adj_list[node].add(dep)

        if internal_order:
            for dep in node._order_after:
                dep_node = self.node_definitions[dep]
                self.adj_list[node].add(dep_node)

            for dep in node._order_before:
                dep_node = self.node_definitions[dep]
                self.adj_list[dep_node].add(node)

    def walk(self):
        """Walk the graph in topological ordering and yield each node.

        Construct a topological ordering of the current graph, walk it, and
        yield each node one by one.

        Yields:
            node (GraphNode): Each node in the graph
        """
        if not self._prepared:
            sorter = graphlib.TopologicalSorter(self.adj_list)
            try:
                self._sorted = tuple(sorter.static_order())
            except graphlib.CycleError as e:
                try:
                    exp_name = self._obj_inst.expander.experiment_namespace
                except AttributeError:
                    exp_name = self._obj_inst.name
                raise GraphCycleError(f'In experiment {exp_name} a cycle was detected '
                                      f'when processing the {self.node_type} graph.\n'
                                      + str(e))
            self._prepared = True

        for node in self._sorted:
            yield node

    def get_node(self, key):
        """Given a key, return the node containing this key

        Args:
            key (str): Name of key to find in the graph

        Returns:
            (GraphNode): Node representing the key requested. Returns None if
                         the key isn't found.
        """
        for node in self.walk():
            if node.key == key:
                return node
        return None


class PhaseGraph(AttributeGraph):

    node_type = 'phase'

    def __init__(self, phase_definitions, obj_inst):
        """Construct a phase graph for a pipeline

        Parse a single pipeline's phase definitions, and build an adjacency
        list from this. Using the graph utiltites, construct a topological
        sorting of the graph.

        Args:
            phase_definitions (dict): Definitions of phases. Should be of the
                                      format {'phase_name': GraphNode}
            obj_inst (obj): Object instance to extract phase functions from
        """

        super().__init__(obj_inst)

        # Define all graph nodes
        for phase_node in phase_definitions.values():
            if phase_node.obj_inst is None:
                phase_node.obj_inst = obj_inst

            if phase_node.attribute is None:
                phase_func = getattr(obj_inst, f'_{phase_node.key}')
                phase_node.set_attribute(phase_func)

            self.add_node(phase_node)

        # Define graph edges
        for phase_node in phase_definitions.values():
            self.define_edges(phase_node, internal_order=True)

    def add_node(self, node, obj_inst=None):
        """Add a new phase node to the graph

        Extract the phase function from the object instance, and inject a new node into the graph.

        Args:
            node (GraphNode): Phase node to add into graph
            obj_inst (Object): Object that owns the phase
        """

        func_obj = obj_inst
        if func_obj is None:
            func_obj = self._obj_inst

        phase_func = getattr(func_obj, f'_{node.key}')
        node.set_attribute(phase_func)

        super().add_node(node)

    def update_graph(self, phase_name, dependencies=[],
                     internal_order=False, obj_inst=None):
        """Update the graph with a new phase and / or new dependencies.

        Given a phase name, and list of dependencies, define new edges in the
        graph. If the phase is new, also construct a new phase node.

        Args:
            phase_name (str): Name of the phase to inject or modify
            dependencies (list(str)): List of phase names to inject dependencies on
            internal_order (Boolean): True to process internal dependencies,
                                      False to skip
            obj_inst (object): Application or modifier instance to extract phase function from
        """
        if self._prepared:
            del self._sorted
            self._sorted = None
            self._prepared = False

        if phase_name not in self.node_definitions:
            phase_node = ramble.util.graph.GraphNode(phase_name)
            self.add_node(phase_node, obj_inst)

        phase_node = self.node_definitions[phase_name]

        dep_nodes = []
        for dep in dependencies:
            if dep not in self.node_definitions:
                dep_node = ramble.util.graph.GraphNode(dep)
                self.add_node(dep_node, obj_inst)

            dep_node = self.node_definitions[dep]
            dep_nodes.append(dep_node)

        super().define_edges(phase_node, dep_nodes)


class ExecutableGraph(AttributeGraph):
    """Graph that handles command executables and builtins"""

    node_type = 'command executable'
    supported_injection_orders = enum.Enum('supported_injection_orders', ['before', 'after'])

    def __init__(self, exec_order, executables, builtin_groups, obj_inst):
        """Construct a new ExecutableGraph

        Executable graphs have node attributes that are either of type
        CommandExecutable, or are a function pointer to a builtin.

        Args:
            exec_order (list(str)): List of executable names in execution order
            executables (dict): Dictionary of executable definitions.
                                Keys are executable names, values are CommandExecutables
            builtins (dict): Dictionary containing definitions of builtins. Keys are names
                             values are configurations of builtins.
            modifier_builtins (dict): Dictionary containing definitions of modifier builtins.
                                      Keys are names values are configurations of builtins.
                                      Modifier builtins are inserted between application builtins
                                      and executables.
            obj_inst (object): Object instance to extract attributes from (when necessary)
        """
        super().__init__(obj_inst)
        self._builtin_dependencies = {}

        # Define nodes for executable
        for exec_name, cmd_exec in executables.items():
            exec_node = ramble.util.graph.GraphNode(exec_name, cmd_exec, obj_inst=obj_inst)
            self.node_definitions[exec_name] = exec_node
            if exec_name in exec_order:
                super().update_graph(exec_node)

        # Define nodes for builtins
        for builtins in builtin_groups:
            for builtin, blt_conf in builtins.items():
                self._builtin_dependencies[builtin] = blt_conf['depends_on'].copy()
                exec_node = ramble.util.graph.GraphNode(builtin, blt_conf['function'],
                                                        obj_inst=obj_inst)
                self.node_definitions[builtin] = exec_node

        dep_exec = None
        for exec_name in exec_order:
            if dep_exec is not None:
                exec_node = self.node_definitions[exec_name]
                dep_node = self.node_definitions[dep_exec]
                super().update_graph(exec_node, [dep_node])
            dep_exec = exec_name

        head_node = None
        tail_node = None
        for node in self.walk():
            if head_node is None:
                head_node = node
            tail_node = node

        tail_prepend_builtin = None
        tail_append_builtin = None

        # Add (missing) required builtins
        for builtins in builtin_groups:
            for builtin, blt_conf in builtins.items():
                if blt_conf['required'] and self.get_node(builtin) is None:
                    blt_node = self.node_definitions[builtin]
                    super().update_graph(blt_node)

                    if blt_conf['injection_method'] == 'prepend':
                        if head_node is not None:
                            super().update_graph(head_node, [blt_node])

                        if tail_prepend_builtin is not None:
                            super().update_graph(blt_node, [tail_prepend_builtin])
                        tail_prepend_builtin = blt_node
                    elif blt_conf['injection_method'] == 'append':
                        if tail_node is not None:
                            super().update_graph(blt_node, [tail_node])

                        if tail_append_builtin is not None:
                            super().update_graph(blt_node, [tail_append_builtin])
                        tail_append_builtin = blt_node

                    if blt_conf['depends_on']:
                        deps = []
                        for dep in blt_conf['depends_on']:
                            dep_node = self.node_definitions[dep]
                            super().update_graph(dep_node)
                            deps.append(dep_node)

                        exec_node = self.node_definitions[builtin]
                        super().update_graph(exec_node, deps)

    def inject_executable(self, exec_name, injection_order, relative):
        """Inject an executable into the graph

        Args:
            exec_name (str): Name of executable to inject
            injection_order (str): Order for injection. Can be 'before' or 'after'
            relative (str): Name of executable to inject relative to. Can be
                            None to inject relative to the whole set of executables.
        """
        # Order can be 'before' or 'after.
        # If `relative_to` is not set, then before adds to be the beginning of the list
        #                  and after (default) adds to the end of the list
        # If `relative_to` IS set, then before adds before the first instance of
        #                  the executable in the list
        #                  and after (default) adds after the last instance of the
        #                  executable in the list
        # If `relative_to` is set, and the executable name is not found, raise a fatal error.

        exec_node = self.node_definitions[exec_name]
        cur_exec_order = []
        for node in self.walk():
            cur_exec_order.append(node)

        exp_name = self._obj_inst.expander.experiment_namespace
        order = self.supported_injection_orders.after
        if injection_order is not None:
            if not hasattr(self.supported_injection_orders, injection_order):
                logger.die('In experiment '
                           f'"{exp_name}" '
                           f'injection order of executable "{exec_name}" is set to an '
                           f'invalid value of "{injection_order}".\n'
                           f'Valid values are {self.supported_injection_orders}.')
            order = getattr(self.supported_injection_orders, injection_order)

        if exec_name not in self.node_definitions:
            logger.die('In experiment '
                       f'"{exp_name}" '
                       f'attempting to inject a non existing executable "{exec_name}".')

        if relative is not None:
            relative_error = False
            if relative not in self.node_definitions:
                relative_error = True

            relative_node = self.node_definitions[relative]
            if relative_node not in cur_exec_order:
                relative_error = True

            if relative_error:
                logger.die('In experiment '
                           f'"{exp_name}" '
                           f'attempting to inject executable "{exec_name}" '
                           f'relative to a non existing executable "{relative}".')

        if relative is not None and relative not in self.node_definitions:
            relative_node = self.node_definitions[relative]
            if relative_node not in cur_exec_order:
                logger.die('In experiment '
                           f'"{exp_name}" '
                           f'attempting to inject executable "{exec_name}" '
                           f'relative to a non existing executable "{relative}".')

        # If relative is none, determine head and tail nodes to inject properly
        if relative is None:
            head_node = cur_exec_order[0]
            tail_node = cur_exec_order[-1]

            super().update_graph(exec_node)
            if order == self.supported_injection_orders.before:
                super().update_graph(head_node, [exec_node])
            elif order == self.supported_injection_orders.after:
                super().update_graph(exec_node, [tail_node])
        else:
            relative_node = self.node_definitions[relative]
            order_index = cur_exec_order.index(relative_node)

            if order == self.supported_injection_orders.before:
                super().update_graph(relative_node, [exec_node])
                if order_index > 0:
                    super().update_graph(exec_node, [cur_exec_order[order_index - 1]])
            elif order == self.supported_injection_orders.after:
                super().update_graph(exec_node, [relative_node])
                if order_index < len(cur_exec_order) - 1:
                    super().update_graph(cur_exec_order[order_index + 1], [exec_node])

        # If exec_name is a builtin, inject edges to it's dependencies
        if exec_name in self._builtin_dependencies:
            dep_nodes = []
            for dep in self._builtin_dependencies[exec_name]:
                dep_node = self.node_definitions[dep]
                dep_nodes.append(dep_node)
            super().update_graph(exec_node, dep_nodes)


class GraphError(ramble.error.RambleError):
    """
    Exception raised with errors in a graph type
    """


class GraphCycleError(GraphError):
    """
    Exception raised when a cycle is detected in a graph
    """
