"""
Orchestrates a single end-to-end plan generation:
UserInput -> prompt -> Gemini call -> validated LLM response -> budget math
-> FullPlanResponse.

Kept free of any Streamlit imports so it can be unit/integration tested
in isolation and reused if the frontend ever changes.
"""

from __future__ import annotations

from core.schema import UserInput, FullPlanResponse
from core.prompts import SYSTEM_INSTRUCTION, build_user_prompt
from core.llm_client import generate_structured_plan
from core.budget_service import compute_budget_feasibility


def generate_full_plan(user_input: UserInput) -> FullPlanResponse:
    """Run the full pipeline for one user request. Makes a real Gemini API call."""
    prompt = build_user_prompt(user_input)
    llm_response = generate_structured_plan(SYSTEM_INSTRUCTION, prompt)

    budget = compute_budget_feasibility(
        grocery_list=llm_response.grocery_list,
        budget_limit=user_input.budget_limit,
        currency=user_input.currency,
        substitutions=llm_response.substitutions,
    )

    return FullPlanResponse(llm_response=llm_response, budget=budget)
