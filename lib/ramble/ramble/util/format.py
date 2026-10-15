# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import io
import re
import textwrap

_WHITESPACE_RE = re.compile(r"\s+")


def format_doc(doc_str, **kwargs):
    """Wrap doc string at 72 characters and format nicely"""
    if not doc_str:
        return ""
    indent = kwargs.get("indent", 0)
    doc = _WHITESPACE_RE.sub(" ", doc_str)
    lines = textwrap.wrap(doc, 72)
    results = io.StringIO()
    for line in lines:
        results.write((" " * indent) + line + "\n")
    return results.getvalue()


def when_order(when: str):
    """Sort 'when' conditions consistently when unpacking from sets or lists"""

    if not when:
        return (3, when)  # Handle empty strings

    first_char = when[0]

    if first_char.isalpha():
        priority = 0
    elif first_char == "+":
        priority = 1
    elif first_char == "~":
        priority = 2
    else:
        priority = 3  # For any other characters

    return (priority, when)
