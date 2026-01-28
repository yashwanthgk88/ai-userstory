import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.user import User
from core.security import get_current_user
from config import settings
from services.ai_analyzer import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT_TEMPLATE,
    DEFAULT_MODEL,
    DEFAULT_MAX_TOKENS,
    analyze_with_llm,
)
from services.llm_provider import PROVIDER_MODELS, PROVIDER_DEFAULTS

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai_console"])


class AIConfigResponse(BaseModel):
    system_prompt: str
    user_prompt_template: str
    model: str
    max_tokens: int
    provider: str
    providers: dict  # provider_name -> { models: [...], default_model: str }


class AITestRequest(BaseModel):
    title: str
    description: str
    acceptance_criteria: str | None = None
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    model: str | None = None
    max_tokens: int | None = None
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None


@router.get("/ai-config", response_model=AIConfigResponse)
async def get_ai_config(user: User = Depends(get_current_user)):
    providers_info = {}
    for name, models in PROVIDER_MODELS.items():
        providers_info[name] = {
            "models": models,
            "default_model": PROVIDER_DEFAULTS.get(name, ""),
        }
    return AIConfigResponse(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        user_prompt_template=DEFAULT_USER_PROMPT_TEMPLATE,
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        provider=settings.llm_provider,
        providers=providers_info,
    )


@router.post("/ai-console/test")
async def test_ai_analysis(req: AITestRequest, user: User = Depends(get_current_user)):
    try:
        result = await analyze_with_llm(
            title=req.title,
            description=req.description,
            acceptance_criteria=req.acceptance_criteria,
            system_prompt=req.system_prompt,
            user_prompt_template=req.user_prompt_template,
            model=req.model,
            max_tokens=req.max_tokens,
            provider_name=req.provider,
            api_key=req.api_key,
            base_url=req.base_url,
        )

        raw_response = result.pop("_raw_response", "")
        model_used = result.pop("_model", "")
        input_tokens = result.pop("_input_tokens", 0)
        output_tokens = result.pop("_output_tokens", 0)

        return {
            "raw_response": raw_response,
            "parsed": result,
            "model": model_used,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "abuse_case_count": len(result.get("abuse_cases", [])),
            "stride_threat_count": len(result.get("stride_threats", [])),
            "requirement_count": len(result.get("security_requirements", [])),
            "risk_score": result.get("risk_score", 0),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("AI Console test failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {e}")
