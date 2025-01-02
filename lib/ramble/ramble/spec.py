# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import io
import os

import llnl.util.tty.color as clr

import ramble.repository
import ramble.error
from ramble.util.logger import logger

import spack.parse

#: These are possible token types in the spec grammar.
HASH, DEP, AT, COLON, COMMA, ON, OFF, PCT, EQ, ID, VAL, FILE = range(12)

#: Regex for fully qualified spec names. (e.g., builtin.hdf5)
spec_id_re = r"\w[\w.-]*"

color_formats = {}

default_format = "{name}"


class SpecLexer(spack.parse.Lexer):
    """Parses tokens that make up spack specs."""

    def __init__(self):
        super().__init__(
            [
                (r"\^", lambda scanner, val: self.token(DEP, val)),
                (r"\@", lambda scanner, val: self.token(AT, val)),
                (r"\:", lambda scanner, val: self.token(COLON, val)),
                (r"\,", lambda scanner, val: self.token(COMMA, val)),
                (r"\+", lambda scanner, val: self.token(ON, val)),
                (r"\-", lambda scanner, val: self.token(OFF, val)),
                (r"\~", lambda scanner, val: self.token(OFF, val)),
                (r"\%", lambda scanner, val: self.token(PCT, val)),
                (r"\=", lambda scanner, val: self.token(EQ, val)),
                # Filenames match before identifiers, so no initial filename
                # component is parsed as a spec (e.g., in subdir/spec.yaml)
                (r"[/\w.-]*/[/\w/-]+\.yaml[^\b]*", lambda scanner, v: self.token(FILE, v)),
                # Hash match after filename. No valid filename can be a hash
                # (files end w/.yaml), but a hash can match a filename prefix.
                (r"/", lambda scanner, val: self.token(HASH, val)),
                # Identifiers match after filenames and hashes.
                (spec_id_re, lambda scanner, val: self.token(ID, val)),
                (r"\s+", lambda scanner, val: None),
            ],
            [EQ],
            [
                (r"[\S].*", lambda scanner, val: self.token(VAL, val)),
                (r"\s+", lambda scanner, val: None),
            ],
            [VAL],
        )


# Lexer is always the same for every parser
_lexer = SpecLexer()


class SpecParser(spack.parse.Parser):
    def __init__(self, initial_spec=None):
        """Construct a new SpecParser.

        Args:
            initial_spec (Spec, optional): provide a Spec that we'll parse
                directly into. This is used to avoid construction of a
                superfluous Spec object in the Spec constructor.
        """
        logger.debug(f"Starting parser with spec {initial_spec}")
        super().__init__(_lexer)
        self.previous = None
        self._initial = initial_spec

    def do_parse(self):
        app_spec = None
        try:
            if self.accept(ID):
                app_spec = Spec(self.token.value)

                while self.next:
                    if self.accept(ID):
                        name = self.workload()
                        app_spec.workloads[name] = True
                    else:
                        break
            else:
                self.next_token_error("Invalid token found")
        except spack.parse.ParseError as e:
            raise SpecParseError(e)

        return [app_spec]

    def workload(self, name=None):
        """Return the name of the workload"""
        if name:
            return name
        else:
            self.expect(ID)
            self.check_identifier()
            return self.token.value

    def check_identifier(self, id=None):
        """The only identifiers that can contain '.' are versions, but version
        ids are context-sensitive so we have to check on a case-by-case
        basis. Call this if we detect a version id where it shouldn't be.
        """
        if not id:
            id = self.token.value
        if "." in id:
            self.last_token_error(f"{id}: Identifier cannot contain '.'")


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

        self._application = None
        self._application_class = None
        self.workloads = {}

        if isinstance(spec_like, str):
            namespace, dot, spec_name = spec_like.rpartition(".")
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
            workloads

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
                        raise SpecFormatStringError(m)

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

    @property
    def application(self):
        if not self._application:
            app_type = ramble.repository.ObjectTypes.applications
            self._application = ramble.repository.paths[app_type].get(self)
        return self._application

    @property
    def application_class(self):
        if not self._application_class:
            app_type = ramble.repository.ObjectTypes.applications
            self._application_class = ramble.repository.paths[app_type].get_obj_class(
                self.fullname
            )
        return self._application_class

    @property
    def application_file_path(self):
        app_type = ramble.repository.ObjectTypes.applications
        file_dir = ramble.repository.paths[app_type].dirname_for_object_name(self.fullname)
        app_file = ramble.repository.paths[app_type].filename_for_object_name(self.fullname)
        return os.path.join(file_dir, app_file)


def parse(string):
    """Returns a spec from an input string."""
    return SpecParser().parse(string)


class SpecParseError(ramble.error.SpecError):
    """Wrapper for ParseError for when we're parsing specs."""

    def __init__(self, parse_error):
        super().__init__(parse_error.message)
        self.string = parse_error.string


class SpecFormatStringError(spack.error.SpecError):
    """Called for errors in Spec format strings."""
