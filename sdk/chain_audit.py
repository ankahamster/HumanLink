"""
Helpers for optionally anchoring HumanLink audit summaries on-chain.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple


def anchor_assertion_summary(
    assertion: Dict[str, Any],
    contracts_dir: Path,
    network: str = "sepolia",
) -> Tuple[bool, str]:
    """
    Anchor an assertion audit summary using the Hardhat workspace in contracts/.

    Args:
        assertion: Complete HumanPresenceAssertion dictionary.
        contracts_dir: Path to the Hardhat project root.
        network: Hardhat network name.

    Returns:
        A tuple of (success, message).
    """
    if not assertion:
        return False, "Missing assertion payload"

    if not contracts_dir.exists():
        return False, f"Contracts directory not found: {contracts_dir}"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            encoding="utf-8",
            delete=False,
        ) as temp_file:
            json.dump(assertion, temp_file, ensure_ascii=False, indent=2)
            temp_path = temp_file.name

        env = os.environ.copy()
        env["ASSERTION_JSON_FILE"] = temp_path

        result = subprocess.run(
            ["npm", "run", f"anchor:{network}"],
            cwd=str(contracts_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )

        if result.returncode == 0:
            output = (result.stdout or "").strip()
            return True, output or "Audit summary anchored successfully"

        error_output = "\n".join(
            part.strip() for part in [result.stdout or "", result.stderr or ""] if part.strip()
        )
        return False, error_output or "Hardhat anchor command failed"

    except subprocess.TimeoutExpired:
        return False, "Hardhat anchor command timed out"
    except Exception as exc:
        return False, str(exc)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
