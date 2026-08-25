from typing import Dict
from app.models.user_profile import UserProfile
from app.models.recommendation import AllocationBreakdown

class AllocationEngine:
    def __init__(self):
        self.base_allocations = {
            "conservative": {"equity": 20, "debt": 50, "real_estate": 10, "gold": 15, "cash": 5, "hybrid": 0},
            "moderate": {"equity": 45, "debt": 30, "real_estate": 10, "gold": 10, "cash": 5, "hybrid": 0},
            "aggressive": {"equity": 70, "debt": 15, "real_estate": 5, "gold": 5, "cash": 5, "hybrid": 0},
        }

    def _age_adjustment(self, allocation: Dict, age: int) -> Dict:
        adj = allocation.copy()
        if age > 55:
            shift = min(15, adj["equity"])
            adj["equity"] -= shift
            adj["debt"] += shift
        elif age < 30:
            shift = 10
            adj["equity"] = min(80, adj["equity"] + shift)
            adj["debt"] = max(5, adj["debt"] - shift)
        return adj

    def _goal_adjustment(self, allocation: Dict, goal: str) -> Dict:
        adj = allocation.copy()
        goal_lower = goal.lower() if goal else ""
        if "retirement" in goal_lower:
            adj["equity"] = max(adj["equity"] - 5, 10)
            adj["debt"] += 5
        elif "house" in goal_lower or "property" in goal_lower:
            adj["real_estate"] = min(adj["real_estate"] + 10, 30)
            adj["equity"] = max(adj["equity"] - 10, 10)
        elif "education" in goal_lower or "child" in goal_lower:
            adj["debt"] += 5
            adj["gold"] = max(adj["gold"] - 5, 5)
        return adj

    def _horizon_adjustment(self, allocation: Dict, horizon_years: int) -> Dict:
        adj = allocation.copy()
        if horizon_years < 3:
            shift = min(20, adj["equity"])
            adj["equity"] -= shift
            adj["debt"] += shift
            adj["cash"] = min(adj["cash"] + 5, 20)
        elif horizon_years > 10:
            adj["equity"] = min(adj["equity"] + 10, 80)
            adj["debt"] = max(adj["debt"] - 10, 10)
        return adj

    def _normalize(self, allocation: Dict) -> Dict:
        total = sum(allocation.values())
        if total == 0:
            return allocation
        return {k: round(v / total * 100, 1) for k, v in allocation.items()}

    def get_allocation(self, profile: UserProfile) -> AllocationBreakdown:
        risk = profile.risk_tolerance.lower() if profile.risk_tolerance else "moderate"
        if risk not in self.base_allocations:
            risk = "moderate"
        alloc = self.base_allocations[risk].copy()
        if profile.age:
            alloc = self._age_adjustment(alloc, profile.age)
        if profile.investment_goal:
            alloc = self._goal_adjustment(alloc, profile.investment_goal)
        if profile.investment_horizon_years:
            alloc = self._horizon_adjustment(alloc, profile.investment_horizon_years)
        alloc = self._normalize(alloc)
        return AllocationBreakdown(
            equity_pct=alloc.get("equity", 0),
            debt_pct=alloc.get("debt", 0),
            real_estate_pct=alloc.get("real_estate", 0),
            gold_pct=alloc.get("gold", 0),
            cash_pct=alloc.get("cash", 0),
            hybrid_pct=alloc.get("hybrid", 0),
        )
