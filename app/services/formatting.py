from typing import Any

from app.schemas import DISPLAY_ORDER


def format_key(key: str) -> str:
    return key.replace("_", " ").title()


def format_value(value: Any, key: str = "") -> str:
    if value is None or value == "":
        return "Not provided"

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, float):
        key_lower = key.lower()
        if "rate" in key_lower:
            return f"{value:,.4f}".rstrip("0").rstrip(".")
        if "percent" in key_lower or "tds" in key_lower:
            return f"{value:,.2f}".rstrip("0").rstrip(".")
        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    return str(value)


def ordered_dict(data: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}

    for key in DISPLAY_ORDER:
        if key in data:
            ordered[key] = data[key]

    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value

    return ordered


def render_dict(title: str, data: dict[str, Any]) -> str:
    lines = [title, "-" * len(title)]

    if not data:
        lines.append("No data available.")
        return "\n".join(lines)

    data = ordered_dict(data)

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"\n{format_key(key)}:")
            if not value:
                lines.append("  - None")
            else:
                for sub_key, sub_value in value.items():
                    lines.append(
                        f"  - {format_key(sub_key)}: {format_value(sub_value, sub_key)}"
                    )
        elif isinstance(value, list):
            lines.append(f"\n{format_key(key)}:")
            if not value:
                lines.append("  - None")
            else:
                for item in value:
                    if isinstance(item, dict):
                        item_text = ", ".join(
                            f"{format_key(k)}: {format_value(v, k)}"
                            for k, v in item.items()
                        )
                        lines.append(f"  - {item_text}")
                    else:
                        lines.append(f"  - {format_value(item, key)}")
        else:
            lines.append(f"- {format_key(key)}: {format_value(value, key)}")

    return "\n".join(lines)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_financial_snapshot(inputs: dict[str, Any]) -> dict[str, Any]:
    inr_to_dkk_rate = safe_float(inputs.get("inr_to_dkk_rate"), 0.083)
    india_principal_inr = safe_float(inputs.get("india_principal_inr"), 0.0)
    india_annual_interest_inr = safe_float(inputs.get("india_annual_interest_inr"), 0.0)

    india_principal_dkk = india_principal_inr * inr_to_dkk_rate
    india_annual_interest_dkk = india_annual_interest_inr * inr_to_dkk_rate

    monthly_expenses_dkk = safe_float(inputs.get("monthly_expenses_dkk"), 0.0)
    emergency_months = int(safe_float(inputs.get("emergency_months"), 6))
    emergency_fund_required_dkk = monthly_expenses_dkk * emergency_months

    return {
        "india_principal_dkk": india_principal_dkk,
        "india_annual_interest_dkk": india_annual_interest_dkk,
        "emergency_fund_required_dkk": emergency_fund_required_dkk,
    }
