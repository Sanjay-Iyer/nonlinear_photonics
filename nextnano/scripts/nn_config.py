"""Portable, per-machine configuration for the nextnano++ workflow.

Design goals (why this module looks the way it does):

* **Portable.** Every repository resource is located relative to this file
  via ``pathlib``, so the tracked code works no matter where the repo lives
  on disk. The home laptop and the work laptop can keep the repo in totally
  different directories and nothing here changes.

* **Machine-specific values stay local.** The only per-machine data lives in
  ``config/paths.local.yaml``, which is gitignored and hand-authored on each
  machine from ``paths.local.yaml.example``. Nothing machine-specific is
  tracked or hardcoded.

* **The global nextnanopy config is never written.** We resolve paths here
  and hand them to ``InputFile.execute(**kwargs)`` at run time, which
  overrides nextnanopy's per-file config. We deliberately do NOT call
  ``nn.config.set(...)`` on the process-wide singleton or ``nn.config.save()``
  (which would rewrite the user's ``~/.nextnanopy-config``).

This module has NO hard dependency on nextnanopy: config parsing and
validation are importable and testable on a machine with no license and no
solver installed.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

# --- Repository-relative anchors -------------------------------------------
# NEXTNANO_ROOT is the `nextnano/` directory: this file is scripts/nn_config.py,
# so parents[1] is `nextnano/`. Resolved from __file__, never from the cwd, so
# it is correct regardless of where the repo is checked out or where the
# command is launched from.
NEXTNANO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = NEXTNANO_ROOT / "config" / "paths.local.yaml"
EXAMPLE_PATH = NEXTNANO_ROOT / "config" / "paths.local.yaml.example"
INPUT_DIR = NEXTNANO_ROOT / "inputs"
DEFAULT_OUTPUT_DIR = NEXTNANO_ROOT / "output"

SECTION = "nextnano++"
REQUIRED_KEYS = ("exe", "database", "outputdirectory")

# Execution profiles. STANDARD requires a license path; FREE (the nextnano
# Free edition, or a non-execution / authoring workflow) does not.
PROFILE_STANDARD = "standard"
PROFILE_FREE = "free"


class ConfigError(Exception):
    """Raised for any problem loading or validating paths.local.yaml.

    The message is written to be actionable on its own (it tells the user
    exactly what to fix), so callers can print ``str(exc)`` directly.
    """


@dataclass
class NextnanoConfig:
    """Resolved, validated per-machine configuration.

    All paths are expanded (env vars + ``~``) and resolved to absolute paths.
    ``license`` is ``None`` for the Free / non-execution profile.
    """

    exe: Path
    database: Path
    outputdirectory: Path
    license: Path | None
    threads: int
    profile: str
    source_path: Path

    def execute_kwargs(self, outputdirectory: Path | None = None) -> dict:
        """Build the kwargs handed to ``InputFile.execute(**kwargs)``.

        Passing these explicitly is how we keep the global nextnanopy config
        untouched. ``outputdirectory`` may be overridden per input so separate
        decks write to separate directories and never overwrite each other.
        The license is only included when set (Standard profile); it is passed
        as a path and its contents are never read or printed here.
        """
        out = Path(outputdirectory) if outputdirectory is not None else self.outputdirectory
        kwargs = {
            "exe": str(self.exe),
            "database": str(self.database),
            "outputdirectory": str(out),
            "threads": self.threads,
        }
        if self.license is not None:
            kwargs["license"] = str(self.license)
        return kwargs


def _expand(raw: str) -> str:
    """Expand environment variables and a leading ``~`` in a path string."""
    return os.path.expanduser(os.path.expandvars(raw))


def _resolve_path(raw: str) -> Path:
    """Expand and resolve a path string to an absolute Path.

    ``strict=False`` (the default) so a path that does not yet exist on this
    machine still resolves cleanly -- existence is a preflight concern, not a
    parsing concern.
    """
    return Path(_expand(str(raw).strip())).resolve()


def resolve_config(config_path: str | os.PathLike | None = None) -> NextnanoConfig:
    """Load and validate ``paths.local.yaml`` into a :class:`NextnanoConfig`.

    This performs *structural* validation only (keys present, profile/license
    consistent, threads an int). It does NOT check that exe/database/license
    files exist on disk -- that is what ``run_input.py --check-config`` is for,
    so this function stays usable with placeholder or temporary configs.

    Raises
    ------
    ConfigError
        Missing file, missing ``nextnano++`` section, missing required key,
        Standard profile without a license, or an invalid thread count.
    """
    cfg_path = Path(config_path) if config_path is not None else CONFIG_PATH

    if not cfg_path.is_file():
        raise ConfigError(
            f"nextnano local config not found:\n    {cfg_path}\n\n"
            "This file is machine-specific and gitignored, so it does NOT\n"
            "arrive with a git pull. Create it once on this machine by copying\n"
            "the tracked example and filling in real paths:\n\n"
            f'    copy "{EXAMPLE_PATH}" "{cfg_path}"\n\n'
            "then edit it and set exe / database / outputdirectory (and the\n"
            "license path for the Standard edition)."
        )

    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{cfg_path} is not valid YAML: {exc}") from exc

    section = data.get(SECTION)
    if not isinstance(section, dict):
        raise ConfigError(
            f"{cfg_path} must contain a top-level '{SECTION}:' mapping.\n"
            f"See {EXAMPLE_PATH} for the expected shape."
        )

    missing = [k for k in REQUIRED_KEYS if not str(section.get(k, "") or "").strip()]
    if missing:
        raise ConfigError(
            f"{cfg_path} is missing required key(s) under '{SECTION}:': "
            f"{', '.join(missing)}.\n"
            f"See {EXAMPLE_PATH}. 'outputdirectory' is required so results land "
            "in a known location rather than next to the input deck."
        )

    license_raw = str(section.get("license", "") or "").strip()
    profile_raw = str(section.get("profile", "") or "").strip().lower()

    if profile_raw in (PROFILE_STANDARD, PROFILE_FREE):
        profile = profile_raw
    else:
        # No explicit profile: an empty license is the explicit opt-in to the
        # Free / non-execution profile; a non-empty license implies Standard.
        profile = PROFILE_FREE if not license_raw else PROFILE_STANDARD

    if profile == PROFILE_STANDARD and not license_raw:
        raise ConfigError(
            f"{cfg_path}: the Standard execution profile requires a 'license' "
            "path.\nSet 'license:' to your License_nnp.lic, or leave it empty "
            "(or set 'profile: free') to select the Free / non-execution "
            "profile."
        )

    threads_raw = section.get("threads", 0)
    try:
        threads = int(threads_raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            f"{cfg_path}: 'threads' must be an integer, got {threads_raw!r}."
        ) from exc
    if threads < 0:
        raise ConfigError(f"{cfg_path}: 'threads' must be >= 0, got {threads}.")

    return NextnanoConfig(
        exe=_resolve_path(section["exe"]),
        database=_resolve_path(section["database"]),
        outputdirectory=_resolve_path(section["outputdirectory"]),
        license=_resolve_path(license_raw) if license_raw else None,
        threads=threads,
        profile=profile,
        source_path=cfg_path,
    )


# --- Preflight (--check-config) --------------------------------------------


@dataclass
class Check:
    """A single preflight result. ``required=False`` marks informational rows
    that never cause an overall FAIL (e.g. the Python version)."""

    name: str
    ok: bool
    detail: str
    required: bool = True


def preflight(
    config_path: str | os.PathLike | None = None,
    inputs: list[Path] | None = None,
) -> tuple[list[Check], bool]:
    """Run all no-execution preflight checks and return (checks, overall_ok).

    Reports Python + nextnanopy status, the resolved config, existence of the
    exe/database/license, output-directory writability, thread validity, and
    any resolved input files. Performs no solver execution.
    """
    checks: list[Check] = []

    checks.append(Check("Python version", True, sys.version.split()[0], required=False))

    try:
        import nextnanopy as nn

        checks.append(Check("nextnanopy import", True, f"version {nn.__version__}"))
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        checks.append(Check("nextnanopy import", False, f"not importable: {exc}"))

    try:
        cfg = resolve_config(config_path)
    except ConfigError as exc:
        # Without a valid config nothing else can be checked; stop here.
        checks.append(Check("local config", False, str(exc).splitlines()[0]))
        return checks, False

    checks.append(Check("local config path", True, str(cfg.source_path)))
    checks.append(Check("execution profile", True, cfg.profile, required=False))
    checks.append(Check("executable exists", cfg.exe.is_file(), str(cfg.exe)))
    checks.append(Check("database exists", cfg.database.is_file(), str(cfg.database)))

    if cfg.profile == PROFILE_STANDARD:
        # cfg.license is guaranteed non-None for the Standard profile.
        checks.append(Check("license exists", cfg.license.is_file(), str(cfg.license)))
    else:
        checks.append(
            Check("license", True, "not required (free/non-execution profile)", required=False)
        )

    checks.append(Check("threads valid", cfg.threads >= 0, str(cfg.threads)))

    # Output directory exists-or-creatable AND writable.
    out = cfg.outputdirectory
    try:
        out.mkdir(parents=True, exist_ok=True)
        probe = out / ".nn_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks.append(Check("output dir writable", True, str(out)))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("output dir writable", False, f"{out}: {exc}"))

    for path in inputs or []:
        checks.append(Check(f"input: {path.name}", path.is_file(), str(path)))

    overall_ok = all(c.ok for c in checks if c.required)
    return checks, overall_ok


if __name__ == "__main__":
    # Small convenience CLI: print the resolved config (never license contents).
    try:
        resolved = resolve_config()
    except ConfigError as err:
        print(err, file=sys.stderr)
        sys.exit(1)
    print(f"Resolved nextnano++ config from {resolved.source_path}:")
    print(f"  profile         = {resolved.profile}")
    print(f"  exe             = {resolved.exe}")
    print(f"  database        = {resolved.database}")
    print(f"  outputdirectory = {resolved.outputdirectory}")
    print(f"  license         = {'<set>' if resolved.license else '<none / free>'}")
    print(f"  threads         = {resolved.threads}")
