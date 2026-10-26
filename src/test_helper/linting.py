import subprocess
import sys


def pylint(self, target_file: str, rcfile_path: str = ".pylintrc"):

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pylint",
            f"--rcfile={rcfile_path}",
            target_file,
        ],
        capture_output=True,
        text=True,
    )

    return result.returncode, result.stdout