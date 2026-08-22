"""Run two clean pipeline builds in temp dirs and assert byte-identical output."""

from __future__ import annotations

import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from srdlib import SOURCE_FILE

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = [
    "extract_srd.py",
    "build_manifest.py",
    "build_bundle.py",
    "build_llms_full.py",
    "build_search_index.py",
    "build_collection_indexes.py",
    "build_coverage.py",
    "build_review_ledger.py",
]


def build_in(workdir: Path) -> Path:
    shutil.copy2(ROOT / SOURCE_FILE, workdir / SOURCE_FILE)
    shutil.copytree(ROOT / "scripts", workdir / "scripts")
    shutil.copytree(ROOT / "systems", workdir / "systems")
    for script in PIPELINE:
        subprocess.run(
            [sys.executable, f"scripts/{script}", "--root", "."],
            cwd=workdir,
            check=True,
            capture_output=True,
        )
    return workdir / "objects"


def compare(dir_a: Path, dir_b: Path):
    mismatches = []
    files_a = sorted(p.relative_to(dir_a) for p in dir_a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(dir_b) for p in dir_b.rglob("*") if p.is_file())
    if files_a != files_b:
        mismatches.append("file listings differ")
    for rel in files_a:
        if not filecmp.cmp(dir_a / rel, dir_b / rel, shallow=False):
            mismatches.append(str(rel))
    return mismatches, len(files_a)


def main():
    with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
        out_a = build_in(Path(tmp_a))
        out_b = build_in(Path(tmp_b))
        mismatches, total = compare(out_a, out_b)
        if not filecmp.cmp(
            Path(tmp_a) / "llms-full.txt", Path(tmp_b) / "llms-full.txt", shallow=False
        ):
            mismatches.append("llms-full.txt")
        total += 1
    if mismatches:
        print("\n".join(mismatches[:20]))
        print(f"FAIL: {len(mismatches)} non-deterministic artifacts")
        sys.exit(1)
    print(f"OK: {total} artifacts byte-identical across two clean builds")


if __name__ == "__main__":
    main()
