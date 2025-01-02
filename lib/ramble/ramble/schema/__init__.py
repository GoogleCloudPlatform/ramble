# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""This module contains jsonschema files for all of Ramble's YAML formats."""

import llnl.util.lang
import llnl.util.tty

# jsonschema is imported lazily as it is heavy to import
# and increases the start-up time


def _make_validator():
    import jsonschema

    def _deprecated_properties(validator, deprecated, instance, schema):
        if not (validator.is_type(instance, "object") or validator.is_type(instance, "array")):
            return

        # Get a list of the deprecated properties, return if there is none
        deprecated_properties = [x for x in instance if x in deprecated["properties"]]
        if not deprecated_properties:
            return

        # Retrieve the template message
        msg_str_or_func = deprecated["message"]
        if isinstance(msg_str_or_func, str):
            msg = msg_str_or_func.format(properties=deprecated_properties)
        else:
            msg = msg_str_or_func(instance, deprecated_properties)

        is_error = deprecated["error"]
        if not is_error:
            llnl.util.tty.warn(msg)
        else:
            import jsonschema

            yield jsonschema.ValidationError(msg)

    return jsonschema.validators.extend(
        jsonschema.Draft4Validator, {"deprecatedProperties": _deprecated_properties}
    )


Validator = llnl.util.lang.Singleton(_make_validator)
