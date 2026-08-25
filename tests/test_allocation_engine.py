from types import SimpleNamespace

import pytest

from app.modules.allocation_engine import AllocationEngine

engine = AllocationEngine()


def make_profile(risk_tolerance="moderate", age=35, investment_goal="wealth_creation", investment_horizon_years=10):
    return SimpleNamespace(
        risk_tolerance=risk_tolerance,
        age=age,
        investment_goal=investment_goal,
        investment_horizon_years=investment_horizon_years,
    )


@pytest.mark.parametrize("risk", ["conservative", "moderate", "aggressive"])
def test_allocation_percentages_always_sum_to_100(risk):
    alloc = engine.get_allocation(make_profile(risk_tolerance=risk))
    total = (
        alloc.equity_pct + alloc.debt_pct + alloc.real_estate_pct
        + alloc.gold_pct + alloc.cash_pct + alloc.hybrid_pct
    )
    assert total == pytest.approx(100.0, abs=0.1)


def test_unknown_risk_tolerance_falls_back_to_moderate():
    alloc_unknown = engine.get_allocation(make_profile(risk_tolerance="yolo"))
    alloc_moderate = engine.get_allocation(make_profile(risk_tolerance="moderate"))
    assert alloc_unknown == alloc_moderate


def test_older_investor_shifts_from_equity_to_debt():
    young = engine.get_allocation(make_profile(age=25))
    old = engine.get_allocation(make_profile(age=60))
    assert old.equity_pct < young.equity_pct
    assert old.debt_pct > young.debt_pct


def test_short_horizon_reduces_equity_and_raises_cash():
    long_horizon = engine.get_allocation(make_profile(investment_horizon_years=15))
    short_horizon = engine.get_allocation(make_profile(investment_horizon_years=2))
    assert short_horizon.equity_pct < long_horizon.equity_pct
    assert short_horizon.cash_pct >= long_horizon.cash_pct


def test_property_goal_increases_real_estate_allocation():
    baseline = engine.get_allocation(make_profile(investment_goal="wealth_creation"))
    property_goal = engine.get_allocation(make_profile(investment_goal="property_purchase"))
    assert property_goal.real_estate_pct > baseline.real_estate_pct


def test_retirement_goal_reduces_equity():
    baseline = engine.get_allocation(make_profile(investment_goal="wealth_creation"))
    retirement = engine.get_allocation(make_profile(investment_goal="retirement"))
    assert retirement.equity_pct < baseline.equity_pct
