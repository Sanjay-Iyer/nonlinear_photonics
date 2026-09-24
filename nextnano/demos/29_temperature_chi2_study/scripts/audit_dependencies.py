"""Check Demo 29 Python imports and path literals for numbered-demo dependencies."""
import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(r"(?:demo[_\\/]*2[0-8]|demos[/\\]2[0-8]|Demo2[0-8])", re.I)
LOCAL_REFERENCE_FIXTURES = {"validation/historical_demo28_mixed_300K.csv"}


def check() -> list[str]:
    problems = []
    for path in list((ROOT / "chi2").glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                names = [node.value]
            else:
                continue
            for name in names:
                # A copied CSV inside Demo 29 is a local comparison fixture,
                # not a runtime dependency on the Demo 28 directory.
                if name in LOCAL_REFERENCE_FIXTURES:
                    continue
                if FORBIDDEN.search(name):
                    problems.append(f"{path.name}:{node.lineno}: {name[:100]}")
    return problems


if __name__ == "__main__":
    errors = check()
    print("FAIL: " + "; ".join(errors) if errors else "PASS: Demo 29 has no numbered-demo import/path dependency")
    raise SystemExit(2 if errors else 0)
