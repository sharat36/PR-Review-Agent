# param_type_analyzer.py
import re
from collections import defaultdict
from infer_type_ai import infer_type_ai


def extract_function_definitions(code):
    pattern = re.compile(r'function\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)
    functions = {}
    for match in pattern.finditer(code):
        name, args = match.groups()
        arg_list = [arg.strip().split(" $")[-1] for arg in args.split(',') if arg.strip()]
        functions[name] = {'params': arg_list, 'body': '', 'assignments': {}, 'calls': []}

    func_blocks = list(re.finditer(r'function\s+\w+\s*\([^)]*\)\s*\{', code))
    for i, match in enumerate(func_blocks):
        start = match.end()
        end = func_blocks[i + 1].start() if i + 1 < len(func_blocks) else len(code)
        body = code[start:end]
        name = re.search(r'function\s+(\w+)', match.group()).group(1)
        functions[name]['body'] = body
        assign_pattern = re.compile(r'\$(\w+)\s*=\s*([^;]+);')
        for assign_match in assign_pattern.finditer(body):
            var, val = assign_match.groups()
            functions[name]['assignments'][var] = val.strip()

    return functions


def extract_function_calls(code):
    pattern = re.compile(r'(\w+)\s*\((.*?)\);', re.MULTILINE)
    calls = defaultdict(list)
    for match in pattern.finditer(code):
        func_name, args = match.groups()
        args = [arg.strip() for arg in args.split(',') if arg.strip()]
        calls[func_name].append(args)
    return calls


def infer_type(expr):
    expr = expr.strip()
    if '??' in expr:
        parts = expr.split('??')
        return infer_type(parts[-1])
    elif re.match(r'^\$\w+\[\'"].+?[\'"\]]', expr):
        return 'array_key'
    elif '->' in expr:
        return 'object_property'
    elif expr.startswith("'") or expr.startswith('"'):
        return 'string'
    elif expr.startswith('[') or expr.startswith('array('):
        return 'array'
    elif re.match(r'^\d+$', expr):
        return 'int'
    elif expr.startswith('new '):
        return 'class'
    elif expr in ['true', 'false']:
        return 'bool'
    elif expr == 'null':
        return 'null'
    else:
        return 'variable'


def resolve_param_types(functions, calls):
    param_types = defaultdict(lambda: defaultdict(list))

    def resolve(func_name, passed_args, depth=0, visited=None):
        if visited is None:
            visited = set()
        if depth > 10 or func_name in visited:
            return
        visited.add(func_name)

        if func_name not in functions:
            return

        param_list = functions[func_name]['params']
        assignments = functions[func_name]['assignments']
        body = functions[func_name]['body']

        for i, param in enumerate(param_list):
            if i < len(passed_args):
                value = passed_args[i]
                t = infer_type(value)

                if t in ('variable', 'array_key', 'object_property', 'unknown'):
                    t = infer_type_ai(value, context_code=body)

                param_types[func_name][param].append(t)

                if t == 'variable':
                    var_name = value.strip("$")
                    for called_func, arglists in calls.items():
                        for args in arglists:
                            for arg in args:
                                if arg.strip("$") == var_name:
                                    resolve(called_func, args, depth + 1, visited.copy())

    for caller, arglists in calls.items():
        for args in arglists:
            resolve(caller, args)

    return param_types


def find_odd_types(param_types):
    oddities = {}
    for func, params in param_types.items():
        for param, types in params.items():
            type_counts = defaultdict(int)
            for t in types:
                type_counts[t] += 1
            if len(type_counts) > 1:
                oddities[f"{func}::${param}"] = dict(type_counts)
    return oddities
