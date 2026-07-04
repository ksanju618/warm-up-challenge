"""
Streamlit frontend for the AI Cooking To-Do List.

Deliberately thin: this file collects form input, validates it into a
UserInput model, calls core.meal_service.generate_full_plan (the ONLY
place a real Gemini API call happens), and renders whatever comes back.
No business logic, no hardcoded meal/grocery data lives here.
"""

import os
import logging

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from core.schema import UserInput
from core.meal_service import generate_full_plan
from core.llm_client import LLMConfigError, LLMGenerationError

load_dotenv()
logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="AI Cooking To-Do List", page_icon="🍳", layout="centered")

st.title("🍳 AI Cooking To-Do List")
st.caption(
    "Tell me about your day and budget, and I'll generate a real meal plan, "
    "grocery list, substitutions, and a budget check -- powered live by Gemini."
)

if not os.environ.get("GEMINI_API_KEY"):
    st.warning(
        "GEMINI_API_KEY is not set. Add it to a `.env` file (see `.env.example`) "
        "before generating a plan.",
        icon="⚠️",
    )

with st.form("plan_form"):
    col1, col2 = st.columns(2)
    with col1:
        budget_limit = st.number_input(
            "Daily grocery budget", min_value=1.0, value=300.0, step=10.0,
            help="How much can you spend on groceries for today's meals?",
        )
        currency = st.selectbox("Currency", ["INR", "USD", "EUR", "GBP"], index=0)
        dietary_preference = st.selectbox(
            "Dietary preference",
            ["No restriction", "Vegetarian", "Vegan", "Eggetarian", "Non-Vegetarian"],
        )
    with col2:
        day_type = st.selectbox(
            "What kind of day is it?",
            ["Busy day - quick meals only", "Normal day", "Free day - can cook elaborate meals"],
        )
        cuisine_preference = st.text_input("Cuisine preference (optional)", placeholder="e.g. Indian, Italian")

    allergies_raw = st.text_input(
        "Allergies or dislikes (comma-separated, optional)", placeholder="e.g. peanuts, mushrooms"
    )
    pantry_raw = st.text_area(
        "Ingredients already at home (comma-separated, optional)",
        placeholder="e.g. rice, onions, eggs",
        help="These will be excluded from your grocery cost.",
    )

    submitted = st.form_submit_button("Generate my plan", use_container_width=True)

if submitted:
    try:
        user_input = UserInput(
            budget_limit=budget_limit,
            currency=currency,
            dietary_preference=dietary_preference,
            allergies_or_dislikes=[a.strip() for a in allergies_raw.split(",") if a.strip()],
            cuisine_preference=cuisine_preference or None,
            day_type=day_type,
            pantry_items=[p.strip() for p in pantry_raw.split(",") if p.strip()],
        )
    except ValidationError as exc:
        st.error(f"Please check your inputs: {exc}")
        st.stop()

    with st.spinner("Calling Gemini and building your plan..."):
        try:
            result = generate_full_plan(user_input)
        except LLMConfigError as exc:
            st.error(str(exc))
            st.stop()
        except LLMGenerationError as exc:
            st.error(f"Couldn't generate a plan right now: {exc}")
            st.stop()

    plan = result.llm_response.meal_plan
    budget = result.budget

    st.success("Here's your plan for today!")

    st.subheader("🍽️ Meal Plan")
    for label, meal in [("Breakfast", plan.breakfast), ("Lunch", plan.lunch), ("Dinner", plan.dinner)]:
        with st.expander(f"**{label}: {meal.name}**", expanded=True):
            st.write(meal.description)
            cals = f" · ~{meal.calories_estimate} kcal" if meal.calories_estimate else ""
            st.caption(f"⏱️ ~{meal.prep_time_minutes} min{cals}")

    st.subheader("🛒 Grocery List")
    grocery_rows = [
        {
            "Item": item.name,
            "Quantity": item.quantity,
            "Category": item.category,
            "Est. Price": "Already have it" if item.already_in_pantry else f"{item.estimated_unit_price:.2f} {currency}",
            "Used In": ", ".join(item.used_in),
        }
        for item in result.llm_response.grocery_list
    ]
    st.dataframe(grocery_rows, use_container_width=True, hide_index=True)

    st.subheader("🔄 Substitutions")
    for sub in result.llm_response.substitutions:
        st.markdown(f"- **{sub.original_item}** → {', '.join(sub.substitute_options)}  \n  _{sub.reason}_")

    st.subheader("💰 Budget Feasibility")
    if budget.is_within_budget:
        st.success(f"{budget.message} (Total: {budget.total_estimated_cost:.2f} {currency})")
    else:
        st.error(f"{budget.message} (Total: {budget.total_estimated_cost:.2f} {currency})")
        if budget.cost_saving_tips:
            st.markdown("**Ways to cut cost:**")
            for tip in budget.cost_saving_tips:
                st.markdown(f"- {tip}")

    if result.llm_response.notes:
        st.info(result.llm_response.notes)

    st.caption(
        "⚠️ Prices are AI-generated estimates for planning purposes, not live "
        "market prices. Actual costs will vary by store and location."
    )
