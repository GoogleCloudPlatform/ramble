# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import six

import llnl.util.tty as tty

import ramble.error

import spack.parse

#: These are possible token types in the spec grammar.
HASH, DEP, AT, COLON, COMMA, ON, OFF, PCT, EQ, ID, VAL, FILE = range(12)

#: Regex for fully qualified spec names. (e.g., builtin.hdf5)
spec_id_re = r'\w[\w.-]*'


class SpecLexer(spack.parse.Lexer):

    """Parses tokens that make up spack specs."""

    def __init__(self):
        super(SpecLexer, self).__init__([
            (r'\^', lambda scanner, val: self.token(DEP,   val)),
            (r'\@', lambda scanner, val: self.token(AT,    val)),
            (r'\:', lambda scanner, val: self.token(COLON, val)),
            (r'\,', lambda scanner, val: self.token(COMMA, val)),
            (r'\+', lambda scanner, val: self.token(ON,    val)),
            (r'\-', lambda scanner, val: self.token(OFF,   val)),
            (r'\~', lambda scanner, val: self.token(OFF,   val)),
            (r'\%', lambda scanner, val: self.token(PCT,   val)),
            (r'\=', lambda scanner, val: self.token(EQ,    val)),

            # Filenames match before identifiers, so no initial filename
            # component is parsed as a spec (e.g., in subdir/spec.yaml)
            (r'[/\w.-]*/[/\w/-]+\.yaml[^\b]*',
             lambda scanner, v: self.token(FILE, v)),

            # Hash match after filename. No valid filename can be a hash
            # (files end w/.yaml), but a hash can match a filename prefix.
            (r'/', lambda scanner, val: self.token(HASH, val)),

            # Identifiers match after filenames and hashes.
            (spec_id_re, lambda scanner, val: self.token(ID, val)),

            (r'\s+', lambda scanner, val: None)],
            [EQ],
            [(r'[\S].*', lambda scanner, val: self.token(VAL,    val)),
             (r'\s+', lambda scanner, val: None)],
            [VAL])


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
        tty.debug('Starting parser with spec %s' % (initial_spec))
        super(SpecParser, self).__init__(_lexer)
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
        if '.' in id:
            self.last_token_error(
                "{0}: Identifier cannot contain '.'".format(id))


class Spec(object):
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
        self.workloads = {}

        if isinstance(spec_like, six.string_types):
            namespace, dot, spec_name = spec_like.rpartition('.')
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

    def __str__(self):
        return self.name


def parse(string):
    """Returns a spec from an input string.
    """
    return SpecParser().parse(string)


class SpecParseError(ramble.error.SpecError):
    """Wrapper for ParseError for when we're parsing specs."""
    def __init__(self, parse_error):
        super(SpecParseError, self).__init__(parse_error.message)
        self.string = parse_error.string
