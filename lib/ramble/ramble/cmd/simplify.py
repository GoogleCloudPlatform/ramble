# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ast
import difflib
import fnmatch
import inspect
import io
import os
import re
import sys
import tokenize

import ramble.keywords
import ramble.repository
import ramble.util.colors as color
from ramble.expander import (
    format_spec_regex,
    supported_list_function_pointers,
    supported_modules,
    supported_scalar_function_pointers,
    supported_scalar_function_with_self_arg_pointers,
)
from ramble.util.logger import logger

description = "find and simplify unused or unreachable sections in definitions"
section = "developer"
level = "long"

_ALLOWED_MATH_NAMES = frozenset(
    list(supported_scalar_function_pointers.keys())
    + list(supported_list_function_pointers.keys())
    + list(supported_scalar_function_with_self_arg_pointers.keys())
    + list(supported_modules.keys())
    + ["True", "False", "None"]
)
_RESERVED_PATTERNS = tuple(ramble.keywords.Keywords().reserved_patterns)
_DOCSTRING_REGEX = re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', flags=re.DOTALL)
_COMMENT_REGEX = re.compile(r"#.*")
_TEMPLATE_VAR_REGEX = re.compile(r"\{[a-zA-Z0-9_:-]+\}")


def extract_referenced_names(template_str):
    if not isinstance(template_str, str):
        return set()

    referenced = set()
    brace_contents = []
    stack = []
    escaped = False
    for i, char in enumerate(template_str):
        if char == "{":
            if not escaped:
                stack.append(i)
        elif char == "}":
            if not escaped and stack:
                start = stack.pop()
                brace_contents.append(template_str[start + 1 : i])
        elif char == "\n":
            stack = []

        if char == "\\":
            escaped = True
        else:
            escaped = False

    for content in brace_contents:
        match = format_spec_regex.search(content)
        if match:
            content = match.group("kw")

        # Replace '::' with '.' to make namespace references valid Python attributes
        ast_content = content.replace("::", ".")
        try:
            tree = ast.parse(ast_content, mode="eval")

            def get_refs(node, parent=None):
                r = set()
                if isinstance(node, ast.Name):
                    if isinstance(parent, ast.Attribute) and node is parent.value:
                        pass
                    else:
                        r.add(node.id)
                elif isinstance(node, ast.Attribute):
                    if isinstance(parent, ast.Attribute) and node is parent.value:
                        pass
                    else:
                        r.add(node.attr)
                    r.update(get_refs(node.value, parent=node))
                else:
                    for child in ast.iter_child_nodes(node):
                        r.update(get_refs(child, parent=node))
                return r

            referenced.update(get_refs(tree.body))
        except SyntaxError:
            # Fallback to regex-based extraction if syntax is not valid Python
            words = re.findall(r"[a-zA-Z0-9_:-]+", content)
            for word in words:
                if "::" in word:
                    referenced.add(word.split("::")[-1])
                else:
                    referenced.add(word)
    return referenced


def find_class_file(parent_cls, obj_path=None):
    module = sys.modules.get(parent_cls.__module__)
    if module and hasattr(module, "__file__") and module.__file__:
        return module.__file__

    if not obj_path:
        return None

    parts = parent_cls.__module__.split(".")
    if len(parts) >= 4 and parts[0] == "ramble":
        obj_abbrev = parts[1]
        obj_name = parts[3]
        for o_type in ramble.repository.ObjectTypes:
            if o_type == ramble.repository.ObjectTypes.base_classes:
                continue
            abbrev = ramble.repository.type_definitions[o_type]["abbrev"]
            if abbrev == obj_abbrev:
                try:
                    path_inst = ramble.repository.paths[o_type]
                    return path_inst.filename_for_object_name(obj_name)
                except Exception:
                    pass
    return None


def find_template_file(cls, src_path_config, obj_path=None):
    if os.path.isabs(src_path_config):
        if os.path.isfile(src_path_config):
            return src_path_config
        return None

    # Get MRO to find where the class/parents are defined
    for parent_cls in inspect.getmro(cls):
        p_file_path = find_class_file(parent_cls, obj_path)
        if p_file_path and (parent_cls.__module__.startswith("ramble") or "ramble" in p_file_path):
            candidate = os.path.join(os.path.dirname(p_file_path), src_path_config)
            if os.path.isfile(candidate):
                return candidate
    return None


def get_nested_dict_keys(cls, attr_name):
    """Extract all inner keys from a 2-level dictionary attribute."""
    keys = set()

    nested_dict = getattr(cls, attr_name, None)
    if nested_dict:
        for inner in nested_dict.values():
            if isinstance(inner, dict):
                keys.update(inner.keys())
    return keys


def iter_nested_dict_values(cls, attr_name):
    """Yield all inner values from a 2-level dictionary attribute."""
    nested_dict = getattr(cls, attr_name, None)
    if nested_dict:
        for inner in nested_dict.values():
            if isinstance(inner, dict):
                yield from inner.values()


def iter_defined_variables(cls):
    """Yield all variable instances defined on an object class."""
    if hasattr(cls, "workloads") and cls.workloads:
        for app_workloads in cls.workloads.values():
            for wl_obj in app_workloads.values():
                for var_list in wl_obj.variables.values():
                    for var in var_list:
                        yield var

    if hasattr(cls, "object_variables") and cls.object_variables:
        for var_list in cls.object_variables.values():
            for var in var_list:
                yield var


def iter_object_template_strings(cls, obj_path=None):
    """Yield (template_str, fom_captures, ignore_names) for all templates in an object."""
    # Executables
    for exec_obj in iter_nested_dict_values(cls, "executables"):
        templates = (
            exec_obj.template if isinstance(exec_obj.template, list) else [exec_obj.template]
        )
        for t in templates:
            yield (t, None, None)

    # Workload and object variables
    for var in iter_defined_variables(cls):
        yield (str(var.default), None, None)

    # Environment variables (object, workload group, workload level)
    env_sources = []
    if hasattr(cls, "object_environment_variables") and cls.object_environment_variables:
        env_sources.append(cls.object_environment_variables.values())
    if hasattr(cls, "workload_group_env_vars") and cls.workload_group_env_vars:
        env_sources.append(cls.workload_group_env_vars.values())
    if hasattr(cls, "workloads") and cls.workloads:
        for app_workloads in cls.workloads.values():
            env_sources.extend(
                wl_obj.environment_variables.values()
                for wl_obj in app_workloads.values()
                if getattr(wl_obj, "environment_variables", None)
            )

    for source in env_sources:
        for env_vars_list in source:
            for env_var in env_vars_list:
                if env_var.name:
                    yield (env_var.name, None, None)
                if env_var.value:
                    yield (str(env_var.value), None, None)

    # Inputs
    for input_obj in iter_nested_dict_values(cls, "inputs"):
        url = getattr(input_obj, "url", None)
        if url is None and isinstance(input_obj, dict):
            url = input_obj.get("url")
        if url:
            yield (url, None, None)

    # Figures of merit
    if hasattr(cls, "figures_of_merit") and cls.figures_of_merit:
        for contexts_dict in cls.figures_of_merit.values():
            for foms_dict in contexts_dict.values():
                for fom_val in foms_dict.values():
                    if isinstance(fom_val, dict):
                        fom_captures = set()
                        if "fom_regex" in fom_val:
                            try:
                                fom_captures.update(
                                    re.compile(fom_val["fom_regex"]).groupindex.keys()
                                )
                            except re.error as e:
                                logger.warn(
                                    "Invalid regex for figure of merit: "
                                    f"{fom_val['fom_regex']}. Error: {e}"
                                )
                        if "log_file" in fom_val:
                            yield (fom_val["log_file"], fom_captures, None)

    # Success criteria
    if hasattr(cls, "success_criteria") and cls.success_criteria:
        for when_dict in cls.success_criteria.values():
            if isinstance(when_dict, dict):
                for criteria_dict in when_dict.values():
                    if isinstance(criteria_dict, dict):
                        if "file" in criteria_dict:
                            yield (criteria_dict["file"], None, None)
                        if "formula" in criteria_dict:
                            ignore = (
                                {"value"}
                                if criteria_dict.get("mode") == "fom_comparison"
                                else None
                            )
                            yield (criteria_dict["formula"], None, ignore)

    # Registered templates
    for tpl_config in iter_nested_dict_values(cls, "templates"):
        src_path_config = tpl_config.get("src_path") if isinstance(tpl_config, dict) else None
        if src_path_config:
            tpl_file = find_template_file(cls, src_path_config, obj_path)
            if tpl_file:
                try:
                    with open(tpl_file, encoding="utf-8") as f_tpl:
                        yield (f_tpl.read(), None, None)
                except Exception:
                    pass


def clean_source_code(source_code):
    """Strip comments, docstrings, and template braces from source code."""
    cleaned = _COMMENT_REGEX.sub("", source_code)
    cleaned = _DOCSTRING_REGEX.sub("", cleaned)
    return _TEMPLATE_VAR_REGEX.sub("", cleaned)


def count_unreferenced_items(items, used_set, def_patterns, cleaned_code):
    """Find items not in used_set that are only referenced in their definitions."""
    unused = []
    pattern_prefix = r"\b(?:" + "|".join(def_patterns) + r")"
    for item in sorted(items):
        if item in used_set:
            continue
        occurrences = len(re.findall(rf"\b{re.escape(item)}\b", cleaned_code))
        defs = len(
            re.findall(
                rf'{pattern_prefix}\s*\(\s*[\'"]{re.escape(item)}[\'"]',
                cleaned_code,
            )
        )
        if occurrences <= defs:
            unused.append(item)
    return unused


def get_arg_value(arg_node):
    if isinstance(arg_node, ast.Constant):
        return arg_node.value
    if hasattr(ast, "Str") and isinstance(arg_node, ast.Str):
        return arg_node.s
    return None


def get_node_end_lineno(node, file_lines=None):
    if getattr(node, "end_lineno", None) is not None:
        return node.end_lineno

    if not file_lines:
        return node.lineno

    # Fallback for Python versions lacking AST end_lineno
    source = "\n".join(file_lines[node.lineno - 1 :])
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        depth = 0
        saw_paren = False
        for tok_type, tok_str, _, (erow, _), _ in tokens:
            if tok_str in "([{":
                depth += 1
                saw_paren = True
            elif tok_str in ")]}":
                depth -= 1
                if saw_paren and depth <= 0:
                    return (node.lineno - 1) + erow
            elif tok_type == tokenize.NEWLINE and not saw_paren:
                return (node.lineno - 1) + erow
    except Exception:
        pass
    return node.lineno


DIRECTIVE_CATEGORIES = {
    "workload_variable": "variables",
    "variable": "variables",
    "input_file": "inputs",
    "executable": "executables",
    "formatted_executable": "executables",
    "define_compiler": "compilers",
}


def iter_class_directive_calls(tree):
    """Yield (node, call, func_name, category, first_arg_val) for class directive calls."""
    if not tree:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):

            def _walk_body(body):
                for item in body:
                    if isinstance(item, ast.Expr) and isinstance(item.value, ast.Call):
                        call = item.value
                        if isinstance(call.func, ast.Name):
                            func_name = call.func.id
                            category = DIRECTIVE_CATEGORIES.get(func_name)
                            first_val = get_arg_value(call.args[0]) if call.args else None
                            yield (item, call, func_name, category, first_val)
                    elif isinstance(item, ast.With):
                        yield from _walk_body(item.body)

            yield from _walk_body(node.body)
            break


def parse_source_tree(file_path):
    """Read and parse an AST from a file path."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        return content, ast.parse(content)
    except (OSError, SyntaxError) as e:
        logger.warn(f"Could not parse {file_path}: {e}")
        return None, None


def locate_directive_lines(
    file_path, unused_vars, unused_inputs, unused_execs, unused_compilers, broken_vars
):
    content, tree = parse_source_tree(file_path)
    if not tree or not content:
        return []

    file_lines = content.splitlines()
    unused_by_category = {
        "variables": set(unused_vars) | set(broken_vars),
        "inputs": set(unused_inputs),
        "executables": set(unused_execs),
        "compilers": set(unused_compilers),
    }

    ranges_to_remove = []
    for node, _call, _func_name, category, val in iter_class_directive_calls(tree):
        if category and val and val in unused_by_category.get(category, set()):
            ranges_to_remove.append((node.lineno, get_node_end_lineno(node, file_lines)))

    return ranges_to_remove


def parse_local_definitions(file_path):
    defs = {"variables": {}, "inputs": {}, "executables": {}, "compilers": {}}
    content, tree = parse_source_tree(file_path)
    if not tree or not content:
        return defs

    file_lines = content.splitlines(keepends=True)
    for node, _call, _func_name, category, val in iter_class_directive_calls(tree):
        if category and val:
            start = node.lineno
            end = get_node_end_lineno(node, file_lines)
            source_text = "".join(file_lines[start - 1 : end])
            defs[category][val] = (start, end, source_text)
    return defs


def apply_simplifications(file_path, ranges, pending_insertions=None):
    with open(file_path, encoding="utf-8") as f:
        original_content = f.read()

    original_lines = original_content.splitlines(keepends=True)
    new_lines = list(original_lines)

    # Sort ranges in descending order of start line
    for start, end in sorted(ranges, reverse=True):
        del new_lines[start - 1 : end]

    new_content = "".join(new_lines)

    if pending_insertions:
        try:
            tree = ast.parse(new_content)
        except Exception as e:
            logger.warn(f"Could not parse simplified content of {file_path} for insertion: {e}")
            return original_lines, new_lines, new_content

        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_node = node
                break

        if class_node:
            first_func_line = None
            last_class_level_line = None
            modified_lines = new_content.splitlines(keepends=True)

            for node in class_node.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if first_func_line is None or node.lineno < first_func_line:
                        first_func_line = node.lineno
                else:
                    end_line = get_node_end_lineno(node, modified_lines)
                    if last_class_level_line is None or end_line > last_class_level_line:
                        last_class_level_line = end_line

            if first_func_line is not None:
                insert_idx = first_func_line - 1
            elif last_class_level_line is not None:
                insert_idx = last_class_level_line
            else:
                insert_idx = class_node.lineno

            indent = "    "
            if class_node.body:
                first_node = class_node.body[0]
                if first_node.lineno - 1 < len(modified_lines):
                    line = modified_lines[first_node.lineno - 1]
                    indent = " " * (len(line) - len(line.lstrip()))

            insert_lines = []
            for _cat, _item_name, source_text in pending_insertions:
                src_lines = source_text.splitlines()
                non_empty_src_lines = [line for line in src_lines if line.strip()]
                if non_empty_src_lines:
                    min_spaces = min(
                        len(line) - len(line.lstrip()) for line in non_empty_src_lines
                    )
                else:
                    min_spaces = 0

                for line in src_lines:
                    stripped = line[min_spaces:]
                    if stripped.strip():
                        insert_lines.append(indent + stripped + "\n")
                    else:
                        insert_lines.append("\n")

            modified_lines.insert(insert_idx, "".join(insert_lines))
            new_content = "".join(modified_lines)
            new_lines = new_content.splitlines(keepends=True)

    return original_lines, new_lines, new_content


def is_valid_reference(
    var_name,
    all_defined_variables,
    defined_inputs,
    defined_software_specs,
    source_code,
    fom_captures=None,
):
    if (
        var_name in all_defined_variables
        or var_name in defined_inputs
        or (var_name.endswith("_path") and var_name[:-5] in defined_software_specs)
        or var_name in ramble.keywords.default_keys
        or (fom_captures and var_name in fom_captures)
        or var_name in _ALLOWED_MATH_NAMES
        or any(pat.match(var_name) for pat in _RESERVED_PATTERNS)
    ):
        return True

    # Strip quotes or match as literal token in source code (fallback for python references)
    return bool(re.search(r"\b" + re.escape(var_name) + r"\b", source_code))


def _matches_any_pattern(val, defined_items):
    return val == "*" or any(fnmatch.fnmatch(item, val) for item in defined_items)


def _extract_kwarg_values(kw_node):
    if isinstance(kw_node.value, ast.List):
        return [get_arg_value(elt) for elt in kw_node.value.elts]
    val = get_arg_value(kw_node.value)
    return [val] if val is not None else []


def is_variable_reference_broken(call, all_defined_workloads, all_defined_workload_groups):
    for kw in call.keywords:
        if kw.arg in ("workload", "workloads"):
            for wl_val in _extract_kwarg_values(kw):
                if wl_val and not _matches_any_pattern(wl_val, all_defined_workloads):
                    return True
        elif kw.arg == "workload_group":
            for wg_val in _extract_kwarg_values(kw):
                if wg_val and not _matches_any_pattern(wg_val, all_defined_workload_groups):
                    return True
    return False


def check_broken_workload_groups(call, group_name, all_defined_workloads):
    broken = []
    for kw in call.keywords:
        if kw.arg == "workloads":
            broken.extend(
                f"{group_name} -> {wl_val}"
                for wl_val in _extract_kwarg_values(kw)
                if wl_val and not _matches_any_pattern(wl_val, all_defined_workloads)
            )
    return broken


def analyze_object(name, obj_type):
    obj_path = ramble.repository.paths[obj_type]
    cls = obj_path.get_obj_class(name)

    target_file_path = obj_path.filename_for_object_name(name)

    # Collect source codes from the class and all its parent classes in ramble/
    source_codes = []
    for parent_cls in inspect.getmro(cls):
        p_file_path = find_class_file(parent_cls, obj_path)
        if p_file_path and (parent_cls.__module__.startswith("ramble") or "ramble" in p_file_path):
            try:
                with open(p_file_path, encoding="utf-8") as f:
                    source_codes.append(f.read())
            except OSError as e:
                logger.warn(f"Could not read source file {p_file_path}: {e}")
    source_code = "\n".join(source_codes)
    cleaned_code = clean_source_code(source_code)

    # Parse AST of the target file
    try:
        with open(target_file_path, encoding="utf-8") as f:
            file_content = f.read()
        tree = ast.parse(file_content)
    except Exception:
        tree = None

    # Collect defined entities (including inherited ones)
    all_defined_workloads = get_nested_dict_keys(cls, "workloads")
    all_defined_workload_groups = set(getattr(cls, "workload_groups", {}) or ())
    defined_inputs = get_nested_dict_keys(cls, "inputs")
    defined_executables = get_nested_dict_keys(cls, "executables")
    defined_variables = {var.name for var in iter_defined_variables(cls)}

    # Collect compilers and software specs
    all_referenced_compilers = set()
    defined_software_specs = set(getattr(cls, "required_packages", {}) or ())

    if hasattr(cls, "software_specs") and cls.software_specs:
        for specs_list in cls.software_specs.values():
            for spec_obj in specs_list:
                if getattr(spec_obj, "compiler", None):
                    all_referenced_compilers.add(spec_obj.compiler)
                defined_software_specs.add(spec_obj.name)
                # If spec name has braces/template parts, add prefix up to the first brace/hyphen
                # E.g. 'orca-{version}' -> add 'orca'
                prefix = spec_obj.name.split("{")[0].rstrip("-")
                if prefix:
                    defined_software_specs.add(prefix)

                # Extract package name from pkg_spec (e.g. 'orca@5.0.4' -> 'orca')
                if spec_obj.pkg_spec:
                    pkg_match = re.match(r"\s*([\w-]+)", spec_obj.pkg_spec)
                    if pkg_match:
                        defined_software_specs.add(pkg_match.group(1))

    # Gather all templates/strings to extract referenced names and check broken template references
    all_referenced_names = set()
    broken_template_refs = set()

    for tpl_str, fom_captures, ignore_names in iter_object_template_strings(cls, obj_path):
        refs = extract_referenced_names(tpl_str)
        all_referenced_names.update(refs)
        for r in refs:
            if ignore_names and r in ignore_names:
                continue
            if not is_valid_reference(
                r,
                defined_variables,
                defined_inputs,
                defined_software_specs,
                cleaned_code,
                fom_captures,
            ):
                broken_template_refs.add(r)

    # Extract workload relationships (executables and inputs used directly in workloads)
    used_executables = set()
    used_inputs = set()
    if hasattr(cls, "workloads") and cls.workloads:
        for app_workloads in cls.workloads.values():
            for wl_obj in app_workloads.values():
                used_executables.update(getattr(wl_obj, "executables", ()) or ())
                used_inputs.update(getattr(wl_obj, "inputs", ()) or ())

    # Also extract inputs referenced in other inputs/url or variables
    for name in all_referenced_names:
        if name in defined_inputs:
            used_inputs.add(name)

    unused_variables = count_unreferenced_items(
        defined_variables,
        all_referenced_names,
        ["workload_variable", "variable"],
        cleaned_code,
    )

    # For each defined input, check if it's used
    unused_inputs = count_unreferenced_items(
        defined_inputs,
        used_inputs,
        ["input_file"],
        cleaned_code,
    )

    # For each defined executable, check if it's used
    unused_executables = count_unreferenced_items(
        defined_executables,
        used_executables,
        ["executable", "edit_file", "patch_file", "formatted_executable"],
        cleaned_code,
    )

    # Statically parse class body to find unused compilers, broken variables, and workload groups
    unused_compilers = []
    broken_vars = []
    broken_groups = []

    if tree:
        for _node, call, func_name, _category, first_val in iter_class_directive_calls(tree):
            if func_name == "define_compiler" and first_val:
                if first_val not in all_referenced_compilers:
                    occurrences = len(re.findall(rf"\b{re.escape(first_val)}\b", cleaned_code))
                    pattern = rf"define_compiler\s*\(\s*[\'\"]{re.escape(first_val)}[\'\"]"
                    defs = len(re.findall(pattern, cleaned_code))
                    if occurrences <= defs:
                        unused_compilers.append(first_val)

            elif func_name in ("workload_variable", "variable"):
                if first_val and is_variable_reference_broken(
                    call, all_defined_workloads, all_defined_workload_groups
                ):
                    broken_vars.append(first_val)

            elif func_name == "workload_group":
                broken_groups.extend(
                    check_broken_workload_groups(call, first_val, all_defined_workloads)
                )

    return (
        unused_variables,
        unused_inputs,
        unused_executables,
        unused_compilers,
        broken_vars,
        broken_groups,
        sorted(broken_template_refs),
    )


def is_subclass_by_name(sub_cls, parent_cls):
    parent_qname = f"{parent_cls.__module__}.{parent_cls.__name__}"
    return any(f"{b.__module__}.{b.__name__}" == parent_qname for b in sub_cls.__mro__)


def compute_proposed_moves(all_names, subclasses_map, local_defs, analysis_results):
    """Compute proposed moves from parent classes to subclasses that use them."""
    proposed_moves = {}
    insertions = {}

    category_map = {
        "variables": 0,
        "inputs": 1,
        "executables": 2,
        "compilers": 3,
    }

    for name in all_names:
        if name not in local_defs or name not in analysis_results:
            continue

        subclasses = subclasses_map.get(name, [])
        if not subclasses:
            continue

        for category, res_idx in category_map.items():
            local_category_defs = local_defs[name][category]
            unused_list = analysis_results[name][res_idx]

            for item_name, (_start, _end, source_text) in local_category_defs.items():
                if item_name in unused_list:
                    using_subclasses = [
                        child
                        for child in subclasses
                        if child in analysis_results
                        and item_name not in analysis_results[child][res_idx]
                        and item_name not in local_defs[child][category]
                    ]

                    if using_subclasses:
                        proposed_moves.setdefault(name, {}).setdefault(category, []).append(
                            (item_name, using_subclasses, source_text)
                        )
                        for child_name in using_subclasses:
                            insertions.setdefault(child_name, []).append(
                                (category, item_name, source_text)
                            )
                        if item_name in analysis_results[name][res_idx]:
                            analysis_results[name][res_idx].remove(item_name)
                        for child_name in subclasses:
                            if child_name in analysis_results:
                                if item_name in analysis_results[child_name][res_idx]:
                                    analysis_results[child_name][res_idx].remove(item_name)

    return proposed_moves, insertions


def setup_parser(subparser):
    subparser.add_argument(
        "-t",
        "--type",
        default="applications",
        choices=ramble.repository.OBJECT_NAMES,
        help="Object type to check (default: applications)",
    )
    subparser.add_argument(
        "-r",
        "--repo",
        default=None,
        help="Only check objects defined within the specified repository namespace",
    )
    subparser.add_argument(
        "-d",
        "--diff",
        action="store_true",
        help="show diff of proposed simplifications",
    )
    subparser.add_argument(
        "-a",
        "--apply",
        action="store_true",
        help="apply proposed simplifications to definition files",
    )
    subparser.add_argument(
        "names",
        nargs="*",
        default=None,
        help="Names of specific objects to check. If none, check all objects.",
    )


def simplify(parser, args):
    obj_type = ramble.repository.ObjectTypes[args.type]
    obj_path = ramble.repository.paths[obj_type]

    if args.repo:
        try:
            repo = obj_path.get_repo(args.repo)
            names_in_repo = set(repo.all_object_names())
            if args.names:
                names = [n for n in args.names if n in names_in_repo]
            else:
                names = list(names_in_repo)
        except Exception:
            logger.error(f"Repository namespace '{args.repo}' is not configured.")
            return 1
    else:
        if args.names:
            names = args.names
        else:
            names = obj_path.all_object_names()

    # Pre-analyze all objects in the repository to build global maps
    all_names = obj_path.all_object_names()
    global_classes = {}
    local_defs = {}
    analysis_results = {}
    analysis_errors = {}

    for name in all_names:
        try:
            cls = obj_path.get_obj_class(name)
            file_path = obj_path.filename_for_object_name(name)
            global_classes[name] = cls
            local_defs[name] = parse_local_definitions(file_path)
            analysis_results[name] = list(analyze_object(name, obj_type))
        except Exception as e:
            analysis_errors[name] = e
            logger.debug(f"Error pre-analyzing {name}: {e}")

    subclasses_map = {}
    for name, cls in global_classes.items():
        subclasses = [
            other_name
            for other_name, other_cls in global_classes.items()
            if other_cls is not cls and is_subclass_by_name(other_cls, cls)
        ]
        subclasses_map[name] = subclasses

    # Compute proposed moves and insertions
    proposed_moves, insertions = compute_proposed_moves(
        all_names, subclasses_map, local_defs, analysis_results
    )

    total_unused_vars = 0
    total_unused_inputs = 0
    total_unused_execs = 0
    total_unused_compilers = 0
    total_broken_vars = 0

    for name in sorted(names):
        if name in analysis_errors:
            logger.warn(f"Error analyzing {name}: {analysis_errors[name]}")
            continue

        try:
            res = analysis_results.get(name) or list(analyze_object(name, obj_type))
            (
                unused_vars,
                unused_inputs,
                unused_execs,
                unused_compilers,
                broken_vars,
                broken_groups,
                broken_templates,
            ) = res

            has_moves = name in proposed_moves
            has_insertions = name in insertions

            if (
                unused_vars
                or unused_inputs
                or unused_execs
                or unused_compilers
                or broken_vars
                or broken_groups
                or broken_templates
                or has_moves
                or has_insertions
            ):
                file_path = obj_path.filename_for_object_name(name)
                color.cprint(f"@c{{=== {args.type.capitalize().rstrip('s')}: {name} ===}}")
                reports = [
                    ("Unused Variables", unused_vars),
                    ("Unused Inputs", unused_inputs),
                    ("Unused Executables", unused_execs),
                    ("Unused Compilers", unused_compilers),
                    ("Variables with Broken Workload/Group Refs", broken_vars),
                    ("Workload Groups with Broken Workload Refs", broken_groups),
                    ("Broken Variable References in Templates", broken_templates),
                ]
                for label, items in reports:
                    if items:
                        print(f"  {label}: {items}")

                total_unused_vars += len(unused_vars)
                total_unused_inputs += len(unused_inputs)
                total_unused_execs += len(unused_execs)
                total_unused_compilers += len(unused_compilers)
                total_broken_vars += len(broken_vars)

                if has_moves:
                    print("  Move to Subclasses:")
                    for category, category_moves in proposed_moves[name].items():
                        for item_name, targets, _ in category_moves:
                            cat_singular = category.capitalize().rstrip("s")
                            print(f"    {cat_singular}: {item_name} -> {targets}")

                if has_insertions:
                    print("  Move from Parents:")
                    for category, item_name, _ in insertions[name]:
                        print(f"    {category.capitalize().rstrip('s')}: {item_name}")

                moved_by_category = {
                    cat: [item[0] for item in proposed_moves.get(name, {}).get(cat, [])]
                    for cat in ("variables", "inputs", "executables", "compilers")
                }

                # Locate line ranges to remove (including compilers,
                # broken variables, and moved ones)
                ranges = locate_directive_lines(
                    file_path,
                    unused_vars + moved_by_category["variables"],
                    unused_inputs + moved_by_category["inputs"],
                    unused_execs + moved_by_category["executables"],
                    unused_compilers + moved_by_category["compilers"],
                    broken_vars,
                )

                pending_insertions = insertions.get(name, [])

                if ranges or pending_insertions:
                    original_lines, new_lines, new_content = apply_simplifications(
                        file_path, ranges, pending_insertions
                    )

                    if args.diff:
                        print("  Proposed Changes:")
                        diff = difflib.unified_diff(
                            original_lines,
                            new_lines,
                            fromfile=file_path,
                            tofile=file_path + ".simplified",
                        )
                        for line in diff:
                            sys.stdout.write("    " + line)

                    if args.apply:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"  Successfully simplified {file_path}")

                print()
        except Exception as e:
            logger.warn(f"Error analyzing {name}: {e}")

    color.cprint(
        f"@g{{Summary: Found {total_unused_vars} unused variables, "
        f"{total_unused_inputs} unused inputs, "
        f"{total_unused_execs} unused executables, "
        f"{total_unused_compilers} unused compilers, "
        f"and {total_broken_vars} variables with broken references.}}"
    )

    return 0
