"""Builds every release package from the single source tree (docs/VERSIONS.md).

    python tools/build_release.py           # rebuild release/<package>.zip and release/<package>/SHA256SUMS.txt
    python tools/build_release.py --check   # exit 1 if any committed package differs from a fresh build

The NinjaScript and Pine files exist once in the repository, under ninjatrader/ and pine/. A package directory holds
only its hand-written documents (INSTALL, presets). The zip is assembled here: the code copied from its source path,
the documents, and a SHA256SUMS.txt over all of them. Entries are sorted and stamped 1980-01-01 with fixed permissions,
so the same sources always give the same contents. release/SHA256SUMS.txt lists each zip's sha256.
"""
from __future__ import annotations

import hashlib
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "release"
B = "ninjatrader/Strategies/MnqNoiseMomentum.cs"
ENGINE = "ninjatrader/AddOns/MnqNoiseEngine.cs"
STRAT = "bin/Custom/Strategies/"
ADDON = "bin/Custom/AddOns/MnqNoiseEngine.cs"

PACKAGES = {
    "MnqMomentumB_v1.1": {
        "code": {STRAT + "MnqNoiseMomentum.cs": B, ADDON: ENGINE},
        "docs": ["INSTALL.md", "PRESET_B-PRACTICE-v1.1.md", "PRESET_B-NATIVE-v1.1.md"],
    },
    "PineReference_v1.5": {
        "code": {STRAT + "MnqNoiseMomentum.cs": B, ADDON: ENGINE,
                 "pine/mnq_noise_momentum_v1.5_user.pine": "pine/reference/mnq_noise_momentum_v1.5_user.pine"},
        "docs": ["INSTALL.md", "PRESETS.md"],
    },
    "MnqMomentumC_candidate": {
        "code": {STRAT + "MnqMomentumC.cs": "ninjatrader/Strategies/MnqMomentumC.cs", ADDON: ENGINE},
        "docs": ["INSTALL.md", "PRESET_C-CANDIDATE.md"],
    },
    "MnqCandidateD_candidate": {
        "code": {STRAT + "MnqCandidateD.cs": "ninjatrader/Strategies/MnqCandidateD.cs", ADDON: ENGINE},
        "docs": ["INSTALL.md", "PRESET_D-CANDIDATE.md", "PRESET_F-CANDIDATE.md"],
    },
    "MnqMomentumRunner_candidate": {
        "code": {STRAT + "MnqMomentumRunner.cs": "ninjatrader/Strategies/MnqMomentumRunner.cs", ADDON: ENGINE},
        "docs": ["INSTALL.md", "PRESET_RUNNER-CANDIDATE.md"],
    },
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def contents(name: str) -> dict[str, bytes]:
    """Every file of the package (path inside the package -> bytes), SHA256SUMS.txt included."""
    spec = PACKAGES[name]
    files = {dst: (ROOT / src).read_bytes() for dst, src in spec["code"].items()}
    files.update({d: (REL / name / d).read_bytes() for d in spec["docs"]})
    sums = "".join(f"{sha(files[p])}  {p}\n" for p in sorted(files))
    files["SHA256SUMS.txt"] = sums.encode()
    return files


def zip_bytes(name: str, files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path in sorted(files):
            info = zipfile.ZipInfo(f"{name}/{path}", date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, files[path], compresslevel=9)
    return buf.getvalue()


def zip_contents(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as z:
        return {i.filename: z.read(i) for i in z.infolist() if not i.is_dir()}


def main() -> int:
    check = "--check" in sys.argv[1:]
    problems, index = [], []
    for name in PACKAGES:
        files = contents(name)
        built = zip_bytes(name, files)
        zpath, spath = REL / f"{name}.zip", REL / name / "SHA256SUMS.txt"
        if check:
            want = {f"{name}/{p}": b for p, b in files.items()}
            if not zpath.exists() or zip_contents(zpath) != want:
                problems.append(f"{zpath.name} differs from its sources")
            if not spath.exists() or spath.read_bytes() != files["SHA256SUMS.txt"]:
                problems.append(f"{name}/SHA256SUMS.txt differs from its sources")
            extra = [p for p in (REL / name).rglob("*") if p.is_file()
                     and p.relative_to(REL / name).as_posix() not in PACKAGES[name]["docs"] + ["SHA256SUMS.txt"]]
            problems += [f"{p.relative_to(ROOT)} is not a package document (code lives only in its source)"
                         for p in extra]
        else:
            zpath.write_bytes(built)
            spath.write_bytes(files["SHA256SUMS.txt"])
        index.append(f"{sha(zpath.read_bytes()) if check else sha(built)}  {zpath.name}\n")
    known = {f"{n}.zip" for n in PACKAGES}
    problems += [f"release/{p.name} belongs to no package" for p in REL.glob("*.zip") if p.name not in known]
    if not check:
        (REL / "SHA256SUMS.txt").write_text("".join(sorted(index, key=lambda x: x.split()[1])))
    for p in problems:
        print(p)
    print("ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
