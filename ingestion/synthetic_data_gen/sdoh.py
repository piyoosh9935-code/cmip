from .clinical_reference import SDOH_FOOD, SDOH_HOUSING, SDOH_INCOME, SDOH_TRANSPORT
from .common import member_id, now_iso, rng_for


def generate_sdoh_for_member(idx: int, batch_id: int) -> dict:
    rng = rng_for("sdoh", idx)
    return {
        "member_id": member_id(idx),
        "housing_status": rng.choices(SDOH_HOUSING, weights=[70, 12, 12, 6])[0],
        "food_security": rng.choices(SDOH_FOOD, weights=[65, 18, 12, 5])[0],
        "transportation_access": rng.choices(SDOH_TRANSPORT, weights=[75, 18, 7])[0],
        "income_bracket": rng.choices(SDOH_INCOME, weights=[15, 30, 35, 20])[0],
        "batch_id": batch_id,
        "loaded_at": now_iso(),
    }
