"""
Claim-by-Move Manager for AI Employee.

Provides atomic file claiming to prevent Cloud and Local agents from
processing the same task simultaneously. A claim moves the file into
In_Progress/<agent>/ and a release moves it to the destination folder.

Protocol:
    1. Agent calls try_claim(file, agent) → file moves to In_Progress/<agent>/
    2. Agent processes the file
    3. Agent calls release(file, destination) → file moves to final folder

If the file doesn't exist at claim time (another agent grabbed it first),
try_claim returns None.

Usage:
    from claim_manager import ClaimManager

    cm = ClaimManager(vault_path)
    claimed = cm.try_claim(Path("Needs_Action/email/task.md"), agent="cloud")
    if claimed:
        # process the file at claimed path
        cm.release(claimed, destination="Pending_Approval/email")
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ClaimManager")

DEFAULT_VAULT = Path(__file__).parent.parent / "AI_Employee_Vault"


class ClaimManager:
    """Manages atomic claim-by-move for task files."""

    def __init__(self, vault_path: Path = DEFAULT_VAULT):
        self.vault_path = Path(vault_path)
        self.in_progress = self.vault_path / "In_Progress"
        # Ensure agent directories exist
        (self.in_progress / "cloud").mkdir(parents=True, exist_ok=True)
        (self.in_progress / "local").mkdir(parents=True, exist_ok=True)

    def try_claim(self, filepath: Path, agent: str) -> Path | None:
        """Attempt to claim a file by moving it to In_Progress/<agent>/.

        Args:
            filepath: Absolute or vault-relative path to the file to claim.
            agent: "cloud" or "local"

        Returns:
            Path to the claimed file in In_Progress/<agent>/, or None if claim failed.
        """
        if agent not in ("cloud", "local"):
            raise ValueError(f"Invalid agent: {agent}. Must be 'cloud' or 'local'.")

        # Resolve to absolute path
        if not filepath.is_absolute():
            filepath = self.vault_path / filepath

        if not filepath.exists():
            logger.warning(f"Claim failed (file gone): {filepath.name}")
            return None

        dest_dir = self.in_progress / agent
        dest = dest_dir / filepath.name

        try:
            filepath.rename(dest)
            logger.info(f"Claimed [{agent}]: {filepath.name} -> In_Progress/{agent}/")
            self._write_claim_metadata(dest, agent, filepath)
            return dest
        except OSError as e:
            logger.warning(f"Claim failed (OS error): {filepath.name} — {e}")
            return None

    def release(self, claimed_path: Path, destination: str) -> Path | None:
        """Release a claimed file by moving it to the destination folder.

        Args:
            claimed_path: Path to the file in In_Progress/<agent>/
            destination: Vault-relative destination folder (e.g. "Pending_Approval/email")

        Returns:
            Path to the file in the destination, or None if release failed.
        """
        if not claimed_path.exists():
            logger.warning(f"Release failed (file gone): {claimed_path.name}")
            return None

        dest_dir = self.vault_path / destination
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / claimed_path.name

        try:
            # Remove claim metadata
            meta_file = claimed_path.with_suffix(claimed_path.suffix + ".claim")
            if meta_file.exists():
                meta_file.unlink()

            claimed_path.rename(dest)
            logger.info(f"Released: {claimed_path.name} -> {destination}/")
            return dest
        except OSError as e:
            logger.error(f"Release failed: {claimed_path.name} — {e}")
            return None

    def list_claims(self, agent: str = None) -> list[Path]:
        """List all currently claimed files, optionally filtered by agent."""
        claims = []
        agents = [agent] if agent else ["cloud", "local"]
        for a in agents:
            agent_dir = self.in_progress / a
            if agent_dir.exists():
                for f in agent_dir.iterdir():
                    if f.is_file() and not f.name.startswith(".") and not f.name.endswith(".claim"):
                        claims.append(f)
        return claims

    def _write_claim_metadata(self, claimed_path: Path, agent: str, original_path: Path):
        """Write a small metadata file alongside the claimed file."""
        meta_file = claimed_path.with_suffix(claimed_path.suffix + ".claim")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        meta_file.write_text(
            f"agent: {agent}\nclaimed_at: {ts}\noriginal: {original_path}\n",
            encoding="utf-8",
        )
