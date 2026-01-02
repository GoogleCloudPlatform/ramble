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


def format_doc(doc_str, **kwargs):
    """Wrap doc string at 72 characters and format nicely"""
    if not doc_str:
        return ""
    indent = kwargs.get("indent", 0)
    doc = re.sub(r"\s+", " ", doc_str)
    lines = textwrap.wrap(doc, 72)
    results = io.StringIO()
    for line in lines:
        results.write((" " * indent) + line + "\n")
    return results.getvalue()
