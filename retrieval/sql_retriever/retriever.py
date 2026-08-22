from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from . import templates


def _format_claim(row: dict) -> str:
    return (
        f"Claim {row['claim_id']} on {row['service_date']}: {row['diagnosis_desc']} "
        f"({row['procedure_desc']}), billed ${row['paid_amount']:.2f}, "
        f"provider {row['provider_name']} ({row['provider_specialty']})."
    )


def _format_medication(row: dict) -> str:
    end = f" through {row['end_date']}" if row.get("end_date") else ""
    return f"Medication {row['medication_name']}, status {row['status']}, started {row['start_date']}{end}."


def _format_encounter(row: dict) -> str:
    return f"{row['encounter_type']} encounter on {row['encounter_date']} ({row['reason']})."


def _format_sdoh(row: dict) -> str:
    return (
        f"Housing: {row['housing_status']}. Food security: {row['food_security']}. "
        f"Transportation: {row['transportation_access']}. Income: {row['income_bracket']}."
    )


def _format_summary(row: dict) -> str:
    return (
        f"Member {row['member_id']}, age {row['age']}, {row['plan_type']} plan, "
        f"cohorts: {row['cohorts'] or 'none'}. {row['total_claims']} claims "
        f"(${row['total_paid_amount']:.2f} total), {row['total_encounters']} encounters, "
        f"{row['active_medication_count']} active medications. "
        f"Active conditions: {row['active_conditions'] or 'none recorded'}."
    )


_FORMATTERS = {
    "claims_history": _format_claim,
    "medication_list": _format_medication,
    "recent_encounters": _format_encounter,
    "sdoh_profile": _format_sdoh,
    "member_summary": _format_summary,
}


class SQLMemberRetriever(BaseRetriever):
    member_id: str
    k: int = 5

    def _get_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        intent = templates.classify_intent(query)
        formatter = _FORMATTERS[intent]

        if intent == "claims_history":
            rows = templates.claims_history(self.member_id, limit=self.k)
        elif intent == "recent_encounters":
            rows = templates.recent_encounters(self.member_id, limit=self.k)
        elif intent == "medication_list":
            rows = templates.medication_list(self.member_id)
        else:
            row = templates.sdoh_profile(self.member_id) if intent == "sdoh_profile" else templates.member_summary(self.member_id)
            rows = [row] if row else []

        return [
            Document(page_content=formatter(row), metadata={**row, "intent": intent, "source": "sql", "member_id": self.member_id})
            for row in rows
        ]
