from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4

router = APIRouter()


class EvaluateRequest(BaseModel):
    product_a: dict
    product_b: dict
    mission_spec: dict = {}
    user_id: str = "U001"


@router.post("/evaluate")
async def evaluate_comparison_endpoint(req: EvaluateRequest):
    """Advanced comparison with full audit trace.

    Uses the 7-phase comparison engine:
    classify → constraints → score → evidence → explain
    """
    from app.services.comparison.engine import evaluate_comparison

    result = await evaluate_comparison({
        "product_a": req.product_a,
        "product_b": req.product_b,
        "mission_spec": req.mission_spec,
        "user_id": req.user_id,
    })

    return {
        "success": True,
        "data": result,
        "error": result.get("error"),
        "request_id": str(uuid4()),
    }
