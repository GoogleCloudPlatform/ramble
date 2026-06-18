# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble import renderer


def test_renderer_dict_variables():
    group = renderer.RenderGroup("experiment")

    group.variables = {
        "dict_var": {"key": "val"},
        "experiment_name": "test_exp",
    }

    renderer_inst = renderer.Renderer()
    results = list(renderer_inst.render_objects(group))

    assert len(results) == 1

    rendered_vars, _ = results[0]

    assert rendered_vars["dict_var"] == {"key": "val"}
    assert rendered_vars["experiment_name"] == "test_exp"
