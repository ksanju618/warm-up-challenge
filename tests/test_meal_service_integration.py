"""
Integration test that makes a REAL call to the Gemini API.

Run explicitly before submission with a valid GEMINI_API_KEY set:
    pytest tests/test_meal_service_integration.py -v -m integration

Skipped automatically in environments without a key (e.g. CI without secrets)
so the rest of the test suite still runs green.
"""

import os
import pytest

from core.schema import UserInput
from core.meal_service import generate_full_plan

pytestmark = pytest.mark.integration

requires_api_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping live Gemini integration test",
)


@requires_api_key
def test_generate_full_plan_end_to_end():
    user_input = UserInput(
        budget_limit=300,
        currency="INR",
        dietary_preference="Vegetarian",
        allergies_or_dislikes=["peanuts"],
        cuisine_preference="Indian",
        day_type="Normal day",
        pantry_items=["rice", "salt"],
    )

    result = generate_full_plan(user_input)

    # Structural assertions -- proves the LLM output validated against schema
    assert result.llm_response.meal_plan.breakfast.name
    assert result.llm_response.meal_plan.lunch.name
    assert result.llm_response.meal_plan.dinner.name
    assert len(result.llm_response.grocery_list) > 0
    assert len(result.llm_response.substitutions) >= 1

    # Allergy constraint should be respected in the actual generated content
    grocery_names = " ".join(item.name.lower() for item in result.llm_response.grocery_list)
    assert "peanut" not in grocery_names

    # Budget math should be internally consistent
    assert result.budget.budget_limit == 300
    assert isinstance(result.budget.is_within_budget, bool)
