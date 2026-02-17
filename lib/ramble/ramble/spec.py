# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import io
from typing import Mapping

import llnl.util.tty.color as clr

import ramble.error

color_formats: Mapping[str, str] = {}
default_format = "{name}"


class Spec:
    def __init__(self, spec_like=None):
        """Create a new Spec.

        Arguments:
          spec_like (optional string): If not provided we initialize an
          anonymous Spec that matches any Spec object; if provided we parse
          this as a Spec string.
        """

        # Copy if spec_like is a Spec.
        if isinstance(spec_like, Spec):
            self._dup(spec_like)
            return

        # init an empty spec that matches anything.
        self.name = None
        self.namespace = None

        if isinstance(spec_like, str):
            namespace, _, spec_name = spec_like.rpartition(".")
            if not namespace:
                namespace = None
            self.name = spec_name
            self.namespace = namespace

    def copy(self):
        new_spec = Spec()
        new_spec._dup(self)
        return new_spec

    def _dup(self, other):
        self.name = other.name
        self.namespace = other.namespace

    def format(self, format_string=default_format, **kwargs):
        r"""Prints out particular pieces of a spec, depending on what is
        in the format string.

        Using the ``{attribute}`` syntax, any field of the spec can be
        selected.  Those attributes can be recursive.

        Commonly used attributes of the Spec for format strings include::

            name

        Args:
            format_string (str): string containing the format to be expanded

        Keyword Args:
            color (bool): True if returned string is colored
            transform (dict): maps full-string formats to a callable \
                              that accepts a string and returns another one

        """

        color = kwargs.get("color", False)
        transform = kwargs.get("transform", {})

        out = io.StringIO()

        def write(s, c=None):
            f = clr.cescape(s)
            if c is not None:
                f = color_formats[c] + f + "@."
            clr.cwrite(f, stream=out, color=color)

        def write_attribute(spec, attribute, color):
            current = spec

            if attribute == "":
                raise SpecFormatStringError("Format string attributes must be non-empty")
            attribute = attribute.lower()

            parts = attribute.split(".")
            assert parts

            # find the morph function for our attribute
            morph = transform.get(attribute, lambda s, x: x)

            # Iterate over components using getattr to get next element
            for idx, part in enumerate(parts):
                if not part:
                    raise SpecFormatStringError("Format string attributes must be non-empty")
                if part.startswith("_"):
                    raise SpecFormatStringError("Attempted to format private attribute")
                else:
                    try:
                        current = getattr(current, part)
                    except AttributeError:
                        parent = ".".join(parts[:idx])
                        m = "Attempted to format attribute %s." % attribute
                        m += f"Spec {parent} has no attribute {part}"
                        raise SpecFormatStringError(m) from None

                    if callable(current):
                        raise SpecFormatStringError("Attempted to format callable object")
                    if not current:
                        # We're not printing anything
                        return

            # Finally, write the output
            col = None
            write(morph(spec, str(current)), col)

        attribute = ""
        in_attribute = False
        escape = False

        for c in format_string:
            if escape:
                out.write(c)
                escape = False
            elif c == "\\":
                escape = True
            elif in_attribute:
                if c == "}":
                    write_attribute(self, attribute, color)
                    attribute = ""
                    in_attribute = False
                else:
                    attribute += c
            else:
                if c == "}":
                    raise SpecFormatStringError("Encountered closing } before opening {")
                elif c == "{":
                    in_attribute = True
                else:
                    out.write(c)
        if in_attribute:
            raise SpecFormatStringError(
                "Format string terminated while reading attribute." "Missing terminating }."
            )

        formatted_spec = out.getvalue()
        return formatted_spec.strip()

    def cformat(self, *args, **kwargs):
        """Same as format, but color defaults to auto instead of False."""
        kwargs = kwargs.copy()
        kwargs.setdefault("color", None)
        return self.format(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def fullname(self):
        return (
            (f"{self.namespace}.{self.name}")
            if self.namespace
            else (self.name if self.name else "")
        )


class SpecFormatStringError(ramble.error.SpecError):
    """Called for errors in Spec format strings."""
