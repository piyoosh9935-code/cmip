import random
from datetime import datetime, timezone

from . import config


def rng_for(*parts: object) -> random.Random:
    """Deterministic per-entity RNG: same parts always produce the same draws,
    regardless of which batch or in what order entities are generated in."""
    return random.Random(f"{config.SEED}:" + ":".join(str(p) for p in parts))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def member_id(index: int) -> str:
    return f"M-{index:05d}"


def provider_id(index: int) -> str:
    return f"P-{index:04d}"
