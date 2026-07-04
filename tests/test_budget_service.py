from core.schema import GroceryItem, Substitution
from core.budget_service import compute_budget_feasibility


def _item(name, price, pantry=False):
    return GroceryItem(
        name=name, quantity="1 unit", category="Other",
        estimated_unit_price=price, used_in=["dinner"], already_in_pantry=pantry,
    )


def test_within_budget():
    groceries = [_item("Rice", 50), _item("Dal", 40)]
    result = compute_budget_feasibility(groceries, budget_limit=200, currency="INR", substitutions=[])
    assert result.is_within_budget is True
    assert result.total_estimated_cost == 90
    assert result.difference == 110
    assert result.cost_saving_tips == []


def test_over_budget_generates_tips():
    groceries = [_item("Paneer", 150), _item("Cashews", 200)]
    subs = [Substitution(original_item="Paneer", substitute_options=["Tofu"], reason="Cheaper protein")]
    result = compute_budget_feasibility(groceries, budget_limit=100, currency="INR", substitutions=subs)
    assert result.is_within_budget is False
    assert result.total_estimated_cost == 350
    assert result.difference == -250
    assert len(result.cost_saving_tips) == 1
    assert "Paneer" in result.cost_saving_tips[0]


def test_pantry_items_excluded_from_cost():
    groceries = [_item("Rice", 50), _item("Salt", 10, pantry=True)]
    result = compute_budget_feasibility(groceries, budget_limit=100, currency="INR", substitutions=[])
    # Salt is already in pantry, so only Rice's 50 should count
    assert result.total_estimated_cost == 50


def test_exact_budget_match_counts_as_within_budget():
    groceries = [_item("Rice", 100)]
    result = compute_budget_feasibility(groceries, budget_limit=100, currency="INR", substitutions=[])
    assert result.is_within_budget is True
