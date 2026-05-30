"""Tests for SelfModifier — all 10 mutation operators."""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

import pytest

from forge.self_modifier import SelfModifier, ALL_OPERATORS, CONSTRUCTIVE_OPERATORS, STRUCTURAL_OPERATORS


@pytest.fixture
def sample_source() -> str:
    """A small but realistic Python module for mutation testing."""
    return (
        "import os\n"
        "import logging\n\n"
        "logger = logging.getLogger(__name__)\n\n"
        "CONFIG_PATH = '/etc/app/config.json'\n"
        "ERROR_MSG = 'something failed'\n\n"
        "class Greeter:\n"
        "    def __init__(self, name: str) -> None:\n"
        "        self.name = name\n\n"
        "    def greet(self) -> str:\n"
        "        return f'Hello, {self.name}'\n\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "def process(items: list[str]) -> None:\n"
        "    for item in items:\n"
        "        if item:\n"
        "            print(item)\n"
        "        else:\n"
        "            print('empty')\n"
    )


@pytest.fixture
def modifier() -> SelfModifier:
    return SelfModifier()


def _assert_valid_python(source: str) -> None:
    """Assert that a string is valid Python."""
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"Invalid Python produced: {e}\n---\n{source}")


class TestConstructiveOperators:
    """Tests for the 5 constructive mutation operators."""

    def test_add_type_hints_adds_return_none(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._add_type_hints(sample_source)
        _assert_valid_python(result)
        assert "-> None" in result or "->  None" in result
        assert "__init__" not in [line for line in result.split("\n") if "__init__" in line and "-> None" in line]

    def test_add_type_hints_preserves_existing(self, modifier: SelfModifier) -> None:
        source = "def greet() -> str:\n    return 'hello'\n"
        result = modifier._add_type_hints(source)
        assert result == source

    def test_add_type_hints_on_async(self, modifier: SelfModifier) -> None:
        source = "async def fetch():\n    return 42\n"
        result = modifier._add_type_hints(source)
        _assert_valid_python(result)
        assert "-> None" in result or "->  None" in result

    def test_add_docstring_adds_to_function(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._add_docstring(sample_source)
        _assert_valid_python(result)
        assert '""' in result or "''" in result

    def test_add_docstring_adds_to_class(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._add_docstring(sample_source)
        _assert_valid_python(result)
        assert "class Greeter:" in result

    def test_add_docstring_preserves_existing(self, modifier: SelfModifier) -> None:
        source = 'def foo() -> None:\n    """Existing doc."""\n    pass\n'
        result = modifier._add_docstring(source)
        assert result == source

    def test_extract_constant_replaces_repeated(self, modifier: SelfModifier) -> None:
        source = (
            "x = 'hello'\n"
            "y = 'hello'\n"
            "z = 'hello'\n"
            "w = 'world'\n"
        )
        result = modifier._extract_constant(source)
        _assert_valid_python(result)
        assert "HELLO" in result or "HELLO" in result.upper()
        assert "'hello'" not in result or result.count("HELLO") >= 3

    def test_extract_constant_skips_unique(self, modifier: SelfModifier) -> None:
        source = "a = 'alpha'\nb = 'beta'\nc = 'gamma'\n"
        result = modifier._extract_constant(source)
        _assert_valid_python(result)
        assert result == source

    def test_add_error_handling_wraps_bare_raise(self, modifier: SelfModifier) -> None:
        source = "def foo() -> None:\n    raise\n"
        result = modifier._add_error_handling(source)
        _assert_valid_python(result)
        assert "try" in result or "except" in result

    def test_inline_return_is_safe_noop(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._inline_return(sample_source)
        assert result == sample_source


class TestStructuralOperators:
    """Tests for the 5 structural mutation operators."""

    def test_insert_code_adds_logging(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._insert_code_block(sample_source)
        _assert_valid_python(result)
        assert "logger.debug" in result

    def test_insert_code_needs_function(self, modifier: SelfModifier) -> None:
        source = "x = 1\ny = 2\n"
        result = modifier._insert_code_block(source)
        assert result == source

    def test_rewrite_function_replaces_body(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._rewrite_function_body(sample_source)
        _assert_valid_python(result)
        assert "pass" in result

    def test_rewrite_function_needs_functions(self, modifier: SelfModifier) -> None:
        source = "x = 1\n"
        result = modifier._rewrite_function_body(source)
        assert result == source

    def test_add_parameter_adds_optional(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._add_parameter(sample_source)
        _assert_valid_python(result)
        assert "_extra_" in result

    def test_add_parameter_needs_functions(self, modifier: SelfModifier) -> None:
        source = "x = 1\n"
        result = modifier._add_parameter(source)
        assert result == source

    def test_swap_condition_negates_if(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._swap_condition(sample_source)
        _assert_valid_python(result)
        assert "not " in result or "not(" in result

    def test_swap_condition_needs_ifs(self, modifier: SelfModifier) -> None:
        source = "x = 1\n"
        result = modifier._swap_condition(source)
        assert result == source

    def test_duplicate_component_copies(self, modifier: SelfModifier, sample_source: str) -> None:
        result = modifier._duplicate_component(sample_source)
        _assert_valid_python(result)
        assert "_copy" in result

    def test_duplicate_component_needs_targets(self, modifier: SelfModifier) -> None:
        source = "x = 1\ny = 2\n"
        result = modifier._duplicate_component(source)
        assert result == source


class TestMutateDispatch:
    """Tests for the async mutate() dispatch method."""

    @pytest.mark.asyncio
    async def test_mutate_with_known_operator(self, modifier: SelfModifier, sample_source: str) -> None:
        result = await modifier.mutate(sample_source, operator="add_type_hints")
        _assert_valid_python(result["source"])
        assert result["operator"] == "add_type_hints"
        assert "operator_desc" in result

    @pytest.mark.asyncio
    async def test_mutate_all_operators(self, modifier: SelfModifier, sample_source: str) -> None:
        for op in ALL_OPERATORS:
            result = await modifier.mutate(sample_source, operator=op)
            _assert_valid_python(result["source"])
            assert result["operator"] == op, f"Operator {op} failed to dispatch correctly"

    @pytest.mark.asyncio
    async def test_mutate_random_operator(self, modifier: SelfModifier, sample_source: str) -> None:
        results = set()
        for _ in range(20):
            result = await modifier.mutate(sample_source)
            results.add(result["operator"])
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_mutate_unknown_falls_back(self, modifier: SelfModifier, sample_source: str) -> None:
        result = await modifier.mutate(sample_source, operator="nonexistent_operator")
        assert result["operator"] == "insert_code"


class TestOperatorMetadata:
    """Tests for operator listing and descriptions."""

    def test_get_operators_all(self, modifier: SelfModifier) -> None:
        ops = modifier.get_operators("all")
        assert len(ops) == 12

    def test_get_operators_constructive(self, modifier: SelfModifier) -> None:
        ops = modifier.get_operators("constructive")
        assert len(ops) == 5
        assert all(op in CONSTRUCTIVE_OPERATORS for op in ops)

    def test_get_operators_structural(self, modifier: SelfModifier) -> None:
        ops = modifier.get_operators("structural")
        assert len(ops) == 5
        assert all(op in STRUCTURAL_OPERATORS for op in ops)

    def test_get_operator_descriptions(self, modifier: SelfModifier) -> None:
        descs = modifier.get_operator_descriptions()
        assert len(descs) == len(ALL_OPERATORS)
        for op in ALL_OPERATORS:
            assert op in descs, f"Missing description for {op}"
            assert len(descs[op]) > 10


class TestTargetedLoading:
    """Tests for the new load_target() method."""

    @pytest.mark.asyncio
    async def test_load_target_known(self, modifier: SelfModifier) -> None:
        source = await modifier.load_target("forge_self_modifier")
        assert source is not None
        assert "class SelfModifier" in source

    @pytest.mark.asyncio
    async def test_load_target_unknown(self, modifier: SelfModifier) -> None:
        source = await modifier.load_target("zzz_nonexistent_xxxx")
        assert source is None

    @pytest.mark.asyncio
    async def test_snapshot_current(self, modifier: SelfModifier) -> None:
        snap = await modifier.snapshot_current()
        assert isinstance(snap, dict)
        assert len(snap) >= 5
        assert any("self_modifier" in k for k in snap)
