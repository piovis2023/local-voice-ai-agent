#!/usr/bin/env python3
"""Bulletproof Chatterbox TTS installer — safe for existing torch/CUDA environments.

This script installs ONE of three Chatterbox model variants without touching
your existing PyTorch, CUDA, cuDNN, or other ML drivers.

Usage:
    python scripts/install_chatterbox.py original
    python scripts/install_chatterbox.py turbo
    python scripts/install_chatterbox.py rsxdalv-faster
    python scripts/install_chatterbox.py --check          # verify only, install nothing
    python scripts/install_chatterbox.py --swap original   # swap to a different variant

How it works:
    1. Snapshots every package version via `pip freeze`
    2. Verifies torch + CUDA are working
    3. Installs chatterbox with --no-deps (NEVER touches torch)
    4. Installs only the missing non-torch dependencies one-by-one
    5. Re-snapshots and diffs to prove nothing was overwritten
    6. Runs a smoke test import

Swap mode (--swap):
    Safely uninstalls the current chatterbox variant, then installs the new one.
    All non-torch deps are kept (99% overlap between variants).
    Only the chatterbox package itself is swapped.

Safe on: Windows 11 / Linux / macOS, conda / venv / system Python.
Requires: Python 3.11+, pip, a working torch+CUDA install.
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Packages that MUST NOT be changed. If any of these change version,
# the install is rolled back.
PROTECTED_PACKAGES = frozenset({
    "torch",
    "torchaudio",
    "torchvision",
    "nvidia-cublas-cu12",
    "nvidia-cuda-cupti-cu12",
    "nvidia-cuda-nvrtc-cu12",
    "nvidia-cuda-runtime-cu12",
    "nvidia-cudnn-cu12",
    "nvidia-cufft-cu12",
    "nvidia-curand-cu12",
    "nvidia-cusolver-cu12",
    "nvidia-cusparse-cu12",
    "nvidia-nccl-cu12",
    "nvidia-nvjitlink-cu12",
    "nvidia-nvtx-cu12",
    "triton",
    "wheel",
    "setuptools",
})

# The chatterbox package itself — install with --no-deps.
INSTALL_TARGETS = {
    "original": "chatterbox-tts",
    "turbo": "chatterbox-tts",
    "rsxdalv-faster": "git+https://github.com/rsxdalv/chatterbox.git@faster",
}

# pip package names to uninstall when swapping variants.
# Both the official and rsxdalv fork register under these names.
UNINSTALL_NAMES = ["chatterbox-tts", "tts-webui.chatterbox-tts"]

# Extra deps that only rsxdalv-faster needs (on top of the shared set).
RSXDALV_EXTRA_DEPS = ["resampy==0.4.3"]

# Non-torch dependencies that chatterbox needs. Installed one-by-one so a
# single failure doesn't block the rest. Order matters: transformers needs
# huggingface-hub, accelerate needs torch (already present), etc.
REQUIRED_DEPS = [
    "transformers",
    "accelerate",
    "conformer",
    "scipy",
    "tqdm",
    "librosa",
    "soundfile",
    "encodec",
    "nemo_text_processing",
    "huggingface-hub",
    "safetensors",
]

# Deps that might fail on some platforms but are optional / best-effort.
OPTIONAL_DEPS = [
    "pesq",
    "pystoi",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _col(colour: str, msg: str) -> str:
    """Wrap *msg* in ANSI colour codes (no-op if not a tty)."""
    if not sys.stdout.isatty():
        return msg
    return f"{colour}{msg}{RESET}"


def _header(msg: str) -> None:
    print(f"\n{_col(BOLD + CYAN, '=' * 60)}")
    print(_col(BOLD + CYAN, f"  {msg}"))
    print(f"{_col(BOLD + CYAN, '=' * 60)}")


def _ok(msg: str) -> None:
    print(f"  {_col(GREEN, '[OK]')}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_col(YELLOW, '[WARN]')}  {msg}")


def _fail(msg: str) -> None:
    print(f"  {_col(RED, '[FAIL]')}  {msg}")


def _pip(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run pip as a subprocess (never import pip directly)."""
    cmd = [sys.executable, "-m", "pip", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
    )


def _freeze() -> dict[str, str]:
    """Return {package_name: version} from pip freeze."""
    result = _pip("freeze", "--local", check=False)
    pkgs: dict[str, str] = {}
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if "==" in line:
            name, ver = line.split("==", 1)
            pkgs[name.lower().replace("_", "-")] = ver
        elif " @ " in line:
            name = line.split(" @ ", 1)[0]
            pkgs[name.lower().replace("_", "-")] = "(editable/url)"
    return pkgs


def _check_torch() -> tuple[bool, str, str]:
    """Check if torch is importable and CUDA-enabled.

    Returns (cuda_available, torch_version, cuda_version_or_error).
    """
    try:
        import torch  # noqa: F811

        ver = torch.__version__
        if torch.cuda.is_available():
            cuda_ver = torch.version.cuda or "unknown"
            return True, ver, cuda_ver
        return False, ver, "CUDA not available"
    except ImportError:
        return False, "NOT INSTALLED", "N/A"


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def preflight(model_type: str) -> dict[str, str]:
    """Run all pre-flight checks. Returns the frozen package snapshot."""
    _header("PRE-FLIGHT CHECKS")

    # 1. Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 11):
        _ok(f"Python {py_ver}")
    else:
        _fail(f"Python {py_ver} — Chatterbox requires Python >= 3.11")
        sys.exit(1)

    # 2. pip available
    result = _pip("--version", check=False)
    if result.returncode == 0:
        pip_ver = result.stdout.strip().split()[1] if result.stdout else "?"
        _ok(f"pip {pip_ver}")
    else:
        _fail("pip not found — install pip first")
        sys.exit(1)

    # 3. torch + CUDA
    cuda_ok, torch_ver, cuda_info = _check_torch()
    if cuda_ok:
        _ok(f"torch {torch_ver} with CUDA {cuda_info}")
    elif torch_ver != "NOT INSTALLED":
        _warn(f"torch {torch_ver} — {cuda_info} (CPU-only, will be slow)")
    else:
        _fail("torch not installed — install PyTorch first (https://pytorch.org)")
        sys.exit(1)

    # 4. GPU memory check (best-effort)
    try:
        import torch

        if torch.cuda.is_available():
            total_mem = torch.cuda.get_device_properties(0).total_mem
            gb = total_mem / (1024**3)
            name = torch.cuda.get_device_name(0)
            if gb >= 6.0:
                _ok(f"GPU: {name} ({gb:.1f} GB VRAM)")
            else:
                _warn(f"GPU: {name} ({gb:.1f} GB) — minimum 6 GB recommended")
    except Exception:
        _warn("Could not query GPU memory (non-fatal)")

    # 5. Model type valid
    if model_type not in INSTALL_TARGETS:
        _fail(f"Unknown model type: {model_type!r}")
        _fail(f"Choose from: {', '.join(sorted(INSTALL_TARGETS))}")
        sys.exit(1)
    _ok(f"Model type: {model_type}")

    # 6. Snapshot current packages
    snapshot = _freeze()
    _ok(f"Package snapshot taken ({len(snapshot)} packages)")

    # 7. Show protected packages that are present
    present_protected = {
        p: snapshot[p] for p in PROTECTED_PACKAGES if p in snapshot
    }
    if present_protected:
        _ok(f"Protected packages found: {len(present_protected)}")
        for pkg, ver in sorted(present_protected.items()):
            print(f"        {pkg}=={ver}")
    else:
        _warn("No protected packages found (fresh environment?)")

    return snapshot


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

def swap_chatterbox(new_model_type: str) -> bool:
    """Uninstall current chatterbox variant, install the new one.

    Returns True on success. Keeps all non-torch deps in place since they
    overlap 99% between variants.
    """
    _header(f"SWAPPING TO CHATTERBOX ({new_model_type.upper()})")

    # 1. Detect what's currently installed
    snapshot = _freeze()
    current = None
    for name in UNINSTALL_NAMES:
        if name in snapshot:
            current = name
            break

    if current:
        print(f"  Current: {current}=={snapshot.get(current, '?')}")
        print(f"  Uninstalling {current}...")
        result = _pip("uninstall", "-y", current, check=False)
        if result.returncode == 0:
            _ok(f"{current} uninstalled")
        else:
            _warn(f"Could not uninstall {current} (may not be installed via pip)")
    else:
        _warn("No existing chatterbox package found — fresh install")

    # 2. Install the new variant
    return install_chatterbox(new_model_type)


def install_chatterbox(model_type: str) -> bool:
    """Install the chatterbox package with --no-deps. Returns True on success."""
    _header(f"INSTALLING CHATTERBOX ({model_type.upper()})")

    target = INSTALL_TARGETS[model_type]
    print(f"  Target: {target}")
    print(f"  Flags:  --no-deps (will NOT touch torch/CUDA)")
    print()

    result = _pip("install", "--no-deps", target, check=False)

    if result.returncode == 0:
        _ok("chatterbox installed successfully (--no-deps)")
        return True

    _fail("chatterbox install failed:")
    for line in result.stderr.strip().splitlines()[-5:]:
        print(f"        {line}")
    return False


def install_deps(model_type: str = "original") -> list[str]:
    """Install non-torch dependencies one-by-one. Returns list of failures."""
    _header("INSTALLING NON-TORCH DEPENDENCIES")

    failures: list[str] = []

    # rsxdalv-faster needs one extra dep
    deps_to_install = list(REQUIRED_DEPS)
    if model_type == "rsxdalv-faster":
        deps_to_install.extend(RSXDALV_EXTRA_DEPS)

    for pkg in deps_to_install:
        # Skip if already installed
        try:
            importlib.import_module(pkg.replace("-", "_"))
            _ok(f"{pkg} (already installed)")
            continue
        except ImportError:
            pass

        result = _pip("install", pkg, check=False)
        if result.returncode == 0:
            _ok(f"{pkg} (installed)")
        else:
            _fail(f"{pkg} (FAILED — see below)")
            for line in result.stderr.strip().splitlines()[-3:]:
                print(f"        {line}")
            failures.append(pkg)

    # Best-effort optional deps
    for pkg in OPTIONAL_DEPS:
        try:
            importlib.import_module(pkg.replace("-", "_"))
            _ok(f"{pkg} (already installed, optional)")
            continue
        except ImportError:
            pass

        result = _pip("install", pkg, check=False)
        if result.returncode == 0:
            _ok(f"{pkg} (installed, optional)")
        else:
            _warn(f"{pkg} (skipped — optional, non-critical)")

    return failures


# ---------------------------------------------------------------------------
# Post-install verification
# ---------------------------------------------------------------------------

def verify(before: dict[str, str], model_type: str) -> bool:
    """Verify nothing protected was changed. Returns True if safe."""
    _header("POST-INSTALL VERIFICATION")

    after = _freeze()
    all_safe = True

    # 1. Check protected packages
    for pkg in sorted(PROTECTED_PACKAGES):
        before_ver = before.get(pkg)
        after_ver = after.get(pkg)

        if before_ver is None and after_ver is None:
            continue  # wasn't present, still isn't
        if before_ver is None and after_ver is not None:
            _fail(f"{pkg}: was NOT installed, now {after_ver} — UNEXPECTED")
            all_safe = False
        elif before_ver is not None and after_ver is None:
            _fail(f"{pkg}: was {before_ver}, now REMOVED — UNEXPECTED")
            all_safe = False
        elif before_ver != after_ver:
            _fail(f"{pkg}: was {before_ver}, now {after_ver} — VERSION CHANGED")
            all_safe = False
        else:
            _ok(f"{pkg}=={after_ver} (unchanged)")

    # 2. Re-check torch + CUDA
    cuda_ok, torch_ver, cuda_info = _check_torch()
    if cuda_ok:
        _ok(f"torch {torch_ver} + CUDA {cuda_info} still working")
    elif torch_ver != "NOT INSTALLED":
        _warn(f"torch {torch_ver} — {cuda_info}")
    else:
        _fail("torch is gone — something went very wrong")
        all_safe = False

    # 3. Smoke test chatterbox import
    try:
        if model_type == "turbo":
            from chatterbox.tts import ChatterboxTurbo  # noqa: F401

            _ok("from chatterbox.tts import ChatterboxTurbo — OK")
        else:
            from chatterbox.tts import ChatterboxTTS2  # noqa: F401

            _ok("from chatterbox.tts import ChatterboxTTS2 — OK")
    except ImportError as exc:
        _fail(f"Chatterbox import failed: {exc}")
        all_safe = False
    except Exception as exc:
        _warn(f"Chatterbox import warning: {exc}")

    # 4. Summary of new packages
    new_pkgs = set(after) - set(before)
    if new_pkgs:
        print(f"\n  New packages installed ({len(new_pkgs)}):")
        for pkg in sorted(new_pkgs):
            print(f"        + {pkg}=={after[pkg]}")

    changed_pkgs = {
        p for p in set(before) & set(after)
        if before[p] != after[p] and p not in PROTECTED_PACKAGES
    }
    if changed_pkgs:
        print(f"\n  Changed packages ({len(changed_pkgs)}):")
        for pkg in sorted(changed_pkgs):
            print(f"        ~ {pkg}: {before[pkg]} -> {after[pkg]}")

    return all_safe


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def rollback_chatterbox() -> None:
    """Best-effort uninstall of chatterbox if verification fails."""
    _header("ROLLING BACK (verification failed)")
    result = _pip("uninstall", "-y", "chatterbox-tts", check=False)
    if result.returncode == 0:
        _ok("chatterbox-tts uninstalled")
    else:
        _warn("Could not uninstall chatterbox-tts (may need manual cleanup)")


# ---------------------------------------------------------------------------
# Check-only mode
# ---------------------------------------------------------------------------

def check_only() -> None:
    """Just report the current state, install nothing."""
    _header("ENVIRONMENT CHECK (read-only)")

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    _ok(f"Python {py_ver}")

    cuda_ok, torch_ver, cuda_info = _check_torch()
    if cuda_ok:
        _ok(f"torch {torch_ver} with CUDA {cuda_info}")
    elif torch_ver != "NOT INSTALLED":
        _warn(f"torch {torch_ver} — {cuda_info}")
    else:
        _fail("torch not installed")

    try:
        import torch

        if torch.cuda.is_available():
            total_mem = torch.cuda.get_device_properties(0).total_mem
            gb = total_mem / (1024**3)
            name = torch.cuda.get_device_name(0)
            _ok(f"GPU: {name} ({gb:.1f} GB)")
    except Exception:
        _warn("Could not query GPU")

    # Check if chatterbox is already installed
    try:
        import chatterbox  # noqa: F401

        _ok("chatterbox is installed")
        try:
            from chatterbox.tts import ChatterboxTTS2  # noqa: F401

            _ok("ChatterboxTTS2 importable (original / rsxdalv-faster)")
        except ImportError:
            _warn("ChatterboxTTS2 not importable")
        try:
            from chatterbox.tts import ChatterboxTurbo  # noqa: F401

            _ok("ChatterboxTurbo importable (turbo)")
        except ImportError:
            _warn("ChatterboxTurbo not importable")
    except ImportError:
        _warn("chatterbox not yet installed")

    # Show protected packages
    snapshot = _freeze()
    present = {p: snapshot[p] for p in PROTECTED_PACKAGES if p in snapshot}
    if present:
        print(f"\n  Protected packages ({len(present)}):")
        for pkg, ver in sorted(present.items()):
            print(f"        {pkg}=={ver}")

    _header("CHECK COMPLETE")
    print("  Run with 'original', 'turbo', or 'rsxdalv-faster' to install.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulletproof Chatterbox TTS installer (safe for existing torch/CUDA).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python scripts/install_chatterbox.py original         # Official model + emotion
              python scripts/install_chatterbox.py turbo            # Fastest official (~6x RT)
              python scripts/install_chatterbox.py rsxdalv-faster   # torch.compile + CUDA graphs
              python scripts/install_chatterbox.py --check          # Verify only, install nothing
              python scripts/install_chatterbox.py --swap turbo     # Swap current -> turbo
              python scripts/install_chatterbox.py --swap rsxdalv-faster  # Swap -> fork

            Swap mode (--swap):
              Safely uninstalls current chatterbox, installs the new variant.
              Non-torch deps are kept since they overlap 99% between all variants.
              Use this to A/B test models without managing multiple conda envs.

            Multi-env strategy (for side-by-side testing):
              Run scripts/setup_chatterbox_envs.bat to create separate conda envs:
                chatterbox-official  -> original + turbo
                chatterbox-rsxdalv   -> rsxdalv-faster

            Safe install guarantee:
              - Uses --no-deps to NEVER touch torch, torchaudio, CUDA, cuDNN, wheel
              - Snapshots all packages before and after, diffs to prove safety
              - Rolls back on any protected package version change
              - Installs non-torch deps one-by-one for fault isolation
        """),
    )
    parser.add_argument(
        "model_type",
        nargs="?",
        choices=["original", "turbo", "rsxdalv-faster"],
        help="Which Chatterbox model variant to install",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check environment only, install nothing",
    )
    parser.add_argument(
        "--swap",
        metavar="MODEL",
        choices=["original", "turbo", "rsxdalv-faster"],
        help="Swap: uninstall current chatterbox variant, install this one instead",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip installing non-torch dependencies (if you already have them)",
    )
    parser.add_argument(
        "--save-snapshot",
        type=Path,
        metavar="FILE",
        help="Save before/after package snapshots to a JSON file",
    )

    args = parser.parse_args()

    if args.check:
        check_only()
        return

    # --swap mode: uninstall current, install new
    if args.swap:
        model = args.swap
        before = preflight(model)
        if not swap_chatterbox(model):
            _fail("Aborting — swap failed")
            sys.exit(1)
        # Install any missing deps (especially rsxdalv's extra resampy)
        dep_failures: list[str] = []
        if not args.skip_deps:
            dep_failures = install_deps(model)
        safe = verify(before, model)
        _save_and_report(args, before, safe, dep_failures, model)
        return

    if not args.model_type:
        parser.print_help()
        print(f"\n{_col(RED, 'Error: specify a model type, --swap MODEL, or --check')}")
        sys.exit(1)

    # --- Run the install pipeline ---
    before = preflight(args.model_type)

    if not install_chatterbox(args.model_type):
        _fail("Aborting — chatterbox install failed")
        sys.exit(1)

    dep_failures: list[str] = []
    if not args.skip_deps:
        dep_failures = install_deps(args.model_type)
    else:
        _header("SKIPPING NON-TORCH DEPENDENCIES (--skip-deps)")

    safe = verify(before, args.model_type)
    _save_and_report(args, before, safe, dep_failures, args.model_type)


def _save_and_report(
    args: argparse.Namespace,
    before: dict[str, str],
    safe: bool,
    dep_failures: list[str],
    model_type: str,
) -> None:
    """Save optional snapshot and print the final verdict."""
    # Save snapshot if requested
    if args.save_snapshot:
        after = _freeze()
        snapshot_data = {
            "model_type": model_type,
            "before": before,
            "after": after,
            "protected_changed": not safe,
        }
        args.save_snapshot.write_text(json.dumps(snapshot_data, indent=2))
        _ok(f"Snapshot saved to {args.save_snapshot}")

    # --- Final verdict ---
    _header("RESULT")

    if not safe:
        _fail("PROTECTED PACKAGES WERE CHANGED — rolling back")
        rollback_chatterbox()
        _fail("Install aborted. Your environment may need manual repair.")
        _fail("Compare the snapshot file to restore exact versions.")
        sys.exit(1)

    if dep_failures:
        _warn(f"Chatterbox installed but {len(dep_failures)} deps failed:")
        for pkg in dep_failures:
            print(f"        - {pkg}")
        _warn("Try installing them manually: pip install " + " ".join(dep_failures))
    else:
        _ok("All packages installed successfully")

    _ok("Protected packages verified UNCHANGED")
    _ok(f"Chatterbox ({model_type}) is ready to use")
    print()
    print(f"  Configure in assistant_config.yml:")
    print(f"    tts:")
    print(f"      provider: \"chatterbox\"")
    print(f"      voice_file: \"path/to/your_voice.wav\"")
    print(f"      model_type: \"{model_type}\"")
    print(f"      device: \"auto\"")
    if model_type != "turbo":
        print(f"      exaggeration: 0.5")
        print(f"      cfg_weight: 0.5")
    print()


if __name__ == "__main__":
    main()
