#!/usr/bin/env python3
"""
Permutative Matrix & Combinatorial Test Case Generator.
Generates Cartesian products and pairwise/orthogonal arrays with constraint filtering.
Supports Python (pytest), TypeScript/JavaScript (Jest/Vitest), Go, Rust, Java (JUnit 5), Markdown, and JSON.
"""

import argparse
import ast
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def safe_eval_filter(expr: str, context: Dict[str, Any]) -> bool:
    """Safely evaluate boolean filter expressions using AST traversal without dynamic evaluation."""
    try:
        node = ast.parse(expr, mode="eval").body
    except SyntaxError:
        return False

    def eval_node(n):
        if isinstance(n, ast.Constant):
            return n.value
        elif isinstance(n, ast.Name):
            return context.get(n.id)
        elif isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            return [eval_node(el) for el in n.elts]
        elif isinstance(n, ast.Compare):
            left = eval_node(n.left)
            for op, comp in zip(n.ops, n.comparators):
                right = eval_node(comp)
                if isinstance(op, ast.Eq) and not (left == right):
                    return False
                elif isinstance(op, ast.NotEq) and not (left != right):
                    return False
                elif isinstance(op, ast.Lt) and not (left < right):
                    return False
                elif isinstance(op, ast.LtE) and not (left <= right):
                    return False
                elif isinstance(op, ast.Gt) and not (left > right):
                    return False
                elif isinstance(op, ast.GtE) and not (left >= right):
                    return False
                elif isinstance(op, ast.In) and not (left in right):
                    return False
                elif isinstance(op, ast.NotIn) and not (left not in right):
                    return False
                left = right
            return True
        elif isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                return all(eval_node(v) for v in n.values)
            elif isinstance(n.op, ast.Or):
                return any(eval_node(v) for v in n.values)
        elif isinstance(n, ast.UnaryOp):
            if isinstance(n.op, ast.Not):
                return not eval_node(n.operand)
        return False

    return bool(eval_node(node))


def load_dimensions(input_str_or_file: str) -> Dict[str, List[Any]]:
    """Load parameter dimensions from inline JSON or file."""
    path = Path(input_str_or_file).expanduser()
    if path.is_file():
        if path.stat().st_size > 5 * 1024 * 1024:
            print("Error: Dimensions file exceeds 5MB size threshold.", file=sys.stderr)
            sys.exit(1)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as err:
            print(f"Error reading dimensions file: {err}", file=sys.stderr)
            sys.exit(1)
    try:
        return json.loads(input_str_or_file)
    except json.JSONDecodeError as err:
        print(f"Error parsing dimensions JSON: {err}", file=sys.stderr)
        sys.exit(1)


def generate_cartesian_matrix(
    dimensions: Dict[str, List[Any]],
    exclude_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate full Cartesian product matrix with optional constraint filtering."""
    keys = list(dimensions.keys())
    value_lists = [dimensions[k] for k in keys]
    product = itertools.product(*value_lists)
    matrix = []

    for combo in product:
        cell = dict(zip(keys, combo))
        if exclude_filter:
            if safe_eval_filter(exclude_filter, cell):
                continue
        matrix.append(cell)

    return matrix


def generate_pairwise_matrix(
    dimensions: Dict[str, List[Any]],
    exclude_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate Pairwise (All-Pairs) covering array.
    Guarantees every 2-way parameter interaction is tested with minimal combinations.
    """
    keys = list(dimensions.keys())
    if len(keys) <= 2:
        return generate_cartesian_matrix(dimensions, exclude_filter)

    # All-pairs greedy heuristic using repr to preserve distinct types
    pairs_to_cover = set()
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            k1, k2 = keys[i], keys[j]
            for v1 in dimensions[k1]:
                for v2 in dimensions[k2]:
                    pairs_to_cover.add(((k1, repr(v1)), (k2, repr(v2))))

    matrix: List[Dict[str, Any]] = []
    full_cartesian = generate_cartesian_matrix(dimensions, exclude_filter)

    remaining_pairs = set(pairs_to_cover)
    for candidate in full_cartesian:
        cand_pairs = set()
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                cand_pairs.add(((keys[i], repr(candidate[keys[i]])), (keys[j], repr(candidate[keys[j]]))))

        covered = cand_pairs.intersection(remaining_pairs)
        if covered:
            matrix.append(candidate)
            remaining_pairs.difference_update(covered)

        if not remaining_pairs:
            break

    if remaining_pairs and len(matrix) < len(full_cartesian):
        for candidate in full_cartesian:
            if candidate not in matrix:
                matrix.append(candidate)
                if len(matrix) >= len(full_cartesian):
                    break

    return matrix if matrix else full_cartesian


def format_pytest(matrix: List[Dict[str, Any]]) -> str:
    """Format combinations as @pytest.mark.parametrize decorator for Python."""
    if not matrix:
        return "# No valid combinations generated."
    keys = list(matrix[0].keys())
    param_names = ", ".join(keys)

    lines = [
        f'@pytest.mark.parametrize("{param_names}", [',
    ]

    for row in matrix:
        vals = [repr(row[k]) for k in keys]
        row_id = "-".join((re.sub(r"[^a-zA-Z0-9_]", "", str(row[k])) or "empty") for k in keys)
        lines.append(f'    pytest.param({", ".join(vals)}, id="{row_id}"),')

    lines.append("])")
    lines.append(f"def test_combinatorial_matrix({param_names}):")
    lines.append("    # Arrange & Act")
    lines.append("    # Assert invariants")
    lines.append("    pass")
    return "\n".join(lines)


def format_jest(matrix: List[Dict[str, Any]]) -> str:
    """Format combinations as test.each table for Jest / Vitest (TypeScript/JavaScript)."""
    if not matrix:
        return "// No valid combinations generated."
    keys = list(matrix[0].keys())

    lines = [
        "test.each([",
    ]

    for row in matrix:
        obj_repr = json.dumps(row)
        row_id = "-".join((re.sub(r"[^a-zA-Z0-9_]", "", str(row[k])) or "empty") for k in keys)
        lines.append(f"  [{obj_repr}, '{row_id}'],")

    lines.append("])('evaluates matrix cell %s [%s]', (params, id) => {")
    lines.append("  // Arrange & Act")
    lines.append("  // Assert invariants")
    lines.append("});")
    return "\n".join(lines)


def format_go(matrix: List[Dict[str, Any]]) -> str:
    """Format combinations as a Go table-driven test slice."""
    if not matrix:
        return "// No valid combinations generated."
    keys = list(matrix[0].keys())

    lines = [
        "tests := []struct {",
        "    name string",
    ]
    for k in keys:
        val = matrix[0][k]
        if isinstance(val, bool):
            type_str = "bool"
        elif isinstance(val, int):
            type_str = "int"
        elif isinstance(val, float):
            type_str = "float64"
        else:
            type_str = "string"
        lines.append(f"    {k} {type_str}")
    lines.append("}{")

    for row in matrix:
        name = "-".join((re.sub(r"[^a-zA-Z0-9_]", "", str(row[k])) or "empty") for k in keys)
        field_strs = []
        for k in keys:
            v = row[k]
            if isinstance(v, str):
                field_strs.append(f'{k}: "{v}"')
            elif isinstance(v, bool):
                field_strs.append(f"{k}: {str(v).lower()}")
            else:
                field_strs.append(f"{k}: {v}")
        lines.append(f'    {{name: "{name}", {", ".join(field_strs)}}},')

    lines.append("}")
    lines.append("for _, tt := range tests {")
    lines.append('    t.Run(tt.name, func(t *testing.T) {')
    lines.append("        // Execute test case")
    lines.append("    })")
    lines.append("}")
    return "\n".join(lines)


def format_rust(matrix: List[Dict[str, Any]]) -> str:
    """Format combinations as a Rust test table vector."""
    if not matrix:
        return "// No valid combinations generated."
    keys = list(matrix[0].keys())

    lines = [
        "#[derive(Debug)]",
        "struct TestCase {",
        "    name: &'static str,",
    ]
    for k in keys:
        val = matrix[0][k]
        if isinstance(val, bool):
            type_str = "bool"
        elif isinstance(val, int):
            type_str = "i64"
        elif isinstance(val, float):
            type_str = "f64"
        else:
            type_str = "&'static str"
        lines.append(f"    {k}: {type_str},")
    lines.append("}")
    lines.append("")
    lines.append("let test_cases = vec![")

    for row in matrix:
        name = "-".join((re.sub(r"[^a-zA-Z0-9_]", "", str(row[k])) or "empty") for k in keys)
        field_strs = []
        for k in keys:
            v = row[k]
            if isinstance(v, str):
                field_strs.append(f'{k}: "{v}"')
            elif isinstance(v, bool):
                field_strs.append(f"{k}: {str(v).lower()}")
            else:
                field_strs.append(f"{k}: {v}")
        lines.append(f'    TestCase {{ name: "{name}", {", ".join(field_strs)} }},')

    lines.append("];")
    lines.append("for tc in test_cases {")
    lines.append("    // Assert test case invariants")
    lines.append("}")
    return "\n".join(lines)


def format_junit(matrix: List[Dict[str, Any]]) -> str:
    """Format combinations as JUnit 5 @CsvSource for Java / Kotlin."""
    if not matrix:
        return "// No valid combinations generated."
    keys = list(matrix[0].keys())

    lines = [
        "@ParameterizedTest",
        "@CsvSource({",
    ]
    for row in matrix:
        vals = ", ".join(str(row[k]) for k in keys)
        lines.append(f'    "{vals}",')
    lines.append("})")
    param_sig = ", ".join(f"String {k}" for k in keys)
    lines.append(f"void testCombinatorialMatrix({param_sig}) {{")
    lines.append("    // Arrange & Act")
    lines.append("    // Assert invariants")
    lines.append("}")
    return "\n".join(lines)


def format_markdown(matrix: List[Dict[str, Any]]) -> str:
    """Format combinations as a Markdown table."""
    if not matrix:
        return "No combinations generated."
    keys = list(matrix[0].keys())
    header = "| # | " + " | ".join(keys) + " | Expected Outcome |"
    separator = "|---|" + "|".join(["---"] * len(keys)) + "|---|"
    lines = [header, separator]

    for idx, row in enumerate(matrix, start=1):
        vals = " | ".join(str(row[k]) for k in keys)
        lines.append(f"| {idx} | {vals} | `PASS` / `REJECT` |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Combinatorial & Permutative Test Matrix Generator")
    parser.add_argument("dimensions", help="Inline JSON string or path to JSON file specifying parameter dimensions")
    parser.add_argument(
        "--format",
        choices=["pytest", "jest", "go", "rust", "junit", "markdown", "json"],
        default="pytest",
        help="Output format (default: pytest)",
    )
    parser.add_argument(
        "--pairwise",
        action="store_true",
        help="Generate minimal Pairwise/Orthogonal covering array instead of full Cartesian product",
    )
    parser.add_argument(
        "--filter",
        help="Boolean expression to exclude impossible domain combinations (e.g. \"role == 'guest' and status == 'admin'\")",
    )
    parser.add_argument("--out", help="Write output to file instead of stdout")

    args = parser.parse_args()
    dims = load_dimensions(args.dimensions)

    if not isinstance(dims, dict) or not all(isinstance(v, list) for v in dims.values()):
        print("Error: Dimensions must be a JSON object mapping parameter names to lists of values.", file=sys.stderr)
        sys.exit(1)

    if args.pairwise:
        matrix = generate_pairwise_matrix(dims, exclude_filter=args.filter)
    else:
        matrix = generate_cartesian_matrix(dims, exclude_filter=args.filter)

    if args.format == "pytest":
        output = format_pytest(matrix)
    elif args.format == "jest":
        output = format_jest(matrix)
    elif args.format == "go":
        output = format_go(matrix)
    elif args.format == "rust":
        output = format_rust(matrix)
    elif args.format == "junit":
        output = format_junit(matrix)
    elif args.format == "markdown":
        output = format_markdown(matrix)
    elif args.format == "json":
        output = json.dumps(matrix, indent=2)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Generated {len(matrix)} test combinations to: {out_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
