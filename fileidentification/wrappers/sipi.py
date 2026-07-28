import json
import subprocess
from pathlib import Path


def sipi_verify(file: Path) -> tuple[bool, str]:
    """
    Run `sipi verify --json` as a decode guard: can sipi open / decode this file?

    sipi emits a JSON report with a "status" field. Returns (is_corrupt, message):
    status "error" -> (True, error_message); status "ok" -> (False, "").
    If sipi emits no JSON report, fall back to the exit code (non-zero -> corrupt) and surface its output.
    """
    cmd = ["sipi", "verify", "--json", str(file)]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)

    try:
        report = json.loads(res.stdout)
    except json.JSONDecodeError:
        if res.returncode == 0:
            return False, ""
        return True, (res.stderr or res.stdout).strip()

    if report.get("status") == "error":
        return True, str(report.get("error_message", "")).strip()
    return False, ""
