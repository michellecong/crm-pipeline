import asyncio
import logging
from typing import Optional

from openai import OpenAI

from ..config import settings


logger = logging.getLogger(__name__)


def _extract_output_text(response) -> str:
    """Best-effort extraction of plaintext from Responses API result."""
    # Newer SDKs expose `output_text`
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text

    # Fallback: traverse `output` blocks
    try:
        blocks = getattr(response, "output", []) or []
        parts = []
        for block in blocks:
            content_list = getattr(block, "content", []) or []
            for item in content_list:
                item_type = getattr(item, "type", None)
                if item_type in ("output_text", "text"):
                    text_obj = getattr(item, "text", None)
                    if isinstance(text_obj, str):
                        parts.append(text_obj)
                    elif text_obj is not None:
                        value = getattr(text_obj, "value", None)
                        if isinstance(value, str):
                            parts.append(value)
        return "\n".join(parts).strip()
    except Exception:
        return ""


def _create_client(api_key: Optional[str]) -> OpenAI:
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)


 


def _sync_company_web_search_freeform(company_name: str) -> str:
    client = _create_client(settings.OPENAI_API_KEY)
    model = settings.OPENAI_MODEL or "gpt-4.1"

    system_prompt = (
        "You are a Web Research Planner focused on B2B sellers. "
        "Plan effective search queries and use the web_search tool to collect URLs. "
        "Include both the official website and authoritative third-party sources "
        "(e.g., top-tier media, reputable industry publications, government registries). "
        "Prefer high-authority domains. Do not generate long summaries. "
        "Focus on listing useful URLs and brief titles."
    )

    user_prompt = (
        f"Company: \"{company_name}\"\n"
        "Please: plan multiple precise queries (including site: filters for the official domain) "
        "AND non-site queries to capture reputable media coverage; collect URLs for the official site, "
        "product pages, news (last 12 months), and case studies/customer stories. "
        "Prefer high-authority sources outside the official domain (e.g., reuters.com, bloomberg.com, wsj.com, ft.com, techcrunch.com). "
        "Avoid social profiles unless they contain official press/case content. Deduplicate and return concise results with URLs."
    )

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        tools=[{"type": "web_search"}],
    )

    text = _extract_output_text(response)
    return text or ""


async def llm_company_web_search_freeform(company_name: str) -> str:
    if not isinstance(company_name, str) or not company_name.strip():
        raise ValueError("Company name must be a non-empty string")
    return await asyncio.to_thread(_sync_company_web_search_freeform, company_name.strip())


