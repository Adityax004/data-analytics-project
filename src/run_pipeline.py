from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(script: str) -> None:
    print(f"\n=== Running {script} ===")
    subprocess.run([sys.executable, str(ROOT / "src" / script)], cwd=ROOT, check=True)


def main() -> None:
    run("generate_data.py")
    run("clean_data.py")
    run("build_database.py")
    run("run_sql_analysis.py")
    run("python_analysis.py")
    run("create_notebook.py")
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()

