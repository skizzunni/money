"""Single-source releases (docs/VERSIONS.md): every package is a reproducible build of the one source tree."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tracked(pattern):
    out = subprocess.run(["git", "ls-files", pattern], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.split()]


def test_committed_packages_are_exact_builds_of_the_sources():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_release.py"), "--check"], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_code_exists_only_at_its_source_path():
    code = [p.relative_to(ROOT).as_posix() for p in tracked("*.cs") + tracked("*.pine")]
    stray = [p for p in code if p.startswith("release/")]
    assert not stray, stray


def test_each_strategy_class_is_defined_once():
    classes = {}
    for p in tracked("*.cs"):
        src = p.read_text(errors="replace")
        for name in re.findall(r"public\s+(?:partial\s+)?class\s+(\w+)\s*:\s*Strategy\b", src):
            classes.setdefault(name, []).append(p.relative_to(ROOT).as_posix())
    assert classes and all(len(v) == 1 for v in classes.values()), classes
