"""Self-writer — applies mutations to the forge's own source files.

This is the component that makes the forge truly self-referential:
it writes mutated source code back to the forge's own .py files,
reloads the modified modules into the running Python process,
and verifies that the forge still functions correctly.

Lifecycle for a single mutation application:
  1. BACKUP: copy original file to archive/backups/
  2. WRITE:  write mutated source to the actual .py file
  3. RELOAD: importlib.reload() the modified module
  4. SMOKE:  verify the module is functional (syntax, key exports, basic call)
  5. COMMIT: if smoke passes, keep the change
  6. ROLLBACK: if smoke fails, restore from backup, reload original
"""

from __future__ import annotations

import ast
import importlib
import logging
import shutil
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class WriteResult:
    """Result of applying a self-modification to disk."""

    success: bool
    file_path: Path
    backup_path: Path | None = None
    module_name: str = ""
    smoke_test_passed: bool = False
    reloaded: bool = False
    error: str = ""
    execution_time: float = 0.0


@dataclass
class SmokeTestConfig:
    """Configuration for post-reload smoke tests."""

    verify_syntax: bool = True
    verify_module_importable: bool = True
    verify_key_exports: bool = True
    call_test_function: str | None = None
    call_test_timeout: float = 2.0


class SelfWriter:
    """Writes mutated forge source to disk and reloads the running module.

    The SelfWriter is the bridge between in-memory evolution (modifying
    source strings) and actual self-modification (changing the forge's
    own .py files and reloading them into the running process).

    Usage:
        writer = SelfWriter(forge_root)
        result = writer.apply_mutation(
            source="...new source...",
            component_type="forge_orchestrator",
            original_source="...old source...",
        )
        if result.success:
            logger.info("Self-modification applied")
        else:
            writer.rollback(result.backup_path, result.file_path)
    """

    COMPONENT_PATH_MAP: dict[str, str] = {
        "forge_orchestrator": "forge/orchestrator.py",
        "forge_self_modifier": "forge/self_modifier.py",
        "forge_self_writer": "forge/self_writer.py",
        "forge___main__": "forge/__main__.py",
        "meta_evolution_meta_evolver": "meta_evolution/meta_evolver.py",
        "evaluators_evaluator": "evaluators/evaluator.py",
        "safety_safety_validator": "safety/safety_validator.py",
        "safety_policy": "safety/policy.py",
        "safety_audit": "safety/audit.py",
        "safety_sandbox": "safety/sandbox.py",
        "archive_archivist": "archive/archivist.py",
        "dashboard_main": "dashboard/main.py",
        "benchmarks_benchmark_suite": "benchmarks/benchmark_suite.py",
        "baseline": "",
    }

    def __init__(
        self,
        forge_root: str | Path | None = None,
        backup_dir: str | Path | None = None,
        smoke_config: SmokeTestConfig | None = None,
    ) -> None:
        self._forge_root = Path(forge_root) if forge_root else Path(__file__).resolve().parent.parent
        self._backup_dir = Path(backup_dir) if backup_dir else self._forge_root / "archive" / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._smoke_config = smoke_config or SmokeTestConfig()
        self._original_sources: dict[str, str] = {}

    def resolve_path(self, component_type: str) -> Path | None:
        """Resolve a component type string to an actual file path.

        Args:
            component_type: Component type like 'forge_orchestrator_mutated'
                or 'forge.orchestrator' or a direct 'module.attribute' path.

        Returns:
            Path to the .py file, or None if it cannot be resolved.
        """
        clean = component_type.replace("_mutated", "").replace("-", "_")

        if clean in self.COMPONENT_PATH_MAP:
            rel = self.COMPONENT_PATH_MAP[clean]
            if not rel:
                return None
            return self._forge_root / rel

        dot_path = clean.replace("_", ".")
        candidate = self._forge_root / f"{dot_path.replace('.', '/')}.py"
        if candidate.exists():
            return candidate

        for pattern in (clean, clean.replace("_", "/"), clean.split("_")[0] if "_" in clean else ""):
            for fpath in self._forge_root.rglob(f"{pattern.split('/')[-1]}.py"):
                if ".git" not in fpath.parts and "__pycache__" not in fpath.parts:
                    return fpath

        return None

    def resolve_module_name(self, file_path: Path) -> str:
        """Resolve a file path to its Python module name.

        Args:
            file_path: Absolute path to a .py file.

        Returns:
            Module name like 'forge.orchestrator'.
        """
        try:
            rel = file_path.resolve().relative_to(self._forge_root.resolve())
            parts = list(rel.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            elif parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]
            return ".".join(parts)
        except ValueError:
            return file_path.stem

    def create_backup(self, file_path: Path) -> Path:
        """Create a timestamped backup of a forge source file.

        Args:
            file_path: Path to the file to back up.

        Returns:
            Path to the backup file.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        rel = file_path.resolve().relative_to(self._forge_root.resolve())
        backup_name = f"{timestamp}_{'_'.join(rel.parts)}.bak"
        backup_path = self._backup_dir / backup_name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(file_path), str(backup_path))
        self._original_sources[str(file_path)] = file_path.read_text()
        logger.debug("Backup created: %s → %s", file_path, backup_path)
        return backup_path

    async def apply_mutation(
        self,
        source: str,
        component_type: str,
        original_source: str = "",
    ) -> WriteResult:
        """Apply a mutation to the forge's own source code.

        Full lifecycle:
          1. Resolve the file path from component_type
          2. Back up the original file
          3. Write the mutated source to disk
          4. Reload the modified module
          5. Run smoke tests on the reloaded module
          6. Return result (caller decides commit vs rollback)

        Args:
            source: The mutated source code to write.
            component_type: Type string identifying the component.
            original_source: Original source for rollback if needed.

        Returns:
            WriteResult with success/failure and diagnostic info.
        """
        start = time.time()
        file_path = self.resolve_path(component_type)

        if file_path is None:
            return WriteResult(
                success=False,
                file_path=Path(component_type),
                error=f"Cannot resolve path for component_type '{component_type}'",
                execution_time=time.time() - start,
            )

        if not file_path.exists():
            return WriteResult(
                success=False,
                file_path=file_path,
                error=f"Target file does not exist: {file_path}",
                execution_time=time.time() - start,
            )

        try:
            backup_path = self.create_backup(file_path)

            if original_source:
                self._original_sources[str(file_path)] = original_source

            file_path.write_text(source)
            logger.info("Wrote mutated source to %s (%d bytes)", file_path, len(source))

            module_name = self.resolve_module_name(file_path)
            module = self._reload_module(module_name)
            reloaded = module is not None

            smoke_passed = False
            if module is not None:
                smoke_passed = await self._run_smoke_test(module, module_name)

            elapsed = time.time() - start
            result = WriteResult(
                success=smoke_passed,
                file_path=file_path,
                backup_path=backup_path,
                module_name=module_name,
                smoke_test_passed=smoke_passed,
                reloaded=reloaded,
                execution_time=elapsed,
            )

            if smoke_passed:
                logger.info(
                    "Self-modification applied: %s (module=%s, %.2fs)",
                    file_path.name, module_name, elapsed,
                )
            else:
                logger.warning(
                    "Smoke test failed for %s — rollback recommended",
                    file_path.name,
                )

            return result

        except Exception as exc:
            elapsed = time.time() - start
            logger.error("Self-modification failed for %s: %s", component_type, exc)
            return WriteResult(
                success=False,
                file_path=file_path or Path(component_type),
                error=str(exc),
                execution_time=elapsed,
            )

    def _reload_module(self, module_name: str) -> ModuleType | None:
        """Reload a module in the running Python process.

        Args:
            module_name: Fully-qualified module name to reload.

        Returns:
            The reloaded module, or None on failure.
        """
        if module_name not in sys.modules:
            logger.warning("Module '%s' is not loaded, cannot reload", module_name)
            return None

        try:
            module = importlib.reload(sys.modules[module_name])
            logger.info("Reloaded module: %s", module_name)
            return module
        except Exception as exc:
            logger.error("Failed to reload module '%s': %s\n%s", module_name, exc, traceback.format_exc())
            return None

    async def _run_smoke_test(self, module: ModuleType, module_name: str) -> bool:
        """Run smoke tests on a reloaded module to verify it is functional.

        Args:
            module: The reloaded module object.
            module_name: Name of the module (for diagnostics).

        Returns:
            True if all smoke tests pass.
        """
        checks: list[tuple[str, Callable[[], bool]]] = []

        if self._smoke_config.verify_module_importable:
            def check_importable() -> bool:
                return module is not None

            checks.append(("module_importable", check_importable))

        if self._smoke_config.verify_syntax:
            source: str = ""
            try:
                source_file = module.__file__
                if source_file:
                    source = Path(source_file).read_text()
            except (AttributeError, OSError):
                pass

            def check_syntax(src: str = source) -> bool:
                if not src:
                    return True
                try:
                    ast.parse(src)
                    return True
                except SyntaxError:
                    return False

            checks.append(("syntax_valid", check_syntax))

        if self._smoke_config.verify_key_exports:
            def check_exports(mod: ModuleType = module) -> bool:
                if hasattr(mod, "__all__"):
                    exports = mod.__all__
                    for name in exports[:5]:
                        if not hasattr(mod, name):
                            logger.warning("Smoke: missing export '%s' in %s", name, module_name)
                            return False
                return True

            checks.append(("key_exports", check_exports))

        if self._smoke_config.call_test_function and hasattr(module, self._smoke_config.call_test_function):
            func_name = self._smoke_config.call_test_function

            def check_func(mod: ModuleType = module, fn: str = func_name) -> bool:
                try:
                    func = getattr(mod, fn)
                    if callable(func):
                        result = func()
                        return result is not False
                except Exception as exc:
                    logger.warning("Smoke: %s() raised %s", fn, exc)
                    return False
                return True

            checks.append((f"call_{func_name}", check_func))

        all_passed = True
        for name, check_fn in checks:
            try:
                passed = check_fn()
                if not passed:
                    logger.warning("Smoke test '%s' FAILED for module %s", name, module_name)
                    all_passed = False
                else:
                    logger.debug("Smoke test '%s' PASSED for module %s", name, module_name)
            except Exception as exc:
                logger.warning("Smoke test '%s' raised exception: %s", name, exc)
                all_passed = False

        return all_passed

    def rollback(self, backup_path: Path | None, target_path: Path) -> bool:
        """Rollback a mutation by restoring from backup.

        Args:
            backup_path: Path to the backup file.
            target_path: Path to the target file to restore.

        Returns:
            True if rollback succeeded.
        """
        if backup_path is None or not backup_path.exists():
            original = self._original_sources.get(str(target_path))
            if original:
                try:
                    target_path.write_text(original)
                    logger.info("Rolled back %s from in-memory original", target_path)
                    return True
                except Exception as exc:
                    logger.error("In-memory rollback failed for %s: %s", target_path, exc)
                    return False
            logger.warning("No backup available for %s", target_path)
            return False

        try:
            shutil.copy2(str(backup_path), str(target_path))
            logger.info("Rolled back %s from backup %s", target_path, backup_path)
            module_name = self.resolve_module_name(target_path)
            self._reload_module(module_name)
            return True
        except Exception as exc:
            logger.error("Backup rollback failed for %s: %s", target_path, exc)
            return False

    def get_available_targets(self) -> list[dict[str, str]]:
        """Return a list of all forge files that can be mutated.

        Returns:
            List of dicts with 'path', 'module', 'component_type' keys.
        """
        targets: list[dict[str, str]] = []
        for fpath in sorted(self._forge_root.rglob("*.py")):
            if ".git" in fpath.parts or "__pycache__" in fpath.parts:
                continue
            rel = fpath.relative_to(self._forge_root)
            module_name = self.resolve_module_name(fpath)
            component_key = module_name.replace(".", "_")
            targets.append({
                "path": str(rel),
                "module": module_name,
                "component_type": component_key,
            })
        return targets
