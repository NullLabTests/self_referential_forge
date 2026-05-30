"""Tests for the SelfWriter — disk write-back and module reload lifecycle."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from forge.self_writer import SelfWriter, WriteResult, SmokeTestConfig


@pytest.fixture
def forge_root() -> Path:
    """Create a temporary forge root with a module to mutate."""
    root = Path(tempfile.mkdtemp(prefix="forge_test_"))
    pkg = root / "forge"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("# forge package\nVERSION = '1.0'\n")
    (pkg / "target.py").write_text(
        "def greet() -> str:\n    return 'hello'\n\n"
        "def add(a: int, b: int) -> int:\n    return a + b\n"
    )
    return root


@pytest.fixture
def writer(forge_root: Path) -> SelfWriter:
    return SelfWriter(
        forge_root=forge_root,
        backup_dir=forge_root / "archive" / "backups",
        smoke_config=SmokeTestConfig(
            verify_syntax=True,
            verify_module_importable=False,
            verify_key_exports=False,
            call_test_function=None,
        ),
    )


def _run(coro):
    """Run a coroutine synchronously in a fresh event loop."""
    return asyncio.run(coro)


class TestSelfWriter:
    """Test suite for SelfWriter — path resolution, backup, write, rollback."""

    def test_resolve_path_by_glob(self, writer: SelfWriter) -> None:
        """Unknown component types resolve via glob search."""
        path = writer.resolve_path("forge_target")
        assert path is not None
        assert path.name == "target.py"
        assert path.parent.name == "forge"

    def test_resolve_path_unknown(self, writer: SelfWriter) -> None:
        """Bogus component type returns None."""
        path = writer.resolve_path("zzz_nonexistent_xxxx")
        assert path is None

    def test_resolve_module_name_target(self, writer: SelfWriter, forge_root: Path) -> None:
        """File paths resolve to correct module names."""
        path = forge_root / "forge" / "target.py"
        name = writer.resolve_module_name(path)
        assert name == "forge.target"

    def test_resolve_module_name_init(self, writer: SelfWriter, forge_root: Path) -> None:
        """__init__.py resolves to the parent package name."""
        path = forge_root / "forge" / "__init__.py"
        name = writer.resolve_module_name(path)
        assert name == "forge"

    def test_create_backup(self, writer: SelfWriter, forge_root: Path) -> None:
        """Backup files are created and match original content."""
        target = forge_root / "forge" / "target.py"
        backup = writer.create_backup(target)
        assert backup.exists()
        assert backup.read_text() == target.read_text()
        assert "backups" in str(backup)

    def test_apply_valid_mutation(self, writer: SelfWriter, forge_root: Path) -> None:
        """A valid mutation is written to disk."""
        new_source = (
            "def greet() -> str:\n"
            "    return 'hello world'\n\n"
            "def add(a: int, b: int) -> int:\n"
            "    return a + b\n"
        )

        result = _run(writer.apply_mutation(
            source=new_source,
            component_type="forge_target",
        ))

        # File should be written even if module not reloadable in test env
        target_path = forge_root / "forge" / "target.py"
        assert target_path.read_text() == new_source
        assert result.file_path == target_path
        assert result.backup_path is not None
        assert result.backup_path.exists()

    def test_apply_invalid_syntax_fails(self, writer: SelfWriter, forge_root: Path) -> None:
        """A mutation with invalid syntax should fail the smoke test."""
        target = forge_root / "forge" / "target.py"
        original = target.read_text()

        bad_source = "def broken(: missing paren"

        result = _run(writer.apply_mutation(
            source=bad_source,
            component_type="forge_target",
            original_source=original,
        ))

        assert not result.smoke_test_passed

    def test_rollback_from_backup(self, writer: SelfWriter, forge_root: Path) -> None:
        """Rollback restores original source from backup."""
        target = forge_root / "forge" / "target.py"
        original = target.read_text()

        backup = writer.create_backup(target)
        target.write_text("# garbage")

        ok = writer.rollback(backup, target)
        assert ok
        assert target.read_text() == original

    def test_rollback_without_backup(self, writer: SelfWriter, forge_root: Path) -> None:
        """Rollback without backup file uses in-memory original."""
        target = forge_root / "forge" / "target.py"
        original = target.read_text()

        writer._original_sources[str(target)] = original
        target.write_text("# garbage")

        ok = writer.rollback(None, target)
        assert ok
        assert target.read_text() == original

    def test_get_available_targets(self, writer: SelfWriter, forge_root: Path) -> None:
        """Available targets lists all .py files with correct module names."""
        targets = writer.get_available_targets()
        assert len(targets) >= 2
        modules = [t["module"] for t in targets]
        assert "forge.target" in modules
        assert "forge" in modules

    def test_resolve_path_map_entries(self, writer: SelfWriter, forge_root: Path) -> None:
        """All non-empty COMPONENT_PATH_MAP entries resolve to .py files."""
        for key, rel in writer.COMPONENT_PATH_MAP.items():
            if not rel:
                continue
            path = writer.resolve_path(key)
            if path is not None:
                assert path.suffix == ".py"

    def test_apply_to_nonexistent_component(self, writer: SelfWriter) -> None:
        """Applying to a bogus component returns failure gracefully."""
        result = _run(writer.apply_mutation(
            source="x = 1",
            component_type="zzz_nonexistent",
        ))
        assert not result.success
        assert result.error

    def test_backup_preserves_original(self, writer: SelfWriter, forge_root: Path) -> None:
        """Backup file content matches the pre-mutation original."""
        target = forge_root / "forge" / "target.py"
        original = target.read_text()

        writer.create_backup(target)
        target.write_text("# mutated")

        # The backup should have the original, not the mutation
        backups = list((forge_root / "archive" / "backups").iterdir())
        assert len(backups) >= 1
        latest = max(backups, key=lambda p: p.stat().st_mtime)
        assert latest.read_text() == original


class TestSmokeTestConfig:
    """Tests for SmokeTestConfig dataclass."""

    def test_defaults(self) -> None:
        cfg = SmokeTestConfig()
        assert cfg.verify_syntax
        assert cfg.verify_module_importable
        assert cfg.call_test_function is None

    def test_custom_values(self) -> None:
        cfg = SmokeTestConfig(
            verify_syntax=False,
            call_test_function="run",
            call_test_timeout=5.0,
        )
        assert not cfg.verify_syntax
        assert cfg.call_test_function == "run"
        assert cfg.call_test_timeout == 5.0


class TestWriteResult:
    """Tests for WriteResult dataclass."""

    def test_default_creation(self) -> None:
        result = WriteResult(success=True, file_path=Path("test.py"))
        assert result.success
        assert result.module_name == ""
        assert not result.reloaded

    def test_failure_result(self) -> None:
        result = WriteResult(
            success=False,
            file_path=Path("test.py"),
            error="Something went wrong",
        )
        assert not result.success
        assert "Something went wrong" in result.error

    def test_smoke_test_tracking(self) -> None:
        result = WriteResult(
            success=True,
            file_path=Path("test.py"),
            smoke_test_passed=True,
            reloaded=True,
        )
        assert result.smoke_test_passed
        assert result.reloaded
