# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


class GraphNode:
    """Class representing a node of a graph, where the node can have an
    attribute attached to it.

    This allows nodes to be added into a graph, have the topological order of
    the graph returned, and be able to refer to the attribute of the original
    node easily.
    """

    def __init__(self, key, attribute=None, obj_inst=None):
        """Construct a graph node

        Args:
            key: The key for the graph node. This is what will be used to sort the graph.
            attribute: A list of arbitrary attribute to keep associated with the key
        """
        self.key = key
        self.attribute = attribute
        self._order_before = []
        self._order_after = []
        self.obj_inst = obj_inst

    def set_attribute(self, attr):
        """Sets the attribute of a graph node

        Args:
            attr: An arbitrary attribute to attach to this node.
        """
        self.attribute = attr

    def order_before(self, key):
        """Adds information that this node should come before another node

        Args:
            key (str): Key of node that should come after this node.
        """

        self._order_before.append(key)

    def order_after(self, key):
        """Adds information that this node should come after another node

        Args:
            key (str): Key of node that should come before this node.
        """

        self._order_after.append(key)

    def __repr__(self):
        """Return a string representation of the node

        Returns:
            str: Text representation of the node
        """
        return f"{self.key}"

    def __str__(self):
        """Return a string representation of the node

        Returns:
            str: Text representation of the node
        """
        return f"{self.key}"

    def __hash__(self):
        """Hash a node based on it's key

        Returns:
            str: hash of the node's key
        """
        return hash(self.key)

    def __eq__(self, other):
        """Equivalence test of nodes

        Returns:
            bool: True if nodes keys are the same, False otherwise.
        """

        if not isinstance(other, GraphNode):
            return False

        return self.key == other.key
