"""Self-modification engine for evolving forge source code.

Applies mutation operators to the forge's own Python source tree —
inserting, deleting, or rewriting AST nodes — so the forge modifies
its own implementation at runtime.
"""

from __future__ import annotations

import ast
import inspect
import logging
import random
import textwrap
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SelfModifier:
    """Applies mutation operators to forge source code components.

    Each operator rewrites the AST of a target component (or the forge
    itself) to introduce a novel variation.  Operators are pluggable
    and can themselves be evolved.
    """

    def __init__(self, forge_root: Path | None = None) -> None:
        self.forge_root = forge_root or Path(__file__).resolve().parent.parent
        self._loaded_sources: dict[str, str] = {}

    async def snapshot_current(self) -> str:
        """Capture the forge's own source tree as a single text block."""
        parts: list[str] = []
        for path in sorted(self.forge_root.rglob("*.py")):
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(self.forge_root)
            parts.append(f"# --- {relative} ---")
            parts.append(path.read_text())
        return "\n".join(parts)

    async def mutate(
        self,
        source: str,
        operator: str | None = None,
        component_type: str = "component",
    ) -> dict[str, Any]:
        """Apply a named mutation operator to the given source."""
        operators = {
            "insert_code": self._insert_code_block,
            "rewrite_function": self._rewrite_function_body,
            "add_parameter": self._add_parameter,
            "swap_condition": self._swap_condition,
            "duplicate_component": self._duplicate_component,
        }

        operator = operator or random.choice(list(operators.keys()))
        mutator = operators.get(operator, self._insert_code_block)
        new_source = mutator(source)

        return {
            "source": new_source,
            "component_type": f"{component_type}_mutated",
            "operator": operator,
        }

    def _insert_code_block(self, source: str) -> str:
        """Insert a random logging or branching statement into the source."""
        tree = ast.parse(source)
        if not tree.body:
            return source

        target = random.choice(tree.body)
        if not hasattr(target, "body") or not target.body:
            return source

        snippet = (
            "logger.debug('Self-mutation trace: {}')".format(
                uuid.uuid4().hex[:8]
            )
        )
        try:
            insert = ast.parse(textwrap.dedent(snippet)).body
        except SyntaxError:
            return source

        pos = random.randint(0, len(target.body))
        target.body.insert(pos, insert[0])
        return ast.unparse(tree)

    def _rewrite_function_body(self, source: str) -> str:
        """Replace a random function body with a pass."""
        tree = ast.parse(source)
        funcs = [
            n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not funcs:
            return source

        func = random.choice(funcs)
        func.body = [ast.Pass()]
        return ast.unparse(tree)

    def _add_parameter(self, source: str) -> str:
        """Add an optional parameter to a random function."""
        tree = ast.parse(source)
        funcs = [
            n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not funcs:
            return source

        func = random.choice(funcs)
        param_name = f"_extra_{uuid.uuid4().hex[:4]}"
        default = ast.Constant(value=None)
        func.args.args.append(ast.arg(arg=param_name, annotation=None))
        func.args.defaults.append(default)
        return ast.unparse(tree)

    def _swap_condition(self, source: str) -> str:
        """Negate a random if-condition."""
        tree = ast.parse(source)
        ifs = [n for n in ast.walk(tree) if isinstance(n, ast.If)]
        if not ifs:
            return source

        if_node = random.choice(ifs)
        if_node.test = ast.UnaryOp(op=ast.Not(), operand=if_node.test)
        return ast.unparse(tree)

    def _duplicate_component(self, source: str) -> str:
        """Duplicate a random top-level class or function."""
        tree = ast.parse(source)
        candidates = [
            n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not candidates:
            return source

        chosen = random.choice(candidates)
        clone = ast.copy_location(
            ast.parse(
                textwrap.dedent(inspect.getsource(type(chosen))).format(
                    name=chosen.name + "_copy"
                )
                or "pass"
            ).body[0],
            chosen,
        )
        tree.body.insert(tree.body.index(chosen) + 1, clone)
        return ast.unparse(tree)
