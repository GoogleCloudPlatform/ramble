# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from collections.abc import Sequence
from enum import Enum
from typing import Any, Callable, Optional, Union

import ramble.error

reserved_variants = {
    "modifier",
    "package_manager",
    "package_manager_prefix",
    "version",
    "workflow_manager",
}

variant_types = Enum("variant_types", ["default", "experiment"])


class VariantSet:
    """A custom set for housing multiple types of variants, and encapsulating
    the logic of merging them together."""

    def __init__(self):
        self.default_variants = {}
        self.multi_value_variants = {}
        self.experiment_variants = {}
        self._set_cache = None

    def copy(self):
        new_set = VariantSet()

        set_attrs = ["default_variants", "experiment_variants"]
        for set_attr in set_attrs:
            src_attr_set = getattr(self, set_attr)
            dest_attr_set = getattr(new_set, set_attr)
            for name, variant in src_attr_set.items():
                dest_attr_set[name] = variant.copy()

        for name, var_list in self.multi_value_variants.items():
            new_set.multi_value_variants[name] = []
            for variant in var_list:
                new_set.multi_value_variants[name].append(variant.copy())

        return new_set

    def merge_default_variants(self, in_set):
        """Merge another variant set's default variants into this variant set.

        Args:
            in_set: VariantSet to merge into self
        """

        self._set_cache = None
        for name, variant in in_set.default_variants.items():
            if name not in self.default_variants:
                self.default_variants[name] = variant.copy()

    def merge_multi_value_variants(self, in_set):
        """Merge another variant set's multi value variants into this variant set.

        Args:
            in_set: VariantSet to merge into self
        """

        self._set_cache = None
        for name, variant_list in in_set.multi_value_variants.items():
            if name not in self.multi_value_variants:
                self.multi_value_variants[name] = set()
            for variant in variant_list:
                self.multi_value_variants[name].add(variant)

    def default_variant(
        self,
        name: str,
        default: Optional[Any] = None,
        description: str = "",
        values: Optional[Union[Sequence, Callable[[Any], bool]]] = None,
    ):
        """Define a new default variant within this set.

        Default variants are variants defined by directives in an object. These
        are used to define the defaults, and provide documentation for users.

        Args:
            name: Name of variant
            default: Default value of the variant
            description: Description of the variant, and what it's used for
            values: Set of valid values for the variant
        """

        self._define_variant(
            name,
            variant_type=variant_types.default,
            default=default,
            description=description,
            values=values,
        )

    def experiment_variant(self, name: str, value: Any):
        """Define a new experiment variant within this set.

        Experiment variants are variants defined within a workspace's configuration file.
        These are expected to be user defined values that will override the defaults of the object.

        Experiment variants should always be defined after default variants (as
        defaults come from object directives, and experiment variants come from
        yaml). As a result, we only define experiment variants that have a
        corresponding default variant with the same name.

        Args:
            name: Name of variant
            value: The value the variant should take.
        """
        if name in self.default_variants:
            if (
                self.default_variants[name].values
                and value not in self.default_variants[name].values
            ):
                raise RambleVariantError(
                    f"When defining variant {name} the value {value} is not valid.\n"
                    f"   Valid values include: {self.default_variants[name].values}"
                )

            self._define_variant(
                name,
                variant_type=variant_types.experiment,
                default=value,
                description=None,
                values=None,
            )
        elif name in reserved_variants:
            self._define_variant(
                name,
                variant_type=variant_types.experiment,
                default=value,
                description=None,
                values=None,
            )

    def multi_value_variant(self, name: str, value: Any):
        self._set_cache = None
        if name not in self.multi_value_variants:
            self.multi_value_variants[name] = set()

        self.multi_value_variants[name].add(Variant(name, default=value))

    def _define_variant(
        self,
        name: str,
        variant_type: int,
        default: Optional[Any] = None,
        description: str = "",
        values: Optional[Union[Sequence, Callable[[Any], bool]]] = None,
    ):
        """Define a variant within this set.

        This is an abstract method intended to construct a new default or
        experiment variant based on the calling signature.

        Args:
            name: Name of variant
            variant_type: Type of variant (as defined in the variant_types enum) of this variant
            default: Default value of the variant
            description: Description of the variant, and what it's used for
            values: Set of valid values for the variant
        """

        self._set_cache = None
        variant_dict = None
        if variant_type == variant_types.experiment:
            variant_dict = self.experiment_variants

        elif variant_type == variant_types.default:
            variant_dict = self.default_variants

        else:
            raise RambleVariantError(
                f"Cannot define variant {name} with unknown variant type of {variant_type}"
            )

        variant_dict[name] = Variant(
            name=name, default=default, description=description, values=values
        )

    def value(self, name: str):
        """Extract the value of a variant by name

        Args:
            name: Name of variant to determine value for

        Returns:
            Value of variant if found, otherwise None.
        """

        if name in self.experiment_variants:
            return self.experiment_variants[name].default

        if name in self.default_variants:
            return self.default_variants[name].default

        return None

    def as_set(self):
        """Construct a set of definitions for this variant set

        The set of variant definitions will be used to determine if a when
        clause is valid or not.

        Returns:
            set: A set consisting of strings with the variant definitions
        """
        if self._set_cache is not None:
            return self._set_cache

        defined_variants = set()
        out_set = set()

        # Define default variants after experiment variants so we only define
        # undefined variants.
        variant_sets = [self.experiment_variants, self.default_variants]

        for variant_set in variant_sets:
            for name, variant in variant_set.items():
                if name not in defined_variants:
                    out_set.add(variant.as_definition())
                    defined_variants.add(name)

        for name, variant_list in self.multi_value_variants.items():
            for variant in variant_list:
                out_set.add(variant.as_definition())

        self._set_cache = out_set
        return out_set


class Variant:
    """A custom set for housing multiple types of variants, and encapsulating
    the logic of merging them together."""

    def __init__(
        self,
        name: str,
        default: Optional[Any] = None,
        description: str = "",
        values: Optional[Union[Sequence, Callable[[Any], bool]]] = None,
    ):
        self.name = name
        self.default = default
        self.description = description
        self.values = values
        if isinstance(self.default, bool):
            if self.default:
                self._definition = f"+{self.name}"
            else:
                self._definition = f"~{self.name}"
        else:
            self._definition = f"{self.name}={str(self.default)}"

    def copy(self):
        return Variant(
            name=self.name, default=self.default, description=self.description, values=self.values
        )

    def as_definition(self):
        """Build a definition for this variant

        Format the variant as a string which can be used to test against when
        clauses.

        Returns:
            str: String definition for this variant
        """
        return self._definition

        if isinstance(self.default, bool):
            if self.default:
                return f"+{self.name}"
            else:
                return f"~{self.name}"
        return f"{self.name}={str(self.default)}"

    def as_str(self, indent=0):
        """String documentation of this variant

        Returns:
            str: String for information of this variant
        """
        indentation = " " * indent
        out_str = f"{indentation}Variant: {self.name}\n"
        attrs = [
            ("Description", "description"),
            ("Default", "default"),
            ("Values", "values"),
        ]
        for print_name, attr_name in attrs:
            if hasattr(self, attr_name):
                value = getattr(self, attr_name, None)
                if value is not None:
                    out_str += f"{indentation}  {print_name}: {value}"
        return out_str

    def __str__(self):
        return self.as_str(indent=0)


def validate_variant(variant: str):
    """Check if a variant name is valid or not

    If the input variant name is not valid, this function will raise an
    exception. Otherwise this function will not perform any actions.

    Args:
        variant (str): Variant name to test
    """

    if variant in reserved_variants:
        raise RambleVariantError(
            f"Variant {variant} is invalid, as this name is reserved by ramble"
        )


class RambleVariantError(ramble.error.RambleError):
    """Class representing errors with variants"""
