"""
All budget arithmetic lives here, in plain deterministic Python -- never
delegated to the LLM. This is both a hallucination guard (models are
unreliable at arithmetic) and makes the logic trivially unit-testable.
"""

from __future__ import annotations

from typing import List

from core.schema import GroceryItem, Substitution, BudgetFeasibility


def compute_budget_feasibility(
    grocery_list: List[GroceryItem],
    budget_limit: float,
    currency: str,
    substitutions: List[Substitution],
) -> BudgetFeasibility:
    # Items already in the user's pantry cost nothing extra.
    total_cost = sum(
        item.estimated_unit_price for item in grocery_list if not item.already_in_pantry
    )
    total_cost = round(total_cost, 2)
    difference = round(budget_limit - total_cost, 2)
    is_within_budget = total_cost <= budget_limit

    if is_within_budget:
        message = (
            f"You're within budget with {abs(difference)} {currency} to spare."
        )
        tips: List[str] = []
    else:
        message = (
            f"This plan is {abs(difference)} {currency} over your budget of "
            f"{budget_limit} {currency}."
        )
        tips = _build_cost_saving_tips(substitutions, over_budget=True)

    return BudgetFeasibility(
        total_estimated_cost=total_cost,
        budget_limit=budget_limit,
        currency=currency,
        is_within_budget=is_within_budget,
        difference=difference,
        message=message,
        cost_saving_tips=tips,
    )


def _build_cost_saving_tips(substitutions: List[Substitution], over_budget: bool) -> List[str]:
    if not over_budget or not substitutions:
        return []
    tips = []
    for sub in substitutions:
        if sub.substitute_options:
            tips.append(
                f"Swap '{sub.original_item}' for '{sub.substitute_options[0]}' -- {sub.reason}"
            )
    return tips[:3]  # keep it actionable, not overwhelming
