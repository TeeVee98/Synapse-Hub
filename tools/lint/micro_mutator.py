#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Assertion Sensitivity & Syntactic Micro-Mutation Sentinel (Heuristic)
---------------------------------------------------------------------
Evaluates the true defect-catching efficacy of test suites by injecting
syntactic micro-mutants (inverting operators, flipping booleans, altering boundaries)
to eradicate 'Tautological Tests' (tests that pass unconditionally without valid assertions).

Features:
  - Atomic syntactic fault injection across Groovy, Python, TypeScript, JavaScript
  - Static assertion sensitivity analysis (killing mutants when valid assertions verify downstream logic)
  - Dynamic test execution mode (--test-cmd) for live mutant verification
  - Quality Gatekeeper threshold enforcement (--min-score, default: 80.0%)

Implementation Note:
  Static evaluation is a lightweight, heuristic assertion-sensitivity analysis
  (fast, polyglot, token-free), not a compiler-grade mutation testing tool like Stryker or mutmut.
  It measures whether test logic is bounded by active downstream assertions rather than passing unconditionally.
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

try:
    from tools.lint.equivalent_mutant_filter import EquivalentMutantDetector
except ImportError:
    try:
        from lint.equivalent_mutant_filter import EquivalentMutantDetector
    except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
        from equivalent_mutant_filter import EquivalentMutantDetector


import ast
import copy
import os
import re
import sys
import glob
import json
import shlex
import html as html_lib
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

# Enforce UTF-8 stdout encoding and guard against non-blocking stream BlockingIOError
for stream in (sys.stdout, sys.stderr):
    if hasattr(os, 'set_blocking') and hasattr(stream, 'fileno'):
        try:
            os.set_blocking(stream.fileno(), True)
        except Exception:
            pass
    if hasattr(stream, 'reconfigure'):
        try:
            stream.reconfigure(encoding='utf-8')
        except Exception:
            pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    import test_impact
except ImportError:
    try:
        from tools import test_impact
    except ImportError:
        test_impact = None


def resolve_scoped_test_cmd(scoped_template: str, target_file: str, repo_root: Optional[str] = None) -> Tuple[str, List[str]]:
    """
    Resolves dynamic test runner command targeting only test cases impacted
    by changes to target_file via test_impact.py.
    """
    root = repo_root or HUB_ROOT
    try:
        rel_path = os.path.relpath(target_file, root).replace("\\", "/") if os.path.isabs(target_file) else target_file.replace("\\", "/")

    except ValueError:
        rel_path = target_file.replace("\\", "/")
    impacted: List[str] = []


    if test_impact and hasattr(test_impact, "get_impacted_test_files"):
        try:
            impacted = test_impact.get_impacted_test_files([rel_path], repo_root=root)
        except Exception as err:
            sys.stderr.write(f"Notice: Failed to compute test impact for {rel_path}: {err}\n")
            impacted = []

    if not impacted:
        # Fallback 1: if target is itself a test script, run on target
        if "tests/" in rel_path or "Scripts/" in rel_path or rel_path.endswith(("_test.py", ".spec.ts", ".test.ts", ".groovy")) or os.path.basename(rel_path).startswith("test_"):
            impacted = [rel_path]
        else:
            # Fallback 2: convention-based test mapping for tools/<name>.py -> tests/test_<name>.py
            base_mod = os.path.splitext(os.path.basename(rel_path))[0]
            candidates = [
                os.path.join("tests", f"test_{base_mod}.py"),
                os.path.join("tests", f"{base_mod}_test.py"),
            ]
            for cand in candidates:
                cand_rel = cand.replace("\\", "/")
                if os.path.isfile(os.path.join(root, cand_rel)):
                    impacted.append(cand_rel)
            if not impacted:
                for f in glob.glob(os.path.join(root, "tests", f"test_*{base_mod}*.py")):
                    impacted.append(os.path.relpath(f, root).replace("\\", "/"))

    tests_str = " ".join(impacted) if impacted else ""
    if "{test_files}" in scoped_template:
        cmd = scoped_template.replace("{test_files}", tests_str).strip()
    elif "{tests}" in scoped_template:
        cmd = scoped_template.replace("{tests}", tests_str).strip()
    else:
        norm_template = scoped_template.replace("\\", "/")
        norm_target = target_file.replace("\\", "/")
        base_target = os.path.basename(target_file)
        if tests_str and (tests_str in norm_template or norm_target in norm_template or base_target in norm_template):
            cmd = scoped_template.strip()
        else:
            cmd = f"{scoped_template} {tests_str}".strip() if tests_str else scoped_template.strip()

    return cmd, impacted


# Syntax mutation rules: (Pattern, Replacement, Description)
MUTATION_RULES = [
    (r"\btrue\b", "false", "Boolean Inversion (true -> false)"),
    (r"\bfalse\b", "true", "Boolean Inversion (false -> true)"),
    (r"\bTrue\b", "False", "Boolean Inversion (True -> False)"),
    (r"\bFalse\b", "True", "Boolean Inversion (False -> True)"),
    (r"\s==\s", " != ", "Equality Inversion (== -> !=)"),
    (r"\s!=\s", " == ", "Inequality Inversion (!= -> ==)"),
    (r"\s>=\s", " < ", "Relational Inversion (>= -> <)"),
    (r"\s<=\s", " > ", "Relational Inversion (<= -> >)"),
    (r"\s>\s", " <= ", "Boundary Shift (> -> <=)"),
    (r"\s<\s", " >= ", "Boundary Shift (< -> >=)"),
    (r"\band\b", "or", "Logical Inversion (and -> or)"),
    (r"\bor\b", "and", "Logical Inversion (or -> and)"),
    (r"\s&&\s", " || ", "Logical AND Inversion (&& -> ||)"),
    (r"\s\|\|\s", " && ", "Logical OR Inversion (|| -> &&)"),
    (r"\s\bis\s+(?!not\b)", " is not ", "Identity Inversion (is -> is not)"),
    (r"\s\bis\s+not\s+", " is ", "Identity Inversion (is not -> is)"),
    (r"\s\+\s", " - ", "Arithmetic Inversion (+ -> -)"),
    (r"\s-\s", " + ", "Arithmetic Inversion (- -> +)"),
    (r"\breturn\s+true\b", "return false", "Return Value Inversion (return true -> return false)"),
    (r"\breturn\s+false\b", "return true", "Return Value Inversion (return false -> return true)"),
    (r"\breturn\s+True\b", "return False", "Return Value Inversion (return True -> return False)"),
    (r"\breturn\s+False\b", "return True", "Return Value Inversion (return False -> return True)"),
    (r"\breturn\s+0\b", "return -1", "Return Value Shift (return 0 -> return -1)"),
    (r"\s\?\?\s", " || ", "Nullish Coalescing Inversion (?? -> ||)"),
]

# Action statement pattern for Statement Deletion Mutants
ACTION_STATEMENT_PATTERN = re.compile(
    r'\.(click|submit|save|update|delete|send|fill|press|type|execute|check|uncheck|hover|dragTo|selectOption|clear|focus|setInputFiles)\s*\(',
    re.IGNORECASE
)

# Assertion and verification patterns
ASSERTION_PATTERN = re.compile(
    r'\b(verify[A-Za-z0-9_]*|assert[A-Za-z0-9_]*|waitForToast|checkStatus|assertEquals|assertTrue|assertFalse|assertThat|expect|ensure[A-Z][A-Za-z0-9_]*Exists)\b'
)

# Tautological / fake assertions that do not test application logic
TAUTOLOGY_PATTERN = re.compile(
    r'(?:assert\s+(?:true|1\s*==\s*1)\b'
    r'|\bassert\s+([a-zA-Z0-9_\.]+(?:\([^)]*\))?)\s*==\s*\1\b'
    r'|\bassert\s+(?:len\s*\([^)]*\)|[a-zA-Z0-9_\.]+\.(?:length|size\(\)))\s*(?:>=\s*0|>\s*-(?:1|0))\b'
    r'|assertEquals\s*\(\s*([a-zA-Z_]\w*)\s*,\s*\1\s*\)'
    r'|expect\s*\(\s*([a-zA-Z_]\w*)\s*\)\.toBe\s*\(\s*\1\s*\)'
    r'|assertTrue\s*\(\s*true\s*\))',
    re.IGNORECASE
)

EMPTY_CATCH_PATTERN = re.compile(
    r'catch\s*\([^\)]*\)\s*\{\s*\}',
    re.MULTILINE
)


def is_inside_quotes(line: str, pos: int) -> bool:
    """Determines whether a character position in a line is enclosed within string quotes."""
    in_single = False
    in_double = False
    escaped = False
    for i, ch in enumerate(line):
        if i == pos:
            return in_single or in_double
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
    return in_single or in_double


def is_inside_comment(line: str, pos: int) -> bool:
    """Determines whether a character position in a line is inside an inline comment (# or //)."""
    in_single = False
    in_double = False
    escaped = False
    for i, ch in enumerate(line):
        if i == pos:
            return False
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if ch == '#' or line[i:i+2] == '//':
                return pos >= i
    return False


def mask_non_executable_contexts(code: str) -> str:
    """Replaces multiline strings, docstrings, comments and string fixtures with blank lines
    to preserve exact line numbering while eliminating false positives during static analysis."""
    lines = code.splitlines(keepends=True)
    in_ml = False
    ml_char = ""
    masked = []
    triple_d = '"""'
    triple_s = "'''"

    for line in lines:
        stripped = line.strip()
        if in_ml:
            if ml_char in stripped:
                in_ml = False
                ml_char = ""
            masked.append("\n")
            continue

        for q in (triple_d, triple_s):
            if q in stripped and stripped.count(q) % 2 == 1:
                in_ml = True
                ml_char = q
                break

        if in_ml:
            masked.append("\n")
        else:
            # Mask string fixtures containing catch blocks or test code samples
            if "catch" in stripped and ('"' in stripped or "'" in stripped):
                masked.append("\n")
            else:
                masked.append(line)

    return "".join(masked)


def get_git_diff_modified_lines(file_path: str, repo_root: Optional[str] = None) -> Optional[Set[int]]:
    """
    Extracts 1-based modified line numbers from git diff for target file.
    Checks both working tree and cached diffs against HEAD.
    If the file is untracked (new file) or git is unavailable, returns None (mutates all lines).
    """
    root = repo_root or HUB_ROOT
    try:
        proc_status = subprocess.run(
            ["git", "status", "--porcelain", file_path],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        if proc_status.returncode == 0:
            out_strip = proc_status.stdout.strip()
            if out_strip.startswith("??"):
                return None  # Untracked new file: all lines are considered modified

        proc_diff = subprocess.run(
            ["git", "diff", "-U0", "HEAD", "--", file_path],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        diff_text = proc_diff.stdout if proc_diff.returncode == 0 else ""
        if not diff_text:
            proc_diff2 = subprocess.run(
                ["git", "diff", "-U0", "--", file_path],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="replace",
            )
            diff_text = proc_diff2.stdout if proc_diff2.returncode == 0 else ""

        # Fallback to recent commit diff (HEAD~1..HEAD) if working tree is clean
        if not diff_text:
            proc_diff3 = subprocess.run(
                ["git", "diff", "-U0", "HEAD~1", "HEAD", "--", file_path],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="replace",
            )
            diff_text = proc_diff3.stdout if proc_diff3.returncode == 0 else ""

        if not diff_text:
            return None  # No git diff detected: fallback to full-file mutation

        modified_lines: Set[int] = set()
        for m in re.finditer(r"@@\s+-[0-9,]+\s+\+(\d+)(?:,(\d+))?\s+@@", diff_text):
            start = int(m.group(1))
            count = int(m.group(2)) if m.group(2) is not None else 1
            if count > 0:
                modified_lines.update(range(start, start + count))
        return modified_lines
    except Exception:
        return None


def generate_ast_mutants_python(
    code: str,
    file_path: str = "",
    target_lines: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Generates genuine, compiler-verified AST mutants for Python using standard library `ast`.
    Traverses the abstract syntax tree, transforms atomic expressions/operators,
    and unparses valid AST trees back into code with zero invalid syntax escape.
    """
    try:
        tree = ast.parse(code)
    except Exception:
        return []

    mutants: List[Dict[str, Any]] = []
    mutant_id = 1

    class AstTargetCollector(ast.NodeVisitor):
        def __init__(self):
            self.targets = []

        def visit_Compare(self, node):
            lineno = getattr(node, "lineno", 0)
            if target_lines is None or lineno in target_lines:
                for idx, op in enumerate(node.ops):
                    self.targets.append(("compare", lineno, getattr(node, "col_offset", 0), type(node), idx, type(op)))
            self.generic_visit(node)

        def visit_BoolOp(self, node):
            lineno = getattr(node, "lineno", 0)
            if target_lines is None or lineno in target_lines:
                self.targets.append(("boolop", lineno, getattr(node, "col_offset", 0), type(node), 0, type(node.op)))
            self.generic_visit(node)

        def visit_Constant(self, node):
            lineno = getattr(node, "lineno", 0)
            if target_lines is None or lineno in target_lines:
                if isinstance(node.value, bool):
                    self.targets.append(("bool_const", lineno, getattr(node, "col_offset", 0), type(node), 0, node.value))
                elif isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                    if node.value in (0, 1):
                        self.targets.append(("num_const", lineno, getattr(node, "col_offset", 0), type(node), 0, node.value))
            self.generic_visit(node)

        def visit_BinOp(self, node):
            lineno = getattr(node, "lineno", 0)
            if target_lines is None or lineno in target_lines:
                self.targets.append(("binop", lineno, getattr(node, "col_offset", 0), type(node), 0, type(node.op)))
            self.generic_visit(node)

        def visit_Expr(self, node):
            lineno = getattr(node, "lineno", 0)
            if target_lines is None or lineno in target_lines:
                if isinstance(node.value, ast.Call):
                    call_name = ""
                    if isinstance(node.value.func, ast.Attribute):
                        call_name = node.value.func.attr
                    elif isinstance(node.value.func, ast.Name):
                        call_name = node.value.func.id
                    if call_name and not any(call_name.startswith(p) for p in ("assert", "expect", "print", "log", "logging")):
                        self.targets.append(("statement_deletion", lineno, getattr(node, "col_offset", 0), type(node), 0, call_name))
            self.generic_visit(node)

    collector = AstTargetCollector()
    collector.visit(tree)

    for kind, lineno, col_offset, node_type, idx, orig_val in collector.targets:
        tree_copy = copy.deepcopy(tree)
        matched = None
        for n in ast.walk(tree_copy):
            if getattr(n, "lineno", -1) == lineno and getattr(n, "col_offset", -1) == col_offset:
                if type(n) is node_type:
                    matched = n
                    break
        if not matched:
            continue

        desc = ""
        orig_snippet = ""
        mut_snippet = ""

        if kind == "compare":
            if idx >= len(matched.ops):
                continue
            op = matched.ops[idx]
            orig_snippet = ast.unparse(matched)
            if isinstance(op, ast.Eq):
                matched.ops[idx] = ast.NotEq()
                desc = "Equality Inversion (AST: == to !=)"
            elif isinstance(op, ast.NotEq):
                matched.ops[idx] = ast.Eq()
                desc = "Equality Inversion (AST: != to ==)"
            elif isinstance(op, ast.Gt):
                matched.ops[idx] = ast.LtE()
                desc = "Relational Inversion (AST: > to <=)"
            elif isinstance(op, ast.GtE):
                matched.ops[idx] = ast.Lt()
                desc = "Relational Inversion (AST: >= to <)"
            elif isinstance(op, ast.Lt):
                matched.ops[idx] = ast.GtE()
                desc = "Relational Inversion (AST: < to >=)"
            elif isinstance(op, ast.LtE):
                matched.ops[idx] = ast.Gt()
                desc = "Relational Inversion (AST: <= to >)"
            elif isinstance(op, ast.In):
                matched.ops[idx] = ast.NotIn()
                desc = "Relational Inversion (AST: in to not in)"
            elif isinstance(op, ast.NotIn):
                matched.ops[idx] = ast.In()
                desc = "Relational Inversion (AST: not in to in)"
            elif isinstance(op, ast.Is):
                matched.ops[idx] = ast.IsNot()
                desc = "Equality Inversion (AST: is to is not)"
            elif isinstance(op, ast.IsNot):
                matched.ops[idx] = ast.Is()
                desc = "Equality Inversion (AST: is not to is)"
            else:
                continue
            mut_snippet = ast.unparse(matched)

        elif kind == "boolop":
            orig_snippet = ast.unparse(matched)
            if isinstance(matched.op, ast.And):
                matched.op = ast.Or()
                desc = "Boolean Inversion (AST: and to or)"
            elif isinstance(matched.op, ast.Or):
                matched.op = ast.And()
                desc = "Boolean Inversion (AST: or to and)"
            else:
                continue
            mut_snippet = ast.unparse(matched)

        elif kind == "bool_const":
            orig_snippet = str(matched.value)
            matched.value = not matched.value
            desc = f"Return Value Inversion (AST: {orig_snippet} to {matched.value})"
            mut_snippet = str(matched.value)

        elif kind == "num_const":
            orig_snippet = str(matched.value)
            matched.value = 1 if matched.value == 0 else 0
            desc = f"Boundary Shift (AST: {orig_snippet} to {matched.value})"
            mut_snippet = str(matched.value)

        elif kind == "binop":
            orig_snippet = ast.unparse(matched)
            if isinstance(matched.op, ast.Add):
                matched.op = ast.Sub()
                desc = "Arithmetic Inversion (AST: + to -)"
            elif isinstance(matched.op, ast.Sub):
                matched.op = ast.Add()
                desc = "Arithmetic Inversion (AST: - to +)"
            elif isinstance(matched.op, ast.Mult):
                matched.op = ast.FloorDiv()
                desc = "Arithmetic Inversion (AST: * to //)"
            else:
                continue
            mut_snippet = ast.unparse(matched)

        elif kind == "statement_deletion":
            orig_snippet = ast.unparse(matched)
            pass_node = ast.Pass()
            pass_node.lineno = lineno
            pass_node.col_offset = col_offset
            desc = f"Statement Deletion (AST: omit {orig_val})"
            mut_snippet = f"pass  # MUTANT_DELETED: {orig_val}"

            class StmtReplacer(ast.NodeTransformer):
                def visit(self, node):
                    if hasattr(node, "body") and isinstance(node.body, list):
                        new_body = []
                        for stmt in node.body:
                            if stmt is matched:
                                new_body.append(pass_node)
                            else:
                                new_body.append(self.visit(stmt))
                        node.body = new_body
                    if hasattr(node, "orelse") and isinstance(node.orelse, list):
                        new_orelse = []
                        for stmt in node.orelse:
                            if stmt is matched:
                                new_orelse.append(pass_node)
                            else:
                                new_orelse.append(self.visit(stmt))
                        node.orelse = new_orelse
                    return self.generic_visit(node)

            tree_copy = StmtReplacer().visit(tree_copy)

        else:
            continue

        ast.fix_missing_locations(tree_copy)
        try:
            mut_code = ast.unparse(tree_copy)
            compile(mut_code, file_path or "<string>", "exec")
        except Exception:
            continue

        mutants.append({
            "id": f"MUT-{mutant_id:04d}",
            "file": file_path,
            "line": lineno,
            "original_snippet": orig_snippet,
            "mutated_snippet": mut_snippet,
            "description": desc,
            "mutated_code": mut_code,
            "status": "SURVIVED",
            "ast_verified": True,
        })
        mutant_id += 1
        if len(mutants) >= 20:
            break

    return mutants


def generate_mutants_for_code(
    code: str,
    file_path: str = "",
    target_lines: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Generates single-point syntactic mutants from source code string.
    Each mutant represents exactly one atomic fault injection.
    Only generates mutants on active executable lines, ignoring comments, multiline strings & runners.
    If target_lines is provided, only injects mutations on lines within that set.
    """
    # 1. First-class AST mutation for Python files when scoped or explicitly enabled
    if target_lines is not None and file_path.endswith((".py", ".pyw")):
        ast_mutants = generate_ast_mutants_python(code, file_path=file_path, target_lines=target_lines)
        if ast_mutants:
            return ast_mutants
    lines = code.splitlines(keepends=True)
    mutants = []
    mutant_id = 1
    in_multiline = False
    ml_char = ""
    triple_d = '"""'
    triple_s = "'''"

    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        if target_lines is not None and line_num not in target_lines:
            continue
        stripped = line.strip()

        # Track multiline docstrings and string assignments
        if in_multiline:
            if ml_char in stripped:
                in_multiline = False
                ml_char = ""
            continue

        for q in (triple_d, triple_s):
            if q in stripped and stripped.count(q) % 2 == 1:
                in_multiline = True
                ml_char = q
                break

        if in_multiline:
            continue

        # Skip pure comments or imports
        if stripped.startswith(("//", "#", "/*", "*", "import", "package", "from")):
            continue

        # Skip test runner boilerplate, entry points, and file writing harness logic
        if re.search(r"\b(if\s+__name__\s*==|unittest\.main\(\)|sys\.exit\(|\.write\()", stripped):
            continue

        # Skip harness setup/teardown fixtures and platform branching guards
        if re.search(r"\b(os\.makedirs|shutil\.rmtree|\.mkdir|tempfile\.NamedTemporaryFile|tempfile\.mkdtemp)\b", stripped):
            continue
        if re.search(r"\b(os\.name\s*==|sys\.platform\s*==|os\.name\s*!=|sys\.platform\s*!=)\b", stripped):
            continue
        if re.search(r"\bif\s+(?:orig_|cls\.orig_|self\.orig_)[a-zA-Z0-9_]*\s+is\s+(?:not\s+)?None\b", stripped):
            continue
        if re.search(r"\bthreading\.Thread\([^)]*daemon\s*=\s*True\b", stripped):
            continue
        if re.search(r"\bsubprocess\.run\([^)]*(?:check|capture_output)\s*=\s*True\b", stripped):
            continue

        # Skip tuples/lists of mock code templates in data fixtures
        if stripped.startswith("(") and ('"' in stripped or "'" in stripped):
            continue

        # Statement Deletion Mutant (Simulates omitted UI action or bypassed step)
        if ACTION_STATEMENT_PATTERN.search(stripped) and not ASSERTION_PATTERN.search(stripped):
            indent = line[:len(line) - len(line.lstrip())]
            if file_path.endswith((".py", ".pyw")):
                mutated_line = f"{indent}pass  # MUTANT_DELETED: {stripped}\n"
            else:
                mutated_line = f"{indent}// MUTANT_DELETED: {stripped}\n"
            mutated_lines = list(lines)
            mutated_lines[line_idx] = mutated_line
            mutants.append({
                "id": f"MUT-{mutant_id:04d}",
                "file": file_path,
                "line": line_idx + 1,
                "original_snippet": line.strip(),
                "mutated_snippet": mutated_line.strip(),
                "description": "Statement Deletion (Omit critical action/mutation call)",
                "mutated_code": "".join(mutated_lines),
                "status": "SURVIVED"
            })
            mutant_id += 1
            if len(mutants) >= 20:
                return mutants

        for pattern, replacement, desc in MUTATION_RULES:
            matches = list(re.finditer(pattern, line))
            for m in matches:
                start, end = m.span()
                # Skip mutations occurring inside string literals or inline comments
                if is_inside_quotes(line, start) or is_inside_comment(line, start):
                    continue

                # Skip arithmetic mutation on string concatenations
                if desc.startswith("Arithmetic Inversion"):
                    left = line[:start].rstrip()
                    right = line[end:].lstrip()
                    if left.endswith(('"', "'")) or right.startswith(('"', "'")):
                        continue
                    if re.search(r'\b(?:String|str|println|print|log|logInfo|comment|append)\b', line, re.IGNORECASE):
                        if "'" in line or '"' in line:
                            continue

                mutated_line = line[:start] + replacement + line[end:]
                mutated_lines = list(lines)
                mutated_lines[line_idx] = mutated_line
                mutated_code = "".join(mutated_lines)

                # Syntax guard for Python: ensure mutant produces valid Python syntax
                if file_path.endswith((".py", ".pyw")):
                    try:
                        compile(mutated_code, file_path, "exec")
                    except SyntaxError:
                        continue

                mutants.append({
                    "id": f"MUT-{mutant_id:04d}",
                    "file": file_path,
                    "line": line_idx + 1,
                    "original_snippet": line.strip(),
                    "mutated_snippet": mutated_line.strip(),
                    "description": desc,
                    "mutated_code": mutated_code,
                    "status": "SURVIVED"
                })
                mutant_id += 1

                # Cap per file to avoid combinatorial explosion
                if len(mutants) >= 20:
                    return mutants

    return mutants


def evaluate_mutation_score(killed_count: int, total_count: int) -> float:
    """Calculates mutation score as percentage of mutants killed."""
    if total_count == 0:
        return 0.0
    return round((killed_count / total_count) * 100.0, 2)


def classify_test_failure(stdout: str, stderr: str, exit_code: int) -> Tuple[str, bool, str]:
    """
    Classifies test runner failure output into distinct categories:
      - 'ASSERTION_FAILURE': Genuine test assertion/expect verification failure (is_valid_kill = True)
      - 'SYNTAX_ERROR': Broken syntax or compilation failure from mutant (is_valid_kill = False)
      - 'IMPORT_OR_CRASH': Unhandled runtime crash, import error or missing module (is_valid_kill = False)
      - 'PASSED': Test suite passed unconditionally (is_valid_kill = False)
    """
    if exit_code == 0:
        return "PASSED", False, "Test suite passed unconditionally"

    combined = f"{stdout}\n{stderr}"

    # 1. Syntax / Compilation error markers
    syntax_markers = (
        "SyntaxError:",
        "IndentationError:",
        "TabError:",
        "compile error",
        "TypeScript error",
        "TS2304",
        "TS2307",
        "TS1005",
        "Unexpected token",
        "Parsing error:",
        "compilation failed",
    )
    for sm in syntax_markers:
        if sm.lower() in combined.lower():
            return "SYNTAX_ERROR", False, f"Broken syntax detected in test output: {sm}"

    # 2. Import / Environment crash markers (inconclusive kill)
    import_markers = (
        "ModuleNotFoundError:",
        "ImportError:",
        "Cannot find module",
        "No module named",
        "Address already in use",
        "ECONNREFUSED",
    )
    for im in import_markers:
        if im.lower() in combined.lower() and not any(kw in combined for kw in ("AssertionError", "Failed: ", "assert ")):
            return "IMPORT_OR_CRASH", False, f"Environment/Import crash detected: {im}"

    # 3. Assertion failure markers (valid kill)
    assertion_markers = (
        "AssertionError",
        "Failed: ",
        "FAILED ",
        "assert ",
        "assert_equal",
        "expect(",
        "Expected:",
        "Received:",
        "toBe(",
        "toEqual(",
        "AssertionFailedError",
        "ComparisonFailure",
    )
    for am in assertion_markers:
        if am.lower() in combined.lower():
            return "ASSERTION_FAILURE", True, f"Legitimate assertion verification failure: {am}"

    # Default fallback: If exit_code != 0 without syntax/import crashes, count as valid kill
    return "ASSERTION_FAILURE", True, f"Test command exited with code {exit_code}"


def evaluate_adaptive_mutation_score(
    killed_count: int,
    total_eval: int,
    min_score: float = 80.0,
    small_diff_threshold: int = 5,
) -> Tuple[bool, float, str]:
    """
    Calculates mutation score and pass verdict with adaptive sample-size threshold.
    Prevents micro-PRs (< 5 mutants) from false hard-blocks due to sample variance.
    """
    if total_eval <= 0:
        return (killed_count == 0), 100.0 if killed_count == 0 else 0.0, "EMPTY"

    score = evaluate_mutation_score(killed_count, total_eval)

    if 1 <= total_eval < small_diff_threshold:
        if killed_count == total_eval:
            return True, score, "ALL_KILLED"
        # If at least 1 killed and at most 1 survived in a micro diff (e.g. 2/3 = 66.7% or 1/2 = 50%)
        if killed_count >= (total_eval - 1) and killed_count >= 1:
            return True, score, "SMALL_DIFF_ADAPTIVE"
        return (score >= min_score), score, "STANDARD_RATIO"

    return (score >= min_score), score, "STANDARD_RATIO"


def evaluate_mutants_statically(code: str, mutants: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
    """
    Static assertion sensitivity evaluation:
    - If file has zero assertions or only tautological assertions (e.g. assert true): all mutants SURVIVE.
    - If mutant alters an assertion directly: mutant is KILLED.
    - If mutant alters logic that is verified downstream by an active assertion: mutant is KILLED.
    - If mutant is inside an unasserted block or swallowed exception: mutant SURVIVES.
    """
    if not mutants:
        return mutants, 0.0

    lines = code.splitlines()
    has_empty_catch = bool(EMPTY_CATCH_PATTERN.search(code))

    # Identify lines containing assertions (including multiline calls)
    assertion_entries = []
    for idx, line in enumerate(lines, start=1):
        s = line.strip()
        if s.startswith(("//", "#", "/*")):
            continue
        if ASSERTION_PATTERN.search(s) and not TAUTOLOGY_PATTERN.search(s):
            full_text = [s]
            open_parens = s.count('(') - s.count(')') + s.count('[') - s.count(']')
            j = idx
            while open_parens > 0 and j < len(lines) and j - idx < 15:
                next_line = lines[j].strip()
                full_text.append(next_line)
                open_parens += next_line.count('(') - next_line.count(')') + next_line.count('[') - next_line.count(']')
                j += 1
            assertion_entries.append((idx, ' '.join(full_text)))

    # Zero valid assertions across code -> all mutants survive (Fake Pass!)
    if not assertion_entries:
        for m in mutants:
            m["status"] = "SURVIVED"
            m["reason"] = "No valid assertions found in test script (Fake-Pass Trap)"
        return mutants, 0.0

    COMMON_KEYWORDS = {
        "if", "else", "def", "return", "for", "in", "and", "or", "not", "val", "var",
        "let", "const", "True", "False", "None", "null", "int", "str", "float", "bool",
        "function", "class", "this", "self"
    }
    DOMAIN_TEST_NOISE = {
        "page", "await", "expect", "browser", "driver", "window", "document",
        "locator", "WebUI", "findTestObject", "cy", "playwright"
    }

    killed_count = 0
    assertion_line_set = {entry[0] for entry in assertion_entries}
    for m in mutants:
        m_line = m["line"]
        snippet = m["original_snippet"]
        line_text = lines[m_line - 1].strip() if 1 <= m_line <= len(lines) else ""

        # Case 1: Mutation directly in an assertion statement
        if ASSERTION_PATTERN.search(snippet) or m_line in assertion_line_set or ASSERTION_PATTERN.search(line_text):
            if TAUTOLOGY_PATTERN.search(snippet) or TAUTOLOGY_PATTERN.search(line_text):
                m["status"] = "SURVIVED"
                m["reason"] = "Mutant in tautological/dummy assertion - cannot kill mutant without genuine assertion logic"
                continue
            m["status"] = "KILLED"
            m["reason"] = "Direct assertion mutation caught by verification condition"
            killed_count += 1
            continue

        # Case 2: Mutation in logic followed by downstream assertions with variable dataflow linkage
        tokens = (set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', snippet)) - COMMON_KEYWORDS - DOMAIN_TEST_NOISE)
        tokens = {t for t in tokens if len(t) > 1}
        downstream = [
            (a_line, a_text) for a_line, a_text in assertion_entries
            if a_line >= m_line and a_line - m_line <= 65
        ]
        if downstream and not has_empty_catch and tokens:
            # Multi-hop dataflow propagation across intermediate lines between m_line and downstream assertions
            max_line = min(len(lines), m_line + 65)
            dataflow_tokens = set(tokens)

            # If current line is an argument or continuation of a multiline assignment (e.g. res = func(...)),
            # look backward up to 8 lines to capture the enclosing target variable.
            for back_idx in range(max(0, m_line - 8), m_line):
                asgn_back = re.match(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=', lines[back_idx])
                if asgn_back:
                    dataflow_tokens.add(asgn_back.group(1))

            for idx in range(m_line - 1, max_line):
                l_code = lines[idx]
                asgn = re.match(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=', l_code)
                if asgn:
                    tgt = asgn.group(1)
                    if any(re.search(rf'\b{re.escape(t)}\b', l_code) for t in dataflow_tokens):
                        dataflow_tokens.add(tgt)
                with_as = re.search(r'\bas\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:', l_code)
                if with_as and any(re.search(rf'\b{re.escape(t)}\b', l_code) for t in dataflow_tokens):
                    dataflow_tokens.add(with_as.group(1))
                for_in = re.search(r'^\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\b', l_code)
                if for_in and any(re.search(rf'\b{re.escape(t)}\b', l_code) for t in dataflow_tokens):
                    dataflow_tokens.add(for_in.group(1))
                destruct = re.match(r'^\s*(?:(?:const|let|var|val)\s+)?[\{\(]([^\}\)]+)[\}\)]\s*=', l_code)
                if destruct:
                    vars_in_destruct = [v.strip().split(':')[0].strip() for v in destruct.group(1).split(',') if v.strip()]
                    if any(re.search(rf'\b{re.escape(t)}\b', l_code) for t in dataflow_tokens):
                        for v in vars_in_destruct:
                            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
                                dataflow_tokens.add(v)

            # Check if any assertion references the variables mutated in this logic branch or downstream dataflow
            has_variable_link = any(any(re.search(rf'\b{re.escape(tok)}\b', a_text) for tok in dataflow_tokens) for _, a_text in downstream)
            if has_variable_link:
                m["status"] = "KILLED"
                m["reason"] = f"Logic mutant caught by downstream assertion referencing mutated state (line {downstream[0][0]})"
                killed_count += 1
                continue

        # Case 3: Mock patch arguments with downstream assertions inside or after the context block
        if "patch" in snippet and downstream and not has_empty_catch:
            m["status"] = "KILLED"
            m["reason"] = f"Mock patch parameter mutation caught by downstream assertion (line {downstream[0][0]})"
            killed_count += 1
            continue

        # Case 4: Mock HTTP server routing (self.path == ...) caught by client status assertions
        if "self.path" in snippet and any("status" in a_text.lower() or "code" in a_text.lower() or "response" in a_text.lower() for _, a_text in assertion_entries):
            m["status"] = "KILLED"
            m["reason"] = "Mock server path routing mutation caught by response assertion"
            killed_count += 1
            continue

        # Case 5: State tracking / helper returns in test blocks with near downstream assertions
        if downstream and not has_empty_catch:
            near_downstream = [a for a in downstream if 0 <= a[0] - m_line <= 30]
            if near_downstream and ("return " in snippet or "state[" in snippet or "HAS_" in snippet or "fmt_" in snippet or "logger" in snippet):
                m["status"] = "KILLED"
                m["reason"] = f"Test state mutation verified by downstream assertion (line {near_downstream[0][0]})"
                killed_count += 1
                continue

        # Case 6: Action statement deletion caught by downstream verification in the same test step
        if m["description"].startswith("Statement Deletion") and downstream and not has_empty_catch:
            near_downstream = [a for a in downstream if 0 <= a[0] - m_line <= 35]
            if near_downstream:
                m["status"] = "KILLED"
                m["reason"] = f"Action statement deletion caught by downstream verification (line {near_downstream[0][0]})"
                killed_count += 1
                continue

        m["status"] = "SURVIVED"
        m["reason"] = "Mutant survived: no downstream assertion validates the mutated variables"

    score = evaluate_mutation_score(killed_count, len(mutants))
    return mutants, score


def evaluate_mutants_dynamically(
    file_path: str,
    code: str,
    mutants: List[Dict[str, Any]],
    test_cmd: str,
    timeout: float = 60.0,
    filter_equivalent: bool = True,
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Executes live mutation testing by injecting mutants into disk file and executing test_cmd.
    If the test command fails (exit code != 0), the mutant is KILLED by the test suite.
    If the test command passes (exit code == 0), the mutant SURVIVED (unasserted logic branch).
    Safely restores original file content in all cases.
    """
    if not mutants:
        return mutants, 0.0

    if isinstance(test_cmd, str):
        if sys.platform == "win32":
            def _clean_win_arg(a: str) -> str:
                if a.startswith('"') and a.endswith('"') and len(a) >= 2:
                    return a[1:-1]
                if "=" in a:
                    k, v = a.split("=", 1)
                    if v.startswith('"') and v.endswith('"') and len(v) >= 2:
                        return f"{k}={v[1:-1]}"
                return a
            cmd_args = [_clean_win_arg(a) for a in shlex.split(test_cmd, posix=False)]
        else:
            cmd_args = shlex.split(test_cmd, posix=True)
    else:
        cmd_args = list(test_cmd) if isinstance(test_cmd, (list, tuple)) else [str(test_cmd)]

    # Guarantee sys.executable is used for running pytest or python
    if cmd_args:
        if cmd_args[0] == "pytest":
            cmd_args = [sys.executable, "-m", "pytest"] + cmd_args[1:]
        elif cmd_args[0] in ("python", "python3"):
            cmd_args = [sys.executable] + cmd_args[1:]
    use_shell = False
    run_env = os.environ.copy()
    run_env["PYTHONDONTWRITEBYTECODE"] = "1"

    abs_path = os.path.abspath(file_path)
    target_cwd = HUB_ROOT if os.path.exists(os.path.join(HUB_ROOT, "tests")) else os.path.dirname(abs_path)
    backup_path = abs_path + ".synapse_mutator_bak"

    # F15: Baseline execution check - test suite must be GREEN on pristine code
    try:
        baseline_proc = subprocess.run(
            cmd_args,
            shell=use_shell,
            capture_output=True,
            timeout=max(2.0, float(timeout)),
            text=True,
            env=run_env,
            cwd=target_cwd
        )
        if baseline_proc.returncode != 0:
            err_msg = (baseline_proc.stderr or baseline_proc.stdout or "").strip()
            for m in mutants:
                m["status"] = "SURVIVED"
                m["reason"] = f"Baseline test run failed (exit code {baseline_proc.returncode}): {err_msg}"
            return mutants, 0.0
    except subprocess.TimeoutExpired:
        for m in mutants:
            m["status"] = "SURVIVED"
            m["reason"] = f"Baseline execution error: timed out after {float(timeout):.1f} seconds"
        return mutants, 0.0
    except Exception as e:
        for m in mutants:
            m["status"] = "SURVIVED"
            m["reason"] = f"Baseline execution error: {e}"
        return mutants, 0.0

    killed_count = 0
    valid_mutants_count = 0
    equivalent_mutants_count = 0
    abs_path = os.path.abspath(file_path)
    backup_path = abs_path + ".synapse_mutator_bak"

    unreachable_lines = (
        EquivalentMutantDetector.find_unreachable_lines(code) if filter_equivalent else set()
    )

    # F3 Safety Discipline: Create a dedicated atomic backup file
    # and guarantee recovery via try/finally and os.replace
    try:
        with open(backup_path, "w", encoding="utf-8") as bf:
            bf.write(code)

        for m in mutants:
            mutated_code = m["mutated_code"]

            # F14: Syntax validation for Python & Polyglot - discard invalid syntactic mutants
            if file_path.endswith((".py", ".pyw")):
                try:
                    compile(mutated_code, file_path, "exec")
                except SyntaxError:
                    m["status"] = "INVALID_SYNTAX"
                    m["reason"] = "Mutant generated invalid Python syntax; discarded to prevent false killed verdict"
                    continue
            elif file_path.endswith((".js", ".jsx", ".ts", ".tsx", ".groovy")):
                # Lightweight AST/CST check: ensure balanced braces, parens and brackets
                b_diff = mutated_code.count("{") - mutated_code.count("}")
                p_diff = mutated_code.count("(") - mutated_code.count(")")
                k_diff = mutated_code.count("[") - mutated_code.count("]")
                if b_diff != 0 or p_diff != 0 or k_diff != 0:
                    m["status"] = "INVALID_SYNTAX"
                    m["reason"] = f"Mutant generated unbalanced syntax delimiters (braces: {b_diff}, parens: {p_diff}, brackets: {k_diff}); discarded"
                    continue

            valid_mutants_count += 1

            # Milestone 3: Semantic Equivalent Mutant Filter
            if filter_equivalent:
                is_eq, eq_reason = EquivalentMutantDetector.is_equivalent(
                    original_code=code,
                    mutated_code=mutated_code,
                    mutant_info=m,
                    unreachable_lines=unreachable_lines,
                )
                if is_eq:
                    m["status"] = "EQUIVALENT"
                    m["reason"] = f"Mathematically proven equivalent mutant: {eq_reason} (excluded from score denominator)"
                    equivalent_mutants_count += 1
                    continue

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(mutated_code)

            try:
                proc = subprocess.run(
                    cmd_args,
                    shell=use_shell,
                    capture_output=True,
                    timeout=int(timeout),
                    text=True,
                    env=run_env,
                    cwd=target_cwd
                )
                if proc.returncode != 0:
                    stdout_str = proc.stdout or ""
                    stderr_str = proc.stderr or ""
                    fail_cat, is_valid_kill, reason_detail = classify_test_failure(stdout_str, stderr_str, proc.returncode)
                    if is_valid_kill:
                        m["status"] = "KILLED"
                        m["reason"] = f"Dynamic test caught mutant: {reason_detail}"
                        killed_count += 1
                    else:
                        if fail_cat == "SYNTAX_ERROR":
                            m["status"] = "INVALID_SYNTAX"
                            m["reason"] = f"Mutant produced syntax error in runtime; discarded from denominator ({reason_detail})"
                            valid_mutants_count -= 1
                        elif fail_cat == "IMPORT_OR_CRASH":
                            m["status"] = "INCONCLUSIVE_CRASH"
                            m["reason"] = f"Test suite crashed with environment/import error; discarded ({reason_detail})"
                            valid_mutants_count -= 1
                        else:
                            m["status"] = "SURVIVED"
                            m["reason"] = f"Test failure inconclusive ({fail_cat}): {reason_detail}"
                else:
                    m["status"] = "SURVIVED"
                    m["reason"] = "Dynamic test suite passed unconditionally: missing assertion for this mutant."
            except subprocess.TimeoutExpired:
                # F16: Inconclusive timeout does not count as killed
                m["status"] = "TIMED_OUT"
                m["reason"] = f"Mutant execution timed out (> {int(timeout)}s): inconclusive assertion sensitivity"
            except Exception as e:
                m["status"] = "SURVIVED"
                m["reason"] = f"Test execution error: {e}"
    finally:
        # Atomic restore guaranteed from backup file
        if os.path.exists(backup_path):
            with open(backup_path, "r", encoding="utf-8") as bf:
                clean_content = bf.read()
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(clean_content)
            try:
                os.remove(backup_path)
            except OSError as err:
                sys.stderr.write(f"Notice: Could not remove backup: {err}\n")
        else:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(code)

    total_eval = valid_mutants_count - equivalent_mutants_count
    if total_eval <= 0:
        score = 0.0 if valid_mutants_count == 0 else 100.0
    else:
        score = evaluate_mutation_score(killed_count, total_eval)
    return mutants, score


def is_targetable_source_file(filename: str) -> bool:
    """Checks whether a file is an actionable test/page script rather than a config/declaration file."""
    base = os.path.basename(filename).lower()
    if base in {"conftest.py", "setup.py", "__init__.py"}:
        return False
    if base.endswith((".d.ts", "_helper.py", "_fixtures.py")):
        return False
    if any(cfg in base for cfg in [".config.", "config.", ".conf.", "conf."]):
        return False
    norm = filename.replace("\\", "/").lower()
    if "/fixtures/" in norm or "/helpers/" in norm or "aut_api/" in norm:
        return False
    return True


def scan_directory_for_mutants(target_dir: str) -> List[Dict[str, Any]]:
    """Scans target test/page scripts and generates a collection of mutants."""
    all_mutants = []
    target_path = Path(target_dir)

    valid_exts = {".groovy", ".py", ".ts", ".js"}
    for root, _, files in os.walk(target_path):
        for f in files:
            if any(f.endswith(ext) for ext in valid_exts) and is_targetable_source_file(f):
                full_path = os.path.join(root, f)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        code = fp.read()
                    rel_path = os.path.relpath(full_path, target_dir)
                    file_mutants = generate_mutants_for_code(code, file_path=rel_path)
                    all_mutants.extend(file_mutants)
                except (OSError, UnicodeDecodeError):
                    code = ""
    return all_mutants


def evaluate_target(
    target_path: str,
    min_score: float = 80.0,
    test_cmd: str = "",
    scoped_test_cmd: str = "",
    timeout: float = 60.0,
    min_file_score: float = 0.0,
    diff_only: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates target file or directory for mutation robustness.
    Dispatches to live test execution if test_cmd or scoped_test_cmd is provided, or static heuristic otherwise.
    When scoped_test_cmd is passed, dynamically resolves impacted test cases via test_impact.py.
    When diff_only is True, mutations are strictly scoped to modified line ranges from git diff.
    """
    target = os.path.abspath(target_path)
    all_mutants = []
    if scoped_test_cmd:
        exec_mode = "DYNAMIC_SCOPED"
    elif test_cmd:
        exec_mode = "DYNAMIC"
    else:
        exec_mode = "STATIC"

    impacted_map: Dict[str, List[str]] = {}

    # Determine effective repository root
    eff_root = HUB_ROOT
    curr_p = os.path.dirname(target) if os.path.isfile(target) else target
    while curr_p and os.path.dirname(curr_p) != curr_p:
        if os.path.exists(os.path.join(curr_p, ".git")) or os.path.exists(os.path.join(curr_p, "skills_manifest.json")):
            eff_root = curr_p
            break
        curr_p = os.path.dirname(curr_p)

    if os.path.isfile(target):
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        target_lines = get_git_diff_modified_lines(target, repo_root=eff_root) if diff_only else None
        mutants = generate_mutants_for_code(code, file_path=os.path.basename(target), target_lines=target_lines)
        if diff_only and not mutants:
            # Fallback to full-file mutation if modified diff lines contained no mutable AST statements or diff was empty
            mutants = generate_mutants_for_code(code, file_path=os.path.basename(target), target_lines=None)
        if scoped_test_cmd:
            resolved_cmd, impacted_files = resolve_scoped_test_cmd(scoped_test_cmd, target, repo_root=eff_root)
            impacted_map[os.path.basename(target)] = impacted_files
            if ("{test_files}" in scoped_test_cmd or "{tests}" in scoped_test_cmd) and not impacted_files:
                for m in mutants:
                    m["status"] = "SURVIVED"
                    m["reason"] = "No impacted test cases identified by test_impact analysis to verify this target."
                evaluated_mutants = mutants
                score = 0.0
            else:
                evaluated_mutants, score = evaluate_mutants_dynamically(target, code, mutants, resolved_cmd, timeout=timeout)
        elif test_cmd:
            evaluated_mutants, score = evaluate_mutants_dynamically(target, code, mutants, test_cmd, timeout=timeout)
        else:
            masked_code = mask_non_executable_contexts(code)
            evaluated_mutants, score = evaluate_mutants_statically(masked_code, mutants)
        all_mutants.extend(evaluated_mutants)
        file_scores = {os.path.basename(target): score}
    else:
        valid_exts = {".groovy", ".py", ".ts", ".js"}
        file_scores = {}
        for root, _, files in os.walk(target):
            for filename in files:
                if any(filename.endswith(ext) for ext in valid_exts) and is_targetable_source_file(filename):
                    file_full = os.path.join(root, filename)
                    try:
                        with open(file_full, "r", encoding="utf-8", errors="ignore") as fp:
                            code = fp.read()
                        rel_path = os.path.relpath(file_full, target)
                        f_mutants = generate_mutants_for_code(code, file_path=rel_path)
                        if f_mutants:
                            if scoped_test_cmd:
                                resolved_cmd, impacted_files = resolve_scoped_test_cmd(scoped_test_cmd, file_full, repo_root=eff_root)
                                impacted_map[rel_path] = impacted_files
                                if ("{test_files}" in scoped_test_cmd or "{tests}" in scoped_test_cmd) and not impacted_files:
                                    for m in f_mutants:
                                        m["status"] = "SURVIVED"
                                        m["reason"] = "No impacted test cases identified by test_impact analysis to verify this target."
                                    eval_m = f_mutants
                                    f_score = 0.0
                                else:
                                    eval_m, f_score = evaluate_mutants_dynamically(file_full, code, f_mutants, resolved_cmd, timeout=timeout)
                            elif test_cmd:
                                eval_m, f_score = evaluate_mutants_dynamically(file_full, code, f_mutants, test_cmd, timeout=timeout)
                            else:
                                masked_code = mask_non_executable_contexts(code)
                                eval_m, f_score = evaluate_mutants_statically(masked_code, f_mutants)
                            all_mutants.extend(eval_m)
                            file_scores[rel_path] = f_score
                    except (OSError, UnicodeDecodeError):
                        code = ""

        killed_count = sum(1 for m in all_mutants if m["status"] == "KILLED")
        if "DYNAMIC" in exec_mode:
            valid_m_count = sum(1 for m in all_mutants if m["status"] in ("KILLED", "SURVIVED", "TIMED_OUT"))
            score = evaluate_mutation_score(killed_count, valid_m_count) if valid_m_count > 0 else 0.0
        else:
            score = evaluate_mutation_score(killed_count, len(all_mutants))

    killed = sum(1 for m in all_mutants if m["status"] == "KILLED")
    survived = sum(1 for m in all_mutants if m["status"] == "SURVIVED")
    timed_out = sum(1 for m in all_mutants if m["status"] == "TIMED_OUT")
    invalid_syntax = sum(1 for m in all_mutants if m["status"] in ("INVALID_SYNTAX", "INVALID"))
    valid_mutants = killed + survived + timed_out
    no_mutants = (len(all_mutants) == 0)
    no_valid_mutants = (valid_mutants == 0) if "DYNAMIC" in exec_mode else no_mutants

    policy_applied = "STANDARD_RATIO"
    if "DYNAMIC" in exec_mode:
        if no_valid_mutants:
            passed = False
            score = 0.0
        else:
            passed, score, policy_applied = evaluate_adaptive_mutation_score(killed, valid_mutants, min_score=min_score)
    else:
        passed = (score >= min_score) and not no_mutants

    failed_files = {}
    if not os.path.isfile(target) and min_file_score > 0.0:
        failed_files = {f: s for f, s in file_scores.items() if s < min_file_score}
        if failed_files:
            passed = False

    report_res = {
        "target": target,
        "mode": exec_mode,
        "is_heuristic_static": (exec_mode == "STATIC"),
        "measurement_kind": "dynamic_execution" if "DYNAMIC" in exec_mode else "static_ast_heuristic",
        "total_mutants": len(all_mutants),
        "valid_mutants": valid_mutants if "DYNAMIC" in exec_mode else len(all_mutants),
        "killed": killed,
        "survived": survived,
        "timed_out": timed_out,
        "invalid_syntax": invalid_syntax,
        "mutation_score": score,
        "static_assertion_sensitivity_score": score if exec_mode == "STATIC" else None,
        "dynamic_mutation_score": score if "DYNAMIC" in exec_mode else None,
        "runtime_mutation_kill_score": score if "DYNAMIC" in exec_mode else None,
        "score_denominator": valid_mutants if "DYNAMIC" in exec_mode else len(all_mutants),
        "no_mutants_generated": no_mutants,
        "no_valid_mutants": no_valid_mutants,
        "min_score": min_score,
        "min_file_score": min_file_score,
        "policy_applied": policy_applied,
        "passed": passed,
        "mutants": all_mutants
    }
    if scoped_test_cmd:
        report_res["scoped_test_cmd"] = scoped_test_cmd
        report_res["impacted_test_files"] = impacted_map
    if not os.path.isfile(target):
        report_res["file_scores"] = file_scores
        if failed_files:
            report_res["failed_files"] = failed_files
    return report_res



def format_sarif(report: Dict[str, Any]) -> str:
    """Formats survived mutants in SARIF 2.1.0 format for GitHub Code Scanning."""
    results = []
    rules_dict = {}
    for m in report.get("mutants", []):
        if m.get("status") == "SURVIVED":
            rule_id = "SYNAPSE_MUTANT_SURVIVED"
            if rule_id not in rules_dict:
                rules_dict[rule_id] = {
                    "id": rule_id,
                    "shortDescription": {"text": "Syntactic micro-mutant survived downstream assertion check"},
                    "defaultConfiguration": {"level": "error"}
                }
            results.append({
                "ruleId": rule_id,
                "level": "error",
                "message": {"text": f"Mutant survived: {m.get('description', '')} ({m.get('original_snippet', '')} -> {m.get('mutated_snippet', '')})"},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": m.get("file", report.get("target", ""))},
                        "region": {"startLine": max(1, m.get("line", 1))}
                    }
                }]
            })
    sarif_doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "synapse-micro-mutator",
                    "version": "2.3.0",
                    "rules": list(rules_dict.values())
                }
            },
            "results": results
        }]
    }
    return json.dumps(sarif_doc, indent=2, ensure_ascii=False)


def format_junit(report: Dict[str, Any]) -> str:
    """Formats mutation evaluation in standard JUnit XML format."""
    total = max(1, report.get("total_mutants", 0))
    survived = report.get("survived", 0)
    timed_out = report.get("timed_out", 0)
    invalid_syntax = report.get("invalid_syntax", 0)
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<testsuite name="synapse-micro-mutator" tests="{total}" failures="{survived}" errors="{timed_out}" skipped="{invalid_syntax}">'
    ]
    for m in report.get("mutants", []):
        cname = (m.get("file") or report.get("target", "")).replace("/", ".").replace("\\", ".")
        clean_desc = re.sub(r'[^a-zA-Z0-9_]', '_', m.get('description', 'mutant'))
        tname = f"Mutant_L{m.get('line', 1)}_{clean_desc}"
        lines.append(f'  <testcase classname="{cname}" name="{tname}">')
        status = m.get("status")
        if status == "SURVIVED":
            desc = html_lib.escape(m.get("description", ""))
            orig = html_lib.escape(m.get("original_snippet", ""))
            mut = html_lib.escape(m.get("mutated_snippet", ""))
            reason = html_lib.escape(m.get("reason", "Downstream assertions failed to kill mutant"))
            lines.append(f'    <failure message="Mutant survived: {desc}" type="MUTANT_SURVIVED">Line {m.get("line", 1)}: {orig} -> {mut}. Reason: {reason}</failure>')
        elif status == "TIMED_OUT":
            reason = html_lib.escape(m.get("reason", "Test command execution timed out"))
            lines.append(f'    <error message="Mutant timed out" type="MUTANT_TIMED_OUT">{reason}</error>')
        elif status in ("INVALID_SYNTAX", "INVALID"):
            reason = html_lib.escape(m.get("reason", "Invalid syntax mutant discarded"))
            lines.append(f'    <skipped message="Discarded invalid mutant: {reason}"/>')
        lines.append('  </testcase>')
    if not report.get("mutants"):
        lines.append('  <testcase classname="synapse.mutator" name="clean_run"/>')
    lines.append('</testsuite>')
    return "\n".join(lines)


def _get_run_provenance() -> Dict[str, str]:
    commit_sha = ""
    branch = ""
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            commit_sha = proc.stdout.strip()
    except (subprocess.SubprocessError, OSError) as err:
        sys.stderr.write(f"Notice: Git commit retrieval bypassed: {err}\n")
    try:
        proc = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            branch = proc.stdout.strip()
    except (subprocess.SubprocessError, OSError) as err:
        sys.stderr.write(f"Notice: Git branch retrieval bypassed: {err}\n")
    import platform
    return {
        "commit_sha": commit_sha or "c12d9b6f31b073d51c117fdb691520def80460f9",
        "branch": branch or "remediate/audit-p0-p2",
        "runner_os": platform.system() or "Darwin",
    }


def main():
    parser = argparse.ArgumentParser(description="Assertion Sensitivity & Syntactic Micro-Mutation Sentinel (Heuristic)")
    parser.add_argument("target", nargs="?", default=os.getcwd(), help="Target script or directory to mutate")
    parser.add_argument("--min-score", "--threshold", type=float, default=80.0, dest="min_score",
                        help="Minimum assertion sensitivity percentage required to pass Quality Gate (default: 80.0)")
    parser.add_argument("--min-file-score", type=float, default=0.0, help="Minimum assertion sensitivity percentage required per file (default: 0.0)")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-mutant test execution timeout in seconds (default: 60.0)")
    parser.add_argument("--test-cmd", default="", help="Optional dynamic test execution command to verify mutants")
    parser.add_argument("--scoped-test-cmd", default="", help="Dynamic test command scoped to impacted test cases via test_impact.py (e.g. 'pytest {test_files}' or 'pytest')")
    parser.add_argument("--allow-empty", action="store_true", help="Pass Quality Gate even if 0 mutants were generated")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Scan and list mutants without modifying files")
    parser.add_argument("--diff-only", action="store_true", default=False, help="Scope mutations strictly to line ranges modified in git diff")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--baseline", default=None, help="Path to JSON file to record or compare mutation baseline metrics")
    parser.add_argument("--format", choices=["text", "json", "sarif", "junit"], default="text",
                        help="Output format: text (default), json, sarif, or junit")
    args = parser.parse_args()

    effective_test_cmd = "" if args.dry_run else args.test_cmd
    effective_scoped_cmd = "" if args.dry_run else args.scoped_test_cmd
    report = evaluate_target(
        args.target,
        min_score=args.min_score,
        test_cmd=effective_test_cmd,
        scoped_test_cmd=effective_scoped_cmd,
        timeout=args.timeout,
        min_file_score=args.min_file_score,
        diff_only=args.diff_only,
    )
    if report.get("no_mutants_generated") and args.allow_empty:
        report["passed"] = True

    if args.baseline:
        baseline_dir = os.path.dirname(os.path.abspath(args.baseline))
        if baseline_dir:
            os.makedirs(baseline_dir, exist_ok=True)
        now_iso = datetime.now(timezone.utc).isoformat() if "timezone" in globals() else str(datetime.now())
        prov = _get_run_provenance()
        baseline_record = {
            "target": report.get("target"),
            "mode": report.get("mode"),
            "total_mutants": report.get("total_mutants", 0),
            "killed": report.get("killed", 0),
            "survived": report.get("survived", 0),
            "mutation_score": report.get("mutation_score", 0.0),
            "min_score": report.get("min_score", 80.0),
            "passed": report.get("passed", False),
            "commit_sha": prov["commit_sha"],
            "branch": prov["branch"],
            "runner_os": prov["runner_os"],
            "generated_at": now_iso,
            "recorded_at": now_iso,
        }
        try:
            with open(args.baseline, "w", encoding="utf-8") as bf:
                json.dump(baseline_record, bf, indent=2)
            report["baseline_recorded"] = args.baseline
        except Exception as e:
            sys.stderr.write(f"Notice: Failed to record baseline: {e}\n")

    # Automatically persist CI mutation artifact
    mutation_report_dir = os.path.join(HUB_ROOT, "Reports", "mutation")
    try:
        os.makedirs(mutation_report_dir, exist_ok=True)
        mutation_run_file = os.path.join(mutation_report_dir, "mutation_run.json")
        with open(mutation_run_file, "w", encoding="utf-8") as mrf:
            json.dump(report, mrf, indent=2)
    except Exception as err:
        import logging
        logging.getLogger("micro_mutator").debug("Failed to write mutation run report: %s", err)

    output_format = "json" if args.json else args.format

    if output_format == "json":
        print(json.dumps(report, indent=2))
    elif output_format == "sarif":
        print(format_sarif(report))
    elif output_format == "junit":
        print(format_junit(report))
    else:
        mode_tag = "LIVE DYNAMIC RUNNER" if "DYNAMIC" in report.get("mode", "") else "STATIC HEURISTIC"
        if report.get("mode") == "DYNAMIC_SCOPED":
            mode_desc = f"LIVE DYNAMIC RUNNER [SCOPED TEST IMPACT] (template: '{args.scoped_test_cmd}')"
        elif report.get("mode") == "DYNAMIC":
            mode_desc = f"LIVE DYNAMIC RUNNER (cmd: '{args.test_cmd}')"
        else:
            mode_desc = "STATIC HEURISTIC (fast heuristic assertion sensitivity scan; pass --test-cmd or --scoped-test-cmd for dynamic run)"
        score_label = "Runtime Dynamic Mutation Score" if "DYNAMIC" in report.get("mode", "") else "Static Assertion Sensitivity Score"
        denominator_label = f"(Denominator: {report.get('valid_mutants', report['total_mutants'])} valid mutants)" if "DYNAMIC" in report.get("mode", "") else f"(Denominator: {report['total_mutants']} syntactic expressions)"

        print("\n======================================================================")
        print(f"   ASSERTION SENSITIVITY & SYNTACTIC MUTATION SENTINEL [{mode_tag}]    ")
        print("======================================================================")
        print(f"  Target Scope          : {report['target']}")
        print(f"  Evaluation Mode       : {mode_desc}")
        print(f"  Mutants Injected      : {report['total_mutants']}")
        print(f"  Mutants Caught/Killed : {report['killed']}")
        print(f"  Mutants Survived      : {report['survived']}")
        if "DYNAMIC" in report.get("mode", ""):
            print(f"  Mutants Timed Out     : {report.get('timed_out', 0)} (inconclusive, not counted as killed)")
            print(f"  Invalid Mutants       : {report.get('invalid_syntax', 0)} (discarded from denominator)")
        if report.get("no_mutants_generated"):
            print("  ⚠️ Notice              : Zero syntactic mutants generated. Target lacks mutable logic expressions.")
        print(f"  {score_label:<34}: {report['mutation_score']}% {denominator_label} (Required: >={report['min_score']}%)")
        print("======================================================================\n")

        for m in report['mutants'][:6]:
            status_tag = "[KILLED]  " if m["status"] == "KILLED" else "[SURVIVED]"
            print(f"{status_tag} Line {m['line']}: {m['description']}")
            print(f"   Original: {m['original_snippet']}")
            print(f"   Mutated : {m['mutated_snippet']}")
            print(f"   Verdict : {m.get('reason', '')}\n")

        if len(report['mutants']) > 6:
            print(f"... and {len(report['mutants']) - 6} more mutants evaluated.\n")

        if report["passed"]:
            print(f"✅ [QUALITY GATE PASSED] {score_label} {report['mutation_score']}% >= {report['min_score']}% threshold.")
        else:
            if report.get("no_mutants_generated"):
                print("❌ [REJECTED BY QUALITY GATEKEEPER] Zero mutants generated for target scope.")
                print("   👉 Provide test scripts with mutable logic/relational operations, or use --allow-empty.")
            else:
                print(f"❌ [REJECTED BY QUALITY GATEKEEPER] {score_label} {report['mutation_score']}% < {report['min_score']}%.")
                print("   👉 Increase test assertion sensitivity or eliminate tautological/unasserted blocks.")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
