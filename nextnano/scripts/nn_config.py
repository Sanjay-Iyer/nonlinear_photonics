"""Load per-machine nextnano++ paths into nextnanopy's config.

Split-machine workflow: input decks and analysis code are authored on a
laptop with no license, pushed to git, then pulled and executed on a laptop
that has nextnano Standard installed. The only per-machine difference is
where the executable, database, license, and output directory live -- that
lives in config/paths.local.yaml, which is gitignored and hand-authored on
each machine from paths.local.yaml.example.

Call load_config() once before constructing any nextnanopy InputFile.
"""

from pathlib import Path

import yaml

# config/paths.local.yaml resolved relative to THIS file, never the cwd, so
# scripts work no matter where they are launched from.
_SCRIPT_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = _SCRIPT_DIR.parent / "config" / "paths.local.yaml"
_EXAMPLE_PATH = _SCRIPT_DIR.parent / "config" / "paths.local.yaml.example"

# YAML keys under the "nextnano++" section -> nextnanopy config keys. These
# happen to be identical, but the mapping is explicit so a rename in the YAML
# schema does not silently push a bad key into nextnanopy.
_KEY_MAP = {
    "exe": "exe",
    "database": "database",
    "license": "license",
    "outputdirectory": "outputdirectory",
}


def load_config(config_path: Path | None = None):
    """Read paths.local.yaml and apply it to nextnanopy's global config.

    Parameters
    ----------
    config_path:
        Optional override for the YAML location. Defaults to
        ``<repo>/nextnano/config/paths.local.yaml``.

    Returns
    -------
    dict
        The resolved ``{nextnanopy_key: value}`` mapping that was applied.

    Raises
    ------
    FileNotFoundError
        If the config file is missing, with instructions to create it.
    KeyError / ValueError
        If the file is malformed or missing the ``nextnano++`` section.
    """
    cfg_path = Path(config_path) if config_path is not None else _CONFIG_PATH

    if not cfg_path.is_file():
        raise FileNotFoundError(
            "nextnano config not found:\n"
            f"    {cfg_path}\n\n"
            "This file is machine-specific and gitignored, so it does not\n"
            "arrive with a git pull. Create it once on this machine:\n\n"
            f"    copy \"{_EXAMPLE_PATH}\" \"{cfg_path}\"\n\n"
            "then open it and fill in the real exe / database / license /\n"
            "outputdirectory paths for THIS machine."
        )

    with cfg_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    section = data.get("nextnano++")
    if not isinstance(section, dict):
        raise ValueError(
            f"{cfg_path} must contain a top-level 'nextnano++:' mapping. "
            f"See {_EXAMPLE_PATH} for the expected shape."
        )

    # Import here so the missing-file error above is reportable even on a
    # machine where nextnanopy is not installed (e.g. the home laptop).
    import nextnanopy as nn

    applied = {}
    for yaml_key, nn_key in _KEY_MAP.items():
        value = section.get(yaml_key)
        if value in (None, ""):
            # Skip unset keys; let nextnanopy fall back to its own defaults
            # rather than pushing an empty string that masks them.
            continue
        value = str(value)
        nn.config.set("nextnano++", nn_key, value)
        applied[nn_key] = value

    # These three are load-bearing for this workflow: without exe/database the
    # solver can't run, and without outputdirectory results silently land next
    # to the deck instead of in output/ (breaking the README contract and the
    # runlog convention). License is intentionally not required here -- a
    # portable Standard install may resolve it by default location.
    required = ("exe", "database", "outputdirectory")
    missing = [k for k in required if k not in applied]
    if missing:
        raise ValueError(
            f"{cfg_path} is missing required key(s): {', '.join(missing)}.\n"
            "Uncomment and fill them in under the 'nextnano++:' section "
            f"(see {_EXAMPLE_PATH}). 'outputdirectory' is required so results "
            "land in nextnano/output/ as the workflow expects."
        )

    # Persist so subsequent nextnanopy calls in this and future processes see
    # the values (nextnanopy caches config in the user's home config file).
    nn.config.save()

    return applied


if __name__ == "__main__":
    resolved = load_config()
    print(f"nextnano++ config applied from {_CONFIG_PATH}:")
    for k, v in resolved.items():
        print(f"  {k:16s} = {v}")
