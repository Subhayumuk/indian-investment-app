from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any
import traceback
import os

from agent.agent_logic import analyze_tax


app = FastAPI(
    title="Danish Resident NRI Investment and Tax Planner",
    description="Planner for Danish tax residents with Indian savings/investments.",
    version="1.0.0",
)


# Serve static files
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


class PlannerInput(BaseModel):
    # Residency / identity
    residency_country: Optional[str] = "Denmark"
    tax_resident_denmark: Optional[bool] = True
    indian_residential_status: Optional[str] = "NRI"

    # Indian compliance
    has_pan: Optional[bool] = True
    has_aadhaar: Optional[bool] = None
    files_india_itr: Optional[bool] = False

    # Denmark compliance
    declares_india_income_in_denmark: Optional[bool] = False

    # Exchange rate
    inr_to_dkk_rate: Optional[float] = 0.083

    # Indian savings/investments
    india_principal_inr: Optional[float] = None
    india_annual_interest_inr: Optional[float] = None
    india_interest_rate_percent: Optional[float] = None
    indian_tds_percent: Optional[float] = 10.0

    # Danish income / capital income
    dk_salary_income_dkk: Optional[float] = None
    dk_capital_income_dkk: Optional[float] = None
    dk_bank_interest_dkk: Optional[float] = None

    # Planning preferences
    risk_profile: Optional[str] = "moderate"
    investment_horizon_years: Optional[int] = 7
    monthly_expenses_dkk: Optional[float] = None
    emergency_months: Optional[int] = 6
    needs_liquidity: Optional[bool] = True
    wants_india_exposure: Optional[bool] = True
    wants_denmark_investments: Optional[bool] = True

    # Indian bank accounts
    has_nro_account: Optional[bool] = True
    has_nre_account: Optional[bool] = False
    has_fcnr_account: Optional[bool] = False

    # Free text
    notes: Optional[str] = None


DISPLAY_ORDER = [
    "residency_country",
    "tax_resident_denmark",
    "indian_residential_status",
    "has_pan",
    "has_aadhaar",
    "inr_to_dkk_rate",
    "india_principal_inr",
    "india_annual_interest_inr",
    "india_interest_rate_percent",
    "indian_tds_percent",
    "dk_salary_income_dkk",
    "dk_capital_income_dkk",
    "dk_bank_interest_dkk",
    "risk_profile",
    "investment_horizon_years",
    "monthly_expenses_dkk",
    "emergency_months",
    "needs_liquidity",
    "wants_india_exposure",
    "wants_denmark_investments",
    "has_nro_account",
    "has_nre_account",
    "has_fcnr_account",
    "files_india_itr",
    "declares_india_income_in_denmark",
    "notes",
]


def model_to_actual_dict(payload: PlannerInput) -> Dict[str, Any]:
    """
    Returns only fields actually sent by the frontend/client.
    This avoids showing backend defaults as if the user entered them.
    """
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=True)
    return payload.dict(exclude_unset=True)


def model_to_normalized_dict(payload: PlannerInput) -> Dict[str, Any]:
    """
    Returns full payload with defaults.
    Used internally for calculations.
    """
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


def format_key(key: str) -> str:
    return key.replace("_", " ").title()


def format_value(value: Any, key: str = "") -> str:
    if value is None:
        return "Not provided"

    if value == "":
        return "Not provided"

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, float):
        key_lower = key.lower()

        # Better formatting for exchange rates and percentages
        if "rate" in key_lower:
            return f"{value:,.4f}".rstrip("0").rstrip(".")

        if "percent" in key_lower or "tds" in key_lower:
            return f"{value:,.2f}".rstrip("0").rstrip(".")

        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    return str(value)


def ordered_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keeps important planner fields in a stable order.
    Unknown extra fields are appended after known fields.
    """
    ordered = {}

    for key in DISPLAY_ORDER:
        if key in data:
            ordered[key] = data[key]

    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value

    return ordered


def render_dict(title: str, data: Dict[str, Any]) -> str:
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
    except Exception:
        return default


def build_financial_snapshot(inputs: Dict[str, Any]) -> Dict[str, Any]:
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


def extract_summary_from_result(result: Any) -> str:
    if isinstance(result, dict):
        summary = result.get("summary")
        if summary:
            return str(summary)

        output = result.get("output")
        if output:
            return str(output)

        return "Structured planning result generated successfully."

    return str(result)


def render_key_sections_from_result(result: Dict[str, Any]) -> str:
    """
    Converts important structured result sections into readable text.
    Avoids duplicating internal frontend/backend debug sections.
    """
    if not isinstance(result, dict):
        return str(result)

    skip_keys = {
        "summary",
        "output",
        "received_inputs_from_frontend",
        "normalized_inputs_used_for_calculation",
        "frontend_financial_snapshot",
        "raw_agent_result",
    }

    lines = ["Planner Result", "--------------"]

    rendered_any = False

    for key, value in result.items():
        if key in skip_keys:
            continue

        rendered_any = True

        if isinstance(value, dict):
            lines.append("")
            lines.append(render_dict(format_key(key), value))

        elif isinstance(value, list):
            lines.append("")
            lines.append(f"{format_key(key)}")
            lines.append("-" * len(format_key(key)))

            if not value:
                lines.append("None")
            else:
                for item in value:
                    if isinstance(item, dict):
                        item_text = ", ".join(
                            f"{format_key(k)}: {format_value(v, k)}"
                            for k, v in item.items()
                        )
                        lines.append(f"- {item_text}")
                    else:
                        lines.append(f"- {format_value(item, key)}")

        else:
            lines.append(f"- {format_key(key)}: {format_value(value, key)}")

    if not rendered_any:
        lines.append("No additional structured result sections returned.")

    return "\n".join(lines)


def build_readable_summary(
    result: Dict[str, Any],
    actual_inputs: Dict[str, Any],
    normalized_inputs: Dict[str, Any],
) -> str:
    financial_snapshot = build_financial_snapshot(normalized_inputs)
    summary_text = extract_summary_from_result(result)

    sections = []

    sections.append(
        "Danish Resident NRI Investment and Tax Planner\n"
        "================================================\n"
        "\n"
        "Important: This is a planning assistant output, not personal tax/legal advice. "
        "Please verify with a Danish tax adviser and an Indian CA before acting.\n"
    )

    sections.append(render_dict("Received Inputs From Frontend", actual_inputs))
    sections.append(render_dict("Normalized Inputs Used For Calculation", normalized_inputs))
    sections.append(render_dict("Frontend Financial Snapshot", financial_snapshot))

    sections.append(
        "High-Level Summary\n"
        "------------------\n"
        f"{summary_text}"
    )

    if isinstance(result, dict):
        sections.append(render_key_sections_from_result(result))

    return "\n\n".join(sections)


def normalize_response(
    raw_result: Any,
    actual_inputs: Dict[str, Any],
    normalized_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Always returns:
    - output
    - result
    - structured_result
    """

    if isinstance(raw_result, dict):
        structured_result = dict(raw_result)
    else:
        structured_result = {
            "summary": str(raw_result),
            "raw_agent_result": raw_result,
        }

    structured_result["received_inputs_from_frontend"] = actual_inputs
    structured_result["normalized_inputs_used_for_calculation"] = normalized_inputs
    structured_result["frontend_financial_snapshot"] = build_financial_snapshot(
        normalized_inputs
    )

    output = build_readable_summary(
        structured_result,
        actual_inputs=actual_inputs,
        normalized_inputs=normalized_inputs,
    )

    return {
        "output": output,
        "result": structured_result,
        "structured_result": structured_result,
    }


@app.get("/")
def home():
    index_path = os.path.join("static", "index.html")

    if os.path.exists(index_path):
        return FileResponse(index_path)

    return JSONResponse(
        content={
            "message": "Frontend file not found.",
            "expected_file": "static/index.html",
        }
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "static_index_exists": os.path.exists(os.path.join("static", "index.html")),
        "current_working_directory": os.getcwd(),
    }


@app.post("/api/agent")
def run_agent(payload: PlannerInput):
    try:
        actual_inputs = model_to_actual_dict(payload)
        normalized_inputs = model_to_normalized_dict(payload)

        print("\nActual inputs received from frontend:")
        print(actual_inputs)

        print("\nNormalized inputs used for calculation:")
        print(normalized_inputs)

        raw_result = analyze_tax(normalized_inputs)

        print("\nRaw result from analyze_tax:")
        print(raw_result)

        normalized_response = normalize_response(
            raw_result,
            actual_inputs=actual_inputs,
            normalized_inputs=normalized_inputs,
        )

        return JSONResponse(content=jsonable_encoder(normalized_response))

    except Exception as e:
        print("ERROR in /api/agent:")
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                {
                    "output": f"Backend error: {str(e)}",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
        )


@app.post("/analyze")
def analyze_compatibility(payload: PlannerInput):
    """
    Compatibility endpoint.
    Same behavior as /api/agent.
    """
    try:
        actual_inputs = model_to_actual_dict(payload)
        normalized_inputs = model_to_normalized_dict(payload)

        raw_result = analyze_tax(normalized_inputs)

        normalized_response = normalize_response(
            raw_result,
            actual_inputs=actual_inputs,
            normalized_inputs=normalized_inputs,
        )

        return JSONResponse(content=jsonable_encoder(normalized_response))

    except Exception as e:
        print("ERROR in /analyze:")
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                {
                    "output": f"Backend error: {str(e)}",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
        )