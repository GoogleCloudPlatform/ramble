# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import functools
import io
from typing import Mapping

import ramble.error
import ramble.util.colors as clr

color_formats: Mapping[str, str] = {}
default_format = "{name}"


@functools.lru_cache(maxsize=None)
def _parse_spec_string(spec_like):
    if not spec_like:
        return "", None, None

    # Strip any version suffix if present (e.g., app@1.0)
    spec_like = spec_like.partition("@")[0].lower()

    parts = spec_like.split(".")

    import ramble.repository

    type_map = ramble.repository.get_object_type_map()

    if len(parts) >= 3 and parts[-2] in type_map:
        object_type = type_map[parts[-2]]
        name = parts[-1]
        namespace = ".".join(parts[:-2])
    elif len(parts) >= 2:
        if len(parts) == 2 and parts[0] in type_map:
            object_type = type_map[parts[0]]
            name = parts[1]
            namespace = None
        else:
            object_type = None
            name = parts[-1]
            namespace = ".".join(parts[:-1])
    else:
        object_type = None
        name = parts[0]
        namespace = None

    return name, namespace, object_type


class Spec:
    def __init__(self, spec_like=None, object_type=None):
        """Create a new Spec.

        Arguments:
          spec_like (optional string or Spec): If not provided we initialize an
          anonymous Spec that matches any Spec object; if provided we parse
          this as a Spec string.
          object_type (optional ObjectTypes): Optional object type enum.
        """

        # Copy if spec_like is a Spec.
        if isinstance(spec_like, Spec):
            self._dup(spec_like)
            if object_type is not None:
                self.object_type = object_type
            return

        # init an empty spec that matches anything.
        self.name = None
        self.namespace = None
        self.object_type = object_type

        if isinstance(spec_like, str):
            self._parse_spec_string(spec_like)

    def _parse_spec_string(self, spec_like):
        self.name, self.namespace, parsed_type = _parse_spec_string(spec_like)
        if self.object_type is None:
            self.object_type = parsed_type

    def copy(self):
        new_spec = Spec()
        new_spec._dup(self)
        return new_spec

    def _dup(self, other):
        self.name = other.name
        self.namespace = other.namespace
        self.object_type = getattr(other, "object_type", None)

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
                        m = f"Attempted to format attribute {attribute}."
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
        return self.name if self.name is not None else ""

    @property
    def fullname(self):
        if not self.name:
            return ""
        import ramble.repository

        if self.namespace:
            if self.object_type:
                abbrev = ramble.repository.type_definitions[self.object_type]["abbrev"]
                return f"{self.namespace}.{abbrev}.{self.name}"
            return f"{self.namespace}.{self.name}"
        else:
            if self.object_type:
                abbrev = ramble.repository.type_definitions[self.object_type]["abbrev"]
                return f"{abbrev}.{self.name}"
            return self.name


class SpecFormatStringError(ramble.error.SpecError):
    """Called for errors in Spec format strings."""
