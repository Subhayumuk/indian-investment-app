from typing import Any

from app.services.formatting import (
    build_financial_snapshot,
    format_key,
    format_value,
    render_dict,
)


def extract_summary_from_result(result: Any) -> str:
    if isinstance(result, dict):
        summary = result.get("summary")
        if summary:
            return str(summary)

        output = result.get("output")
        if output:
            return str(output)

        display_text = result.get("display_text")
        if display_text:
            return str(display_text)

        return "Structured planning result generated successfully."

    return str(result)


def render_key_sections_from_result(result: dict[str, Any]) -> str:
    skip_keys = {
        "summary",
        "output",
        "display_text",
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
    result: dict[str, Any],
    actual_inputs: dict[str, Any],
    normalized_inputs: dict[str, Any],
) -> str:
    financial_snapshot = build_financial_snapshot(normalized_inputs)
    summary_text = extract_summary_from_result(result)

    sections = [
        (
            "Danish Resident NRI Investment and Tax Planner\n"
            "================================================\n"
            "\n"
            "Important: This is a planning assistant output, not personal tax/legal advice. "
            "Please verify with a Danish tax adviser and an Indian CA before acting.\n"
        ),
        render_dict("Received Inputs From Frontend", actual_inputs),
        render_dict("Normalized Inputs Used For Calculation", normalized_inputs),
        render_dict("Frontend Financial Snapshot", financial_snapshot),
        (
            "High-Level Summary\n"
            "------------------\n"
            f"{summary_text}"
        ),
    ]

    if isinstance(result, dict):
        sections.append(render_key_sections_from_result(result))

    return "\n\n".join(sections)


def normalize_response(
    raw_result: Any,
    actual_inputs: dict[str, Any],
    normalized_inputs: dict[str, Any],
) -> dict[str, Any]:
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
