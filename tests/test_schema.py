import pytest
from pydantic import ValidationError

from core.schema import (
    UserInput,
    Meal,
    MealPlan,
    GroceryItem,
    Substitution,
    MealPlanLLMResponse,
)


def test_user_input_rejects_non_positive_budget():
    with pytest.raises(ValidationError):
        UserInput(
            budget_limit=0,
            dietary_preference="Vegetarian",
            day_type="Normal day",
        )


def test_user_input_defaults():
    ui = UserInput(
        budget_limit=250,
        dietary_preference="Vegan",
        day_type="Busy day - quick meals only",
    )
    assert ui.currency == "INR"
    assert ui.allergies_or_dislikes == []
    assert ui.pantry_items == []


def test_grocery_item_rejects_negative_price():
    with pytest.raises(ValidationError):
        GroceryItem(
            name="Rice",
            quantity="1 kg",
            category="Grains",
            estimated_unit_price=-5,
            used_in=["dinner"],
        )


def test_meal_plan_llm_response_full_shape():
    meal = Meal(name="Poha", description="Light flattened rice breakfast", prep_time_minutes=15)
    plan = MealPlan(breakfast=meal, lunch=meal, dinner=meal)
    item = GroceryItem(
        name="Poha (flattened rice)", quantity="200 g", category="Grains",
        estimated_unit_price=25.0, used_in=["breakfast"],
    )
    sub = Substitution(
        original_item="Poha", substitute_options=["Oats", "Semolina"], reason="More easily available"
    )
    response = MealPlanLLMResponse(
        meal_plan=plan, grocery_list=[item], substitutions=[sub], notes="Simple day plan"
    )
    assert response.meal_plan.breakfast.name == "Poha"
    assert response.grocery_list[0].estimated_unit_price == 25.0
