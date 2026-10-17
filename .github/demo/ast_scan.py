#!/usr/bin/env python3
"""Tree-sitter source parsing for the multi-language functional demo."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from tree_sitter_language_pack import get_parser

LANGUAGES = {
    "go": {"calls": {"call_expression"}, "functions": {"function_declaration", "method_declaration", "func_literal"}},
    "python": {"calls": {"call"}, "functions": {"function_definition", "lambda"}},
    "javascript": {"calls": {"call_expression"}, "functions": {"function_declaration", "generator_function_declaration", "method_definition", "function_expression", "arrow_function"}},
    "typescript": {"calls": {"call_expression"}, "functions": {"function_declaration", "generator_function_declaration", "method_definition", "function_expression", "arrow_function"}},
    "java": {"calls": {"method_invocation"}, "functions": {"method_declaration", "constructor_declaration", "lambda_expression"}},
}

def node_text(node: Any, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

def field(node: Any, name: str) -> Any | None:
    return node.child_by_field_name(name)

def call_parts(node: Any, source: bytes) -> tuple[str, str, str]:
    target = field(node, "function")
    object_node = field(node, "object")
    name_node = field(node, "name")
    if target is not None:
        target_text = node_text(target, source)
    elif name_node is not None:
        target_text = (node_text(object_node, source) + "." if object_node is not None else "") + node_text(name_node, source)
        target = object_node or name_node
    else:
        named = list(node.named_children)
        target = named[0] if named else node
        target_text = node_text(target, source)

    receiver_node = None
    method_node = None
    if target is not None:
        for receiver_field, method_field in (
            ("operand", "field"),       # Go selector_expression
            ("object", "attribute"),    # Python attribute
            ("object", "property"),     # JavaScript / TypeScript member_expression
        ):
            r = field(target, receiver_field)
            m = field(target, method_field)
            if r is not None and m is not None:
                receiver_node, method_node = r, m
                break
    if method_node is None and name_node is not None:
        method_node, receiver_node = name_node, object_node

    receiver = node_text(receiver_node, source) if receiver_node is not None else ""
    method = node_text(method_node, source) if method_node is not None else target_text.split(".")[-1]
    return target_text, receiver, method

def enclosing_function(node: Any, source: bytes, language: str) -> str:
    types = LANGUAGES[language]["functions"]
    current = node.parent
    while current is not None:
        if current.type in types:
            name = field(current, "name")
            return node_text(name, source) if name is not None else f"<{current.type}>"
        current = current.parent
    return "<module>"

def classify(receiver: str, method: str) -> tuple[str, str] | None:
    receiver, method = receiver.lower(), method.lower()
    if "anthropic" in receiver and method in {"assess", "createmessage", "generate", "complete", "invoke"}:
        return "synchronous_provider_call", "Syntax shows a direct call to a provider-shaped receiver; this is a syntactic heuristic, not resolved SDK/type behavior."
    if method in {"enqueue", "startexecution", "submitjob", "publish", "sendmessage"}:
        return "async_enqueue", "Syntax shows a method name that suggests queued or workflow handoff; the callee is not resolved."
    if method in {"run", "execute", "handle"}:
        return "delegated_call", "Syntax shows delegation to a helper-shaped method; this file does not establish transitive behavior."
    return None

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--language", required=True, choices=sorted(LANGUAGES))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    path = Path(args.source)
    source = path.read_bytes()
    parser_impl = get_parser(args.language)
    tree = parser_impl.parse(source)
    root = tree.root_node
    if root is None:
        raise SystemExit("Tree-sitter did not return a syntax tree.")

    observations = []
    errors = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "ERROR" or node.is_missing:
            errors.append({
                "node_type": node.type,
                "line": node.start_point.row + 1,
                "column": node.start_point.column + 1,
                "excerpt": node_text(node, source)[:160],
            })
        if node.type in LANGUAGES[args.language]["calls"]:
            target, receiver, method = call_parts(node, source)
            classified = classify(receiver, method)
            if classified:
                outcome, reason = classified
                observations.append({
                    "observation_id": f"TS-{len(observations)+1:03d}",
                    "enclosing_function": enclosing_function(node, source, args.language),
                    "line": node.start_point.row + 1,
                    "column": node.start_point.column + 1,
                    "end_line": node.end_point.row + 1,
                    "end_column": node.end_point.column + 1,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                    "call": target,
                    "expression": node_text(node, source),
                    "receiver_expression": receiver,
                    "method_name": method,
                    "classification": outcome,
                    "classification_basis": "syntactic_heuristic",
                    "reason": reason,
                })
        stack.extend(reversed(node.children))

    digest = hashlib.sha256(source).hexdigest()
    result = {
        "scanner": "tree-sitter-language-pack",
        "scanner_version": "1.22.1",
        "language": args.language,
        "grammar": args.language,
        "source_path": path.as_posix(),
        "source_sha256": digest,
        "parse_status": "parsed_with_errors" if errors else "parsed",
        "root_node_type": root.type,
        "root_has_error": bool(root.has_error),
        "syntax_error_count": len(errors),
        "syntax_errors": errors,
        "observations": sorted(observations, key=lambda item: (item["start_byte"], item["end_byte"])),
        "scope_note": "Tree-sitter parses real language syntax and provides exact source spans. Call labels are receiver/method heuristics; this pass does not type-check, resolve dynamic dispatch, build a transitive call graph, or prove runtime behavior.",
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Tree-sitter ({args.language}): {result['parse_status']}; {len(observations)} classified calls; {len(errors)} syntax errors")
    for item in result["observations"]:
        print(f"  {item['enclosing_function']} {item['line']}:{item['column']} {item['expression']} -> {item['classification']}")
    if errors:
        print("Syntax errors found; see the JSON result for locations.", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
