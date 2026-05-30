"""Self-modification engine for evolving forge source code.

Applies mutation operators to the forge's own Python source tree —
inserting, deleting, or rewriting AST nodes — so the forge modifies
its own implementation at runtime.  Operators can themselves be
evolved (meta-mutation), enabling open-ended growth of the forge's
genetic vocabulary.
"""

from __future__ import annotations

import ast
import copy
import logging
import random
import textwrap
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ALL_OPERATORS: tuple[str, ...] = (
    "add_type_hints", "add_docstring", "extract_constant",
    "add_error_handling", "inline_return",
    "insert_code", "rewrite_function", "add_parameter",
    "swap_condition", "duplicate_component",
    "evolve_operator", "recombine_modules",
    "transplant_function",
)

CONSTRUCTIVE_OPERATORS: tuple[str, ...] = (
    "add_type_hints", "add_docstring", "extract_constant",
    "add_error_handling", "inline_return",
)

STRUCTURAL_OPERATORS: tuple[str, ...] = (
    "insert_code", "rewrite_function", "add_parameter",
    "swap_condition", "duplicate_component",
)

OPERATOR_DESCRIPTIONS: dict[str, str] = {
    "add_type_hints": "Add -> None return type to functions lacking annotations",
    "add_docstring": "Add minimal docstring to functions and classes lacking one",
    "extract_constant": "Replace repeated string literal with module-level constant",
    "add_error_handling": "Wrap bare raise statements in try/except",
    "inline_return": "Simplify single-expression return functions",
    "insert_code": "Insert a random logging statement into a function body",
    "rewrite_function": "Replace a function body with pass",
    "add_parameter": "Add an optional None parameter to a function",
    "swap_condition": "Negate a random if-condition",
    "duplicate_component": "Deep-copy a random top-level class or function",
    "cross_file_recombine": "Transplant a function from one file into another",
}


class SelfModifier:
    """Applies mutation operators to forge source code components.

    Each operator rewrites the AST of a target component (or the forge
    itself) to introduce a novel variation.  Operators are pluggable
    and can themselves be evolved via the ``_evolve_operator`` meta-
    mutation.
    """

    MUTATABLE_FILES: list[dict[str, str]] = [
        {"path": "benchmarks/benchmark_runner.py", "risk": "low", "module": "benchmarks.benchmark_runner"},
        {"path": "benchmarks/benchmark_suite.py", "risk": "low", "module": "benchmarks.benchmark_suite"},
        {"path": "forge/self_writer.py", "risk": "medium", "module": "forge.self_writer"},
        {"path": "forge/self_modifier.py", "risk": "high", "module": "forge.self_modifier"},
        {"path": "forge/orchestrator.py", "risk": "high", "module": "forge.orchestrator"},
        {"path": "meta_evolution/meta_evolver.py", "risk": "medium", "module": "meta_evolution.meta_evolver"},
        {"path": "evaluators/evaluator.py", "risk": "high", "module": "evaluators.evaluator"},
        {"path": "archive/archivist.py", "risk": "low", "module": "archive.archivist"},
    ]

    def __init__(self, forge_root: Path | None = None) -> None:
        self.forge_root = forge_root or Path(__file__).resolve().parent.parent
        self._loaded_sources: dict[str, str] = {}

    def select_target(self, risk_max: str = "low", generation: int = 0) -> str:
        """Select a mutable file target filtered by risk level.

        Risk escalates with generation count: low-risk at gen < 5,
        medium at gen < 20, high thereafter.  This prevents the forge
        from dangerous self-modifications before it has proven
        evolutionary fitness.

        Args:
            risk_max: Maximum risk level — 'low', 'medium', or 'high'.
                Overrides generation-based escalation when explicitly set.
            generation: Current evolution generation. Higher values
                unlock riskier targets.

        Returns:
            Relative path string like 'benchmarks/benchmark_runner.py'.
        """
        risk_order = {"low": 0, "medium": 1, "high": 2}

        if risk_max == "low":
            if generation >= 20:
                risk_max = "high"
            elif generation >= 5:
                risk_max = "medium"

        max_level = risk_order.get(risk_max, 0)
        candidates = [
            f for f in self.MUTATABLE_FILES
            if risk_order.get(f["risk"], 99) <= max_level
        ]
        if not candidates:
            candidates = [self.MUTATABLE_FILES[0]]
        return random.choice(candidates)["path"]

    async def read_file(self, relative_path: str) -> str:
        """Read a single forge source file.

        Args:
            relative_path: Relative path like 'benchmarks/benchmark_runner.py'.

        Returns:
            The file contents as a string.
        """
        full_path = self.forge_root / relative_path
        return full_path.read_text()

    async def load_target(self, component_type: str) -> str | None:
        """Load the source of a single forge file by component type.

        Args:
            component_type: Component type like 'forge_orchestrator' or
                a dotted module path like 'forge.orchestrator'.

        Returns:
            Source code as string, or None if the file cannot be resolved.
        """
        from forge.self_writer import SelfWriter
        writer = SelfWriter(forge_root=self.forge_root)
        path = writer.resolve_path(component_type)
        if path is None or not path.exists():
            logger.warning("Cannot load target '%s': path not found", component_type)
            return None
        source = path.read_text()
        self._loaded_sources[component_type] = source
        logger.debug("Loaded target '%s' from %s (%d bytes)", component_type, path, len(source))
        return source

    async def snapshot_current(self) -> dict[str, str]:
        """Capture all forge source files, keyed by component type.

        Returns:
            Dict mapping component_type → source_code for every .py file.
        """
        from forge.self_writer import SelfWriter
        writer = SelfWriter(forge_root=self.forge_root)
        snap: dict[str, str] = {}
        for target in writer.get_available_targets():
            ctype = target["component_type"]
            path = writer._forge_root / target["path"]
            snap[ctype] = path.read_text()
        return snap

    async def mutate(
        self,
        source: str,
        operator: str | None = None,
        component_type: str = "component",
    ) -> dict[str, Any]:
        """Apply a named mutation operator to a single-file source string.

        Args:
            source: Source code of a single Python file.
            operator: Name of the operator to apply. If None, picks randomly.
            component_type: Identifier for logging/tracking.

        Returns:
            Dict: source (mutated), component_type, operator, operator_desc.
        """
        operators: dict[str, Any] = {
            "add_type_hints": self._add_type_hints,
            "add_docstring": self._add_docstring,
            "extract_constant": self._extract_constant,
            "add_error_handling": self._add_error_handling,
            "inline_return": self._inline_return,
            "insert_code": self._insert_code_block,
            "rewrite_function": self._rewrite_function_body,
            "add_parameter": self._add_parameter,
            "swap_condition": self._swap_condition,
            "duplicate_component": self._duplicate_component,
            "evolve_operator": self._evolve_operator,
            "recombine_modules": self._recombine_modules,
            "transplant_function": self._transplant_function,
        }

        operator = operator or random.choice(ALL_OPERATORS)
        mutator = operators.get(operator)
        if mutator is None:
            logger.warning("Unknown operator '%s', falling back to insert_code", operator)
            mutator = self._insert_code_block
            operator = "insert_code"

        new_source = mutator(source)
        desc = OPERATOR_DESCRIPTIONS.get(operator, "")

        return {
            "source": new_source,
            "component_type": f"{component_type}_mutated",
            "operator": operator,
            "operator_desc": desc,
        }

    # ── Constructive Operators ─────────────────────────────────────

    def _add_type_hints(self, source: str) -> str:
        """Add -> None return type to functions that lack any annotation."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        modified = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.returns is None and node.name != "__init__":
                    node.returns = ast.Constant(value=None)
                    modified = True

        if not modified:
            return source
        return ast.unparse(tree)

    def _add_docstring(self, source: str) -> str:
        """Add a minimal docstring to functions and classes that lack one."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        modified = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    doc = ast.Expr(value=ast.Constant(value=""))
                    node.body.insert(0, doc)
                    modified = True

        if not modified:
            return source
        return ast.unparse(tree)

    def _extract_constant(self, source: str) -> str:
        """Replace a repeated string literal with a module-level constant.

        Finds a string literal that appears 3+ times and lifts it to a
        UPPER_CASE constant assignment at the top of the module.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        string_counts: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) >= 3:
                string_counts[node.value] = string_counts.get(node.value, 0) + 1

        candidates = {s: c for s, c in string_counts.items() if c >= 3}
        if not candidates:
            return source

        target_str = max(candidates, key=candidates.get)
        const_name = target_str.upper().replace(" ", "_")[:20]
        if not const_name or const_name[0].isdigit():
            const_name = "S_" + const_name

        constant_assign = ast.Assign(
            targets=[ast.Name(id=const_name, ctx=ast.Store())],
            value=ast.Constant(value=target_str),
        )

        has_const = any(
            isinstance(stmt, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == const_name
                for t in stmt.targets
            )
            for stmt in tree.body
        )
        if has_const:
            return source

        # Insert at top (after imports/docstring)
        insert_pos = 0
        for i, stmt in enumerate(tree.body):
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                insert_pos = i + 1
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Constant, ast.Str)):
                insert_pos = i + 1
            else:
                break

        tree.body.insert(insert_pos, constant_assign)

        class StringReplacer(ast.NodeTransformer):
            def visit_Constant(self, node: ast.Constant) -> ast.AST:
                if isinstance(node.value, str) and node.value == target_str:
                    return ast.Name(id=const_name, ctx=ast.Load())
                return node

        tree = StringReplacer().visit(tree)
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)

    def _add_error_handling(self, source: str) -> str:
        """Wrap top-level bare raise statements in try/except blocks.

        Also wraps direct raise statements inside function bodies.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        modified = False

        class RaiseWrapper(ast.NodeTransformer):
            def visit_Raise(self, node: ast.Raise) -> ast.AST:
                nonlocal modified
                if node.exc is None:
                    modified = True
                    return ast.Try(
                        body=[ast.Raise(exc=ast.Call(
                            func=ast.Name(id="Exception", ctx=ast.Load()),
                            args=[ast.Constant(value="wrapped")],
                            keywords=[],
                        ), cause=None)],
                        handlers=[ast.ExceptHandler(
                            type=ast.Name(id="Exception", ctx=ast.Load()),
                            name=None,
                            body=[ast.Pass()],
                        )],
                        orelse=[],
                        finalbody=[],
                    )
                return node

        tree = RaiseWrapper().visit(tree)
        ast.fix_missing_locations(tree)

        if not modified:
            return source
        return ast.unparse(tree)

    def _inline_return(self, source: str) -> str:
        """Simplify functions with single return statements.

        Not a true inline — this is a placeholder that normalizes
        single-expression return patterns. In a real implementation
        this would inline simple wrapper functions.
        """
        return source  # Placeholder — safe no-op

    # ── Structural Operators ───────────────────────────────────────

    def _insert_code_block(self, source: str) -> str:
        """Insert a random logging statement into a function body."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        targets = [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.body
        ]
        if not targets:
            return source

        func = random.choice(targets)
        snippet = f"logger.debug('Self-mutation trace: {uuid.uuid4().hex[:8]}')"
        try:
            insert = ast.parse(textwrap.dedent(snippet)).body
        except SyntaxError:
            return source

        pos = random.randint(0, len(func.body))
        func.body.insert(pos, insert[0])
        return ast.unparse(tree)

    def _rewrite_function_body(self, source: str) -> str:
        """Replace a random function body with pass."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        funcs = [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not funcs:
            return source

        func = random.choice(funcs)
        func.body = [ast.Pass()]
        return ast.unparse(tree)

    def _add_parameter(self, source: str) -> str:
        """Add an optional parameter to a random function."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        funcs = [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not funcs:
            return source

        func = random.choice(funcs)
        param_name = f"_extra_{uuid.uuid4().hex[:4]}"
        func.args.args.append(ast.arg(arg=param_name, annotation=None))
        func.args.defaults.append(ast.Constant(value=None))
        return ast.unparse(tree)

    def _swap_condition(self, source: str) -> str:
        """Negate a random if-condition via wrapping in not()."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        ifs = [n for n in ast.walk(tree) if isinstance(n, ast.If)]
        if not ifs:
            return source

        if_node = random.choice(ifs)
        if_node.test = ast.UnaryOp(op=ast.Not(), operand=if_node.test)
        return ast.unparse(tree)

    def _duplicate_component(self, source: str) -> str:
        """Duplicate a random top-level class or function via deep copy."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        candidates = [
            n for n in tree.body
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not candidates:
            return source

        chosen = random.choice(candidates)
        clone: ast.AST = copy.deepcopy(chosen)
        if isinstance(clone, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            clone.name = clone.name + "_copy"
        tree.body.insert(tree.body.index(chosen) + 1, clone)
        return ast.unparse(tree)

    def _evolve_operator(self, source: str) -> str:
        """Meta-mutation: wrap an existing operator in a novel structural pattern.

        Parses the source, finds an existing private method (``_foo``),
        wraps its body in a randomly chosen structural pattern (loop,
        try/except, comprehension, conditional dispatch, or async
        gather), and appends it as a new operator method with a unique
        name.  This expands the forge's genetic vocabulary at runtime.
        """
        tree = ast.parse(source)
        operator_methods = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef)
            and n.name.startswith("_")
            and not n.name.startswith("__")
        ]
        if not operator_methods:
            return source

        base = random.choice(operator_methods)
        base_name = base.name.lstrip("_")
        new_name = f"_{base_name}_evolved_{uuid.uuid4().hex[:4]}"

        wrapper_patterns = [
            self._wrap_in_for_loop,
            self._wrap_in_try_except,
            self._wrap_in_list_comprehension,
            self._wrap_in_async_gather,
            self._wrap_in_conditional_dispatch,
        ]
        wrapper = random.choice(wrapper_patterns)
        new_func = wrapper(base, new_name)

        tree.body.append(new_func)
        return ast.unparse(tree)

    def _recombine_modules(self, source: str) -> str:
        """Cross-module recombination: splice two function bodies together.

        Finds two functions from different logical sections (separated
        by blank-line boundaries) and interleaves their bodies.  This
        is the forge's equivalent of sexual reproduction — it
        recombines genetic material from different components.
        """
        tree = ast.parse(source)
        functions = [
            n for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if len(functions) < 2:
            return source

        a, b = random.sample(functions, 2)

        body_a = list(a.body)
        body_b = list(b.body)

        split_point_a = random.randint(0, len(body_a))
        split_point_b = random.randint(0, len(body_b))

        a.body = body_a[:split_point_a] + body_b[split_point_b:]
        b.body = body_b[:split_point_b] + body_a[split_point_a:]

        return ast.unparse(tree)

    def _cross_file_recombine(self, source_a: str, source_b: str) -> str:
        """Cross-file recombination: transplant a function from source_b into source_a.

        Picks a random function from source_b and inserts a deep copy
        at the top of source_a. This is the forge's sexual reproduction
        across individual files — genetic material flows between modules.

        Returns the modified source_a with the transplanted function.
        """
        try:
            tree_a = ast.parse(source_a)
            tree_b = ast.parse(source_b)
        except SyntaxError:
            return source_a

        donors = [
            n for n in tree_b.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        if not donors:
            return source_a

        donor = copy.deepcopy(random.choice(donors))
        if isinstance(donor, (ast.FunctionDef, ast.AsyncFunctionDef)):
            donor.name = donor.name + "_x"

        insert_pos = 0
        for i, stmt in enumerate(tree_a.body):
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                insert_pos = i + 1
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Constant, ast.Str)):
                insert_pos = i + 1
            else:
                break

        tree_a.body.insert(insert_pos, donor)
        return ast.unparse(tree_a)

    async def mutate_cross_file(
        self,
        source_a: str,
        source_b: str,
        operator: str | None = None,
        component_type: str = "component",
    ) -> dict[str, Any]:
        """Apply a cross-file mutation operator requiring two sources."""
        if operator == "cross_file_recombine":
            new_source = self._cross_file_recombine(source_a, source_b)
        else:
            new_source = source_a

        return {
            "source": new_source,
            "component_type": f"{component_type}_mutated",
            "operator": operator or "cross_file_recombine",
            "operator_desc": "Cross-file function transplant",
        }

    @staticmethod
    def _wrap_in_for_loop(base: ast.FunctionDef, new_name: str) -> ast.FunctionDef:
        """Wrap the base function's body in a for-loop over a simulated range."""
        loop_var = f"_iter_{uuid.uuid4().hex[:4]}"
        loop = ast.For(
            target=ast.Name(id=loop_var, ctx=ast.Store()),
            iter=ast.Call(func=ast.Name(id="range", ctx=ast.Load()), args=[ast.Constant(value=1)], keywords=[]),
            body=list(base.body),
            orelse=[],
        )
        return ast.FunctionDef(
            name=new_name,
            args=copy.deepcopy(base.args),
            body=[loop],
            decorator_list=[],
            returns=None,
            type_params=[],
        )

    @staticmethod
    def _wrap_in_try_except(base: ast.FunctionDef, new_name: str) -> ast.FunctionDef:
        """Wrap the base function's body in a try/except that catches Exception."""
        handler = ast.ExceptHandler(
            type=ast.Name(id="Exception", ctx=ast.Load()),
            name=None,
            body=[
                ast.Raise(
                    exc=ast.Call(
                        func=ast.Attribute(value=ast.Name(id="logger", ctx=ast.Load()), attr="exception"),
                        args=[ast.Constant(value=f"Error in {new_name}")],
                        keywords=[],
                    ),
                    cause=None,
                )
            ],
        )
        try_block = ast.Try(
            body=list(base.body),
            handlers=[handler],
            orelse=[],
            finalbody=[],
        )
        return ast.FunctionDef(
            name=new_name,
            args=copy.deepcopy(base.args),
            body=[try_block],
            decorator_list=[],
            returns=None,
            type_params=[],
        )

    @staticmethod
    def _wrap_in_list_comprehension(base: ast.FunctionDef, new_name: str) -> ast.FunctionDef:
        """Wrap the base function in a list comprehension over a single-item list."""
        comp = ast.ListComp(
            elt=ast.Call(
                func=ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
                    ),
                    body=ast.Call(
                        func=ast.Name(id="list", ctx=ast.Load()),
                        args=[ast.List(elts=[ast.Constant(value=True)], ctx=ast.Load())],
                        keywords=[],
                    ),
                ),
                args=[],
                keywords=[],
            ),
            generators=[
                ast.comprehension(
                    target=ast.Name(id="_", ctx=ast.Store()),
                    iter=ast.List(elts=[ast.Constant(value=1)], ctx=ast.Load()),
                    ifs=[],
                    is_async=0,
                )
            ],
        )
        return ast.FunctionDef(
            name=new_name,
            args=copy.deepcopy(base.args),
            body=base.body + [ast.Expr(value=comp)],
            decorator_list=[],
            returns=None,
            type_params=[],
        )

    @staticmethod
    def _wrap_in_async_gather(base: ast.FunctionDef, new_name: str) -> ast.FunctionDef:
        """Wrap the base function body in an asyncio.gather pattern."""
        gather_call = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="asyncio", ctx=ast.Load()),
                    attr="gather",
                ),
                args=[ast.Call(func=ast.Name(id=new_name, ctx=ast.Load()), args=[], keywords=[])],
                keywords=[],
            )
        )
        return ast.FunctionDef(
            name=new_name,
            args=copy.deepcopy(base.args),
            body=list(base.body) + [gather_call],
            decorator_list=[],
            returns=None,
            type_params=[],
        )

    @staticmethod
    def _wrap_in_conditional_dispatch(base: ast.FunctionDef, new_name: str) -> ast.FunctionDef:
        """Wrap the base function in a conditional dispatch pattern."""
        dispatch_var = f"_mode_{uuid.uuid4().hex[:4]}"
        if_node = ast.If(
            test=ast.Compare(
                left=ast.Name(id=dispatch_var, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value="standard")],
            ),
            body=list(base.body),
            orelse=[
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="logger", ctx=ast.Load()),
                            attr="warning",
                        ),
                        args=[ast.Constant(value=f"Unknown mode in {new_name}")],
                        keywords=[],
                    )
                )
            ],
        )
        new_args = copy.deepcopy(base.args)
        new_args.args.append(ast.arg(arg=dispatch_var, annotation=ast.Name(id="str", ctx=ast.Load())))
        return ast.FunctionDef(
            name=new_name,
            args=new_args,
            body=[if_node],
            decorator_list=[],
            returns=None,
            type_params=[],
        )

    def get_operators(self, category: str = "all") -> list[str]:
        """Return operator names, optionally filtered by category.

        Args:
            category: 'all', 'constructive', or 'structural'.

        Returns:
            List of operator names.
        """
        if category == "constructive":
            return list(CONSTRUCTIVE_OPERATORS)
        elif category == "structural":
            return list(STRUCTURAL_OPERATORS)
        return list(ALL_OPERATORS)

    def get_operator_descriptions(self) -> dict[str, str]:
        """Return all operator descriptions."""
        return dict(OPERATOR_DESCRIPTIONS)
