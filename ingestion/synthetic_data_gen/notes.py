import re
from datetime import datetime, timedelta, timezone

from . import config
from .clinical_reference import COHORTS
from .common import member_id, now_iso, rng_for

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")
_NOTE_TYPES = ["progress note", "consult note", "telehealth note"]

_GENERIC_TEMPLATES = [
    "Annual wellness visit, no acute concerns. Patient reports feeling well overall.",
    "Routine follow-up visit. Vitals stable, no new complaints. Continue current care plan.",
    "Preventive care visit. Discussed age-appropriate screenings and lifestyle counseling.",
]


def _render(rng, cohort: str) -> str:
    spec = COHORTS[cohort]
    template = rng.choice(spec["note_templates"])
    vocab = spec["vocab"]
    chosen = {key: rng.choice(options) for key, options in vocab.items()}
    for placeholder in _PLACEHOLDER_RE.findall(template):
        if placeholder in chosen:
            continue
        if placeholder.endswith("_lower"):
            base = placeholder[: -len("_lower")]
            val = chosen.get(base, "")
            chosen[placeholder] = (val[0].lower() + val[1:]) if val else val
    return template.format(**chosen)


def _volume(rng, cohorts, scale):
    base = sum(rng.randint(*config.NOTES_PER_MEMBER_PER_COHORT) for _ in cohorts) if cohorts \
        else rng.randint(*config.BASELINE_NOTES)
    return max(0, round(base * scale))


def _date(rng, batch_id, past_choices):
    offset = rng.choice(past_choices) if batch_id == 1 else rng.randint(-30, 0)
    return (datetime.now(timezone.utc) + timedelta(days=offset)).date().isoformat()


def generate_notes_for_member(idx, cohorts, provider_ids, batch_id, scale) -> list[dict]:
    rng = rng_for("notes", idx, batch_id)
    n = _volume(rng, cohorts, scale)
    mid = member_id(idx)
    rows = []
    for i in range(n):
        cohort = rng.choice(cohorts) if cohorts else None
        text = _render(rng, cohort) if cohort else rng.choice(_GENERIC_TEMPLATES)
        rows.append(
            {
                "note_id": f"N-{mid}-{batch_id}-{i:04d}",
                "member_id": mid,
                "provider_id": rng.choice(provider_ids),
                "note_type": rng.choices(_NOTE_TYPES, weights=[70, 20, 10])[0],
                "note_date": _date(rng, batch_id, [-700, -450, -250, -100, -40, -15]),
                "note_text": text,
                "cohort_tag": cohort or "general",
                "batch_id": batch_id,
                "loaded_at": now_iso(),
            }
        )
    return rows
