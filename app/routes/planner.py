import logging
import traceback

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from agent.agent_logic import analyze_tax
from app.config import get_settings
from app.schemas import PlannerInput, model_to_actual_dict, model_to_normalized_dict
from app.services.input_adapter import adapt_planner_inputs
from app.services.response import normalize_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["planner"])


def _run_planner(payload: PlannerInput) -> JSONResponse:
    actual_inputs = model_to_actual_dict(payload)
    normalized_inputs = model_to_normalized_dict(payload)
    agent_inputs = adapt_planner_inputs(normalized_inputs)

    logger.debug("Actual inputs: %s", actual_inputs)
    logger.debug("Agent inputs: %s", agent_inputs)

    raw_result = analyze_tax(agent_inputs)
    normalized = normalize_response(
        raw_result,
        actual_inputs=actual_inputs,
        normalized_inputs=normalized_inputs,
    )

    return JSONResponse(content=jsonable_encoder(normalized))


@router.post("/api/agent")
def run_agent(payload: PlannerInput):
    try:
        return _run_planner(payload)
    except Exception as exc:
        logger.exception("Error in /api/agent")
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                {
                    "output": f"Backend error: {exc}",
                    "error": str(exc),
                    "traceback": traceback.format_exc() if get_settings().DEBUG else None,
                }
            ),
        )


@router.post("/analyze")
def analyze_compatibility(payload: PlannerInput):
    """Compatibility endpoint with the same behavior as /api/agent."""
    try:
        return _run_planner(payload)
    except Exception as exc:
        logger.exception("Error in /analyze")
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                {
                    "output": f"Backend error: {exc}",
                    "error": str(exc),
                    "traceback": traceback.format_exc() if get_settings().DEBUG else None,
                }
            ),
        )
