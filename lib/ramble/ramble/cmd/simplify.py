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
import os
import re
import sys

import ramble.repository
import ramble.keywords
import ramble.util.colors as color
from ramble.util.logger import logger

description = "find and simplify unused or unreachable sections in definitions"
section = "developer"
level = "long"


def extract_referenced_names(template_str):
    if not isinstance(template_str, str):
        return set()

    referenced = set()
    brace_contents = []
    stack = []
    for i, char in enumerate(template_str):
        if char == '{':
            stack.append(i)
        elif char == '}' and stack:
            start = stack.pop()
            brace_contents.append(template_str[start + 1:i])

    for content in brace_contents:
        words = re.findall(r'[a-zA-Z0-9_:-]+', content)
        for word in words:
            if '::' in word:
                referenced.add(word.split('::')[-1])
            else:
                referenced.add(word)
    return referenced


def find_template_file(cls, src_path_config):
    if os.path.isabs(src_path_config):
        if os.path.isfile(src_path_config):
            return src_path_config
        return None

    # Get MRO to find where the class/parents are defined
    for parent_cls in inspect.getmro(cls):
        module = sys.modules.get(parent_cls.__module__)
        if module and hasattr(module, '__file__') and module.__file__:
            candidate = os.path.join(os.path.dirname(module.__file__), src_path_config)
            if os.path.isfile(candidate):
                return candidate
    return None


def get_arg_value(arg_node):
    if isinstance(arg_node, ast.Constant):
        return arg_node.value
    if hasattr(ast, 'Str') and isinstance(arg_node, ast.Str):
        return arg_node.s
    return None


def locate_directive_lines(file_path, unused_vars, unused_inputs, unused_execs, unused_compilers, broken_vars):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception:
        return []

    # Find the first class definition in the file
    class_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_node = node
            break

    if not class_node:
        return []

    ranges_to_remove = []

    for node in class_node.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name):
                func_name = call.func.id
                if func_name in ('workload_variable', 'variable'):
                    if call.args:
                        val = get_arg_value(call.args[0])
                        if val in unused_vars or val in broken_vars:
                            ranges_to_remove.append((node.lineno, node.end_lineno))
                elif func_name == 'input_file' and unused_inputs:
                    if call.args:
                        val = get_arg_value(call.args[0])
                        if val in unused_inputs:
                            ranges_to_remove.append((node.lineno, node.end_lineno))
                elif func_name in ('executable', 'formatted_executable') and unused_execs:
                    if call.args:
                        val = get_arg_value(call.args[0])
                        if val in unused_execs:
                            ranges_to_remove.append((node.lineno, node.end_lineno))
                elif func_name == 'define_compiler' and unused_compilers:
                    if call.args:
                        val = get_arg_value(call.args[0])
                        if val in unused_compilers:
                            ranges_to_remove.append((node.lineno, node.end_lineno))

    return ranges_to_remove


def apply_simplifications(file_path, ranges):
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()

    original_lines = original_content.splitlines(keepends=True)
    new_lines = list(original_lines)

    # Sort ranges in descending order of start line
    for start, end in sorted(ranges, reverse=True):
        del new_lines[start - 1:end]

    new_content = "".join(new_lines)
    return original_lines, new_lines, new_content


def is_valid_reference(var_name, all_defined_variables, defined_inputs, defined_software_specs, source_code, fom_captures=None):
    if var_name in all_defined_variables or var_name in defined_inputs:
        return True
    if var_name.endswith('_path') and var_name[:-5] in defined_software_specs:
        return True
    if var_name in ramble.keywords.default_keys:
        return True
    kw_inst = ramble.keywords.Keywords()
    if any(pat.match(var_name) for pat in kw_inst.reserved_patterns):
        return True
    if fom_captures and var_name in fom_captures:
        return True
    # Strip quotes or match as literal token in source code (fallback for python references)
    if re.search(r'\b' + re.escape(var_name) + r'\b', source_code):
        return True
    return False


def analyze_object(name, obj_type):
    obj_path = ramble.repository.paths[obj_type]
    cls = obj_path.get_obj_class(name)

    # Collect source codes from the class and all its parent classes in ramble/
    source_codes = []
    file_path = obj_path.filename_for_object_name(name)
    for parent_cls in inspect.getmro(cls):
        module = sys.modules.get(parent_cls.__module__)
        if module and hasattr(module, '__file__') and module.__file__:
            if 'ramble' in module.__file__:
                try:
                    with open(module.__file__, 'r', encoding='utf-8') as f:
                        source_codes.append(f.read())
                except Exception:
                    pass
    source_code = "\n".join(source_codes)

    # Clean the source code (strip comments/strings) for fallback scan
    cleaned_code = re.sub(r'#.*', '', source_code)
    cleaned_code = re.sub(r'""".*?"""', '', cleaned_code, flags=re.DOTALL)
    cleaned_code = re.sub(r"'''.*?'''", '', cleaned_code, flags=re.DOTALL)

    # Parse AST of the target file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        tree = ast.parse(file_content)
    except Exception:
        tree = None

    # Collect all workloads and workload groups (including inherited ones)
    all_defined_workloads = set()
    if hasattr(cls, 'workloads') and cls.workloads:
        for app_workloads in cls.workloads.values():
            for wl_name in app_workloads:
                all_defined_workloads.add(wl_name)

    all_defined_workload_groups = set()
    if hasattr(cls, 'workload_groups') and cls.workload_groups:
        for group_name in cls.workload_groups:
            all_defined_workload_groups.add(group_name)

    # Collect compilers and software specs (including inherited ones)
    all_defined_compilers = set()
    if hasattr(cls, 'compilers') and cls.compilers:
        for compiler_name in cls.compilers:
            all_defined_compilers.add(compiler_name)

    all_referenced_compilers = set()
    if hasattr(cls, 'software_specs') and cls.software_specs:
        for specs_list in cls.software_specs.values():
            for spec_obj in specs_list:
                if hasattr(spec_obj, 'compiler') and spec_obj.compiler:
                    all_referenced_compilers.add(spec_obj.compiler)

    # 1. Collect all defined inputs (only for applications)
    defined_inputs = set()
    if hasattr(cls, 'inputs') and cls.inputs:
        for inputs_dict in cls.inputs.values():
            for input_name in inputs_dict:
                defined_inputs.add(input_name)

    # 2. Collect all defined executables (only for applications)
    defined_executables = set()
    if hasattr(cls, 'executables') and cls.executables:
        for execs_dict in cls.executables.values():
            for exec_name in execs_dict:
                defined_executables.add(exec_name)

    # 3. Collect all defined variables
    defined_variables = set()

    # Workload variables (for applications)
    if hasattr(cls, 'workloads') and cls.workloads:
        for app_workloads in cls.workloads.values():
            for wl_obj in app_workloads.values():
                for var_list in wl_obj.variables.values():
                    for var in var_list:
                        defined_variables.add(var.name)

    # Object variables (for modifiers, base classes, etc.)
    if hasattr(cls, 'object_variables') and cls.object_variables:
        for var_list in cls.object_variables.values():
            for var in var_list:
                defined_variables.add(var.name)

    # Collect all software spec names (including inherited ones), package names, and required packages
    defined_software_specs = set()
    if hasattr(cls, 'software_specs') and cls.software_specs:
        for specs_list in cls.software_specs.values():
            for spec_obj in specs_list:
                defined_software_specs.add(spec_obj.name)
                # If spec name has braces/template parts, add prefix up to the first brace/hyphen
                # E.g. 'orca-{version}' -> add 'orca'
                prefix = spec_obj.name.split('{')[0].rstrip('-')
                if prefix:
                    defined_software_specs.add(prefix)

                # Extract package name from pkg_spec (e.g. 'orca@5.0.4' -> 'orca')
                if spec_obj.pkg_spec:
                    pkg_match = re.match(r'\s*([\w-]+)', spec_obj.pkg_spec)
                    if pkg_match:
                        defined_software_specs.add(pkg_match.group(1))

    if hasattr(cls, 'required_packages') and cls.required_packages:
        for pkgname in cls.required_packages:
            defined_software_specs.add(pkgname)

    # 4. Gather all templates/strings to extract referenced names and check broken template references
    all_referenced_names = set()
    broken_template_refs = set()

    # Extract from executables templates
    if hasattr(cls, 'executables') and cls.executables:
        for execs_dict in cls.executables.values():
            for exec_obj in execs_dict.values():
                templates = (
                    exec_obj.template
                    if isinstance(exec_obj.template, list)
                    else [exec_obj.template]
                )
                for t in templates:
                    refs = extract_referenced_names(t)
                    all_referenced_names.update(refs)
                    for r in refs:
                        if not is_valid_reference(r, defined_variables, defined_inputs, defined_software_specs, cleaned_code):
                            broken_template_refs.add(r)

    # Extract from variables default values
    if hasattr(cls, 'workloads') and cls.workloads:
        for app_workloads in cls.workloads.values():
            for wl_obj in app_workloads.values():
                for var_list in wl_obj.variables.values():
                    for var in var_list:
                        refs = extract_referenced_names(str(var.default))
                        all_referenced_names.update(refs)
                        for r in refs:
                            if not is_valid_reference(r, defined_variables, defined_inputs, defined_software_specs, cleaned_code):
                                broken_template_refs.add(r)

    if hasattr(cls, 'object_variables') and cls.object_variables:
        for var_list in cls.object_variables.values():
            for var in var_list:
                refs = extract_referenced_names(str(var.default))
                all_referenced_names.update(refs)
                for r in refs:
                    if not is_valid_reference(r, defined_variables, defined_inputs, defined_software_specs, cleaned_code):
                        broken_template_refs.add(r)

    # Extract from inputs url/description
    if hasattr(cls, 'inputs') and cls.inputs:
        for inputs_dict in cls.inputs.values():
            for input_obj in inputs_dict.values():
                url = None
                if hasattr(input_obj, 'url'):
                    url = input_obj.url
                elif isinstance(input_obj, dict) and 'url' in input_obj:
                    url = input_obj['url']
                if url:
                    refs = extract_referenced_names(url)
                    all_referenced_names.update(refs)
                    for r in refs:
                        if not is_valid_reference(r, defined_variables, defined_inputs, defined_software_specs, cleaned_code):
                            broken_template_refs.add(r)

    # Extract from figures of merit log_file
    if hasattr(cls, 'figures_of_merit') and cls.figures_of_merit:
        for contexts_dict in cls.figures_of_merit.values():
            for foms_dict in contexts_dict.values():
                for fom_val in foms_dict.values():
                    fom_captures = set()
                    if isinstance(fom_val, dict) and 'fom_regex' in fom_val:
                        try:
                            fom_captures.update(re.compile(fom_val['fom_regex']).groupindex.keys())
                        except Exception:
                            pass
                    if isinstance(fom_val, dict):
                        if 'log_file' in fom_val:
                            refs = extract_referenced_names(fom_val['log_file'])
                            all_referenced_names.update(refs)
                            for r in refs:
                                if not is_valid_reference(r, defined_variables, defined_inputs, defined_software_specs, cleaned_code, fom_captures):
                                    broken_template_refs.add(r)

    # Extract from success criteria files/formulas
    if hasattr(cls, 'success_criteria') and cls.success_criteria:
        for criteria_dict in cls.success_criteria.values():
            if isinstance(criteria_dict, dict):
                if 'file' in criteria_dict:
                    refs = extract_referenced_names(criteria_dict['file'])
                    all_referenced_names.update(refs)
                    for r in refs:
                        if not is_valid_reference(r, defined_variables, defined_inputs, defined_software_specs, cleaned_code):
                            broken_template_refs.add(r)
                if 'formula' in criteria_dict:
                    refs = extract_referenced_names(criteria_dict['formula'])
                    all_referenced_names.update(refs)
                    for r in refs:
                        if not is_valid_reference(r, defined_variables, defined_inputs, defined_software_specs, cleaned_code):
                            broken_template_refs.add(r)

    # Extract from registered templates
    if hasattr(cls, 'templates') and cls.templates:
        for templates_dict in cls.templates.values():
            for tpl_config in templates_dict.values():
                src_path_config = tpl_config.get("src_path")
                if src_path_config:
                    tpl_file = find_template_file(cls, src_path_config)
                    if tpl_file:
                        try:
                            with open(tpl_file, 'r', encoding='utf-8') as f_tpl:
                                tpl_content = f_tpl.read()
                            refs = extract_referenced_names(tpl_content)
                            all_referenced_names.update(refs)
                            for r in refs:
                                if not is_valid_reference(r, defined_variables, defined_inputs, defined_software_specs, cleaned_code):
                                    broken_template_refs.add(r)
                        except Exception:
                            pass

    # 5. Extract workload relationships (executables and inputs used directly in workloads)
    used_executables = set()
    used_inputs = set()
    if hasattr(cls, 'workloads') and cls.workloads:
        for app_workloads in cls.workloads.values():
            for wl_obj in app_workloads.values():
                if hasattr(wl_obj, 'executables'):
                    used_executables.update(wl_obj.executables)
                if hasattr(wl_obj, 'inputs'):
                    used_inputs.update(wl_obj.inputs)

    # Also extract inputs referenced in other inputs/url or variables
    for name in all_referenced_names:
        if name in defined_inputs:
            used_inputs.add(name)

    unused_variables = []
    for var in sorted(defined_variables):
        if var in all_referenced_names:
            continue
        occurrences = len(re.findall(rf'\b{re.escape(var)}\b', cleaned_code))
        defs = len(re.findall(rf'(?:workload_variable|variable)\s*\(\s*[\'"]{re.escape(var)}[\'"]', cleaned_code))
        if occurrences <= defs:
            unused_variables.append(var)

    # For each defined input, check if it's used
    unused_inputs = []
    for inp in sorted(defined_inputs):
        if inp in used_inputs:
            continue
        occurrences = len(re.findall(rf'\b{re.escape(inp)}\b', cleaned_code))
        defs = len(re.findall(rf'input_file\s*\(\s*[\'"]{re.escape(inp)}[\'"]', cleaned_code))
        if occurrences <= defs:
            unused_inputs.append(inp)

    # For each defined executable, check if it's used
    unused_executables = []
    for exe in sorted(defined_executables):
        if exe in used_executables:
            continue
        occurrences = len(re.findall(rf'\b{re.escape(exe)}\b', cleaned_code))
        defs = (
            len(re.findall(rf'executable\s*\(\s*[\'"]{re.escape(exe)}[\'"]', cleaned_code))
            + len(re.findall(rf'edit_file\s*\(\s*[\'"]{re.escape(exe)}[\'"]', cleaned_code))
            + len(re.findall(rf'patch_file\s*\(\s*[\'"]{re.escape(exe)}[\'"]', cleaned_code))
            + len(
                re.findall(
                    rf'formatted_executable\s*\(\s*[\'"]{re.escape(exe)}[\'"]', cleaned_code
                )
            )
        )
        if occurrences <= defs:
            unused_executables.append(exe)

    # Statically parse class body to find unused compilers, broken variables, and workload groups
    unused_compilers = []
    broken_vars = []
    broken_groups = []

    if tree:
        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_node = node
                break

        if class_node:
            for node in class_node.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    call = node.value
                    if isinstance(call.func, ast.Name):
                        func_name = call.func.id

                        # Compiler check
                        if func_name == 'define_compiler' and call.args:
                            compiler_name = get_arg_value(call.args[0])
                            if compiler_name and compiler_name not in all_referenced_compilers:
                                occurrences = len(re.findall(rf'\b{re.escape(compiler_name)}\b', cleaned_code))
                                defs = len(re.findall(rf'define_compiler\s*\(\s*[\'"]{re.escape(compiler_name)}[\'"]', cleaned_code))
                                if occurrences <= defs:
                                    unused_compilers.append(compiler_name)

                        # Variable broken workload/group reference check
                        elif func_name in ('workload_variable', 'variable'):
                            is_broken = False
                            var_name = get_arg_value(call.args[0]) if call.args else None
                            for kw in call.keywords:
                                if kw.arg == 'workload':
                                    wl_val = get_arg_value(kw.value)
                                    if wl_val and wl_val != '*' and not any(fnmatch.fnmatch(w, wl_val) for w in all_defined_workloads):
                                        is_broken = True
                                elif kw.arg == 'workload_group':
                                    wg_val = get_arg_value(kw.value)
                                    if wg_val and wg_val != '*' and not any(fnmatch.fnmatch(g, wg_val) for g in all_defined_workload_groups):
                                        is_broken = True
                                elif kw.arg == 'workloads':
                                    if isinstance(kw.value, ast.List):
                                        for elt in kw.value.elts:
                                            wl_val = get_arg_value(elt)
                                            if wl_val and wl_val != '*' and not any(fnmatch.fnmatch(w, wl_val) for w in all_defined_workloads):
                                                is_broken = True
                            if is_broken and var_name:
                                broken_vars.append(var_name)

                        # Workload group broken workload reference check
                        elif func_name == 'workload_group':
                            group_name = get_arg_value(call.args[0]) if call.args else None
                            for kw in call.keywords:
                                if kw.arg == 'workloads':
                                    if isinstance(kw.value, ast.List):
                                        for elt in kw.value.elts:
                                            wl_val = get_arg_value(elt)
                                            if wl_val and wl_val != '*' and not any(fnmatch.fnmatch(w, wl_val) for w in all_defined_workloads):
                                                broken_groups.append(f"{group_name} -> {wl_val}")

    return unused_variables, unused_inputs, unused_executables, unused_compilers, broken_vars, broken_groups, sorted(broken_template_refs)


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

    total_unused_vars = 0
    total_unused_inputs = 0
    total_unused_execs = 0
    total_unused_compilers = 0
    total_broken_vars = 0

    for name in sorted(names):
        try:
            res = analyze_object(name, obj_type)
            unused_vars, unused_inputs, unused_execs, unused_compilers, broken_vars, broken_groups, broken_templates = res

            if unused_vars or unused_inputs or unused_execs or unused_compilers or broken_vars or broken_groups or broken_templates:
                file_path = obj_path.filename_for_object_name(name)
                color.cprint(f"@c{{=== {args.type.capitalize().rstrip('s')}: {name} ===}}")
                if unused_vars:
                    print(f"  Unused Variables: {unused_vars}")
                    total_unused_vars += len(unused_vars)
                if unused_inputs:
                    print(f"  Unused Inputs: {unused_inputs}")
                    total_unused_inputs += len(unused_inputs)
                if unused_execs:
                    print(f"  Unused Executables: {unused_execs}")
                    total_unused_execs += len(unused_execs)
                if unused_compilers:
                    print(f"  Unused Compilers: {unused_compilers}")
                    total_unused_compilers += len(unused_compilers)
                if broken_vars:
                    print(f"  Variables with Broken Workload/Group Refs: {broken_vars}")
                    total_broken_vars += len(broken_vars)
                if broken_groups:
                    print(f"  Workload Groups with Broken Workload Refs: {broken_groups}")
                if broken_templates:
                    print(f"  Broken Variable References in Templates: {broken_templates}")

                # Locate line ranges to remove (including compilers and broken variables)
                ranges = locate_directive_lines(
                    file_path, unused_vars, unused_inputs, unused_execs, unused_compilers, broken_vars
                )

                if ranges:
                    original_lines, new_lines, new_content = apply_simplifications(
                        file_path, ranges
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
        f"{total_unused_inputs} unused inputs, {total_unused_execs} unused executables, "
        f"{total_unused_compilers} unused compilers, and {total_broken_vars} variables with broken references.}}"
    )

    return 0
