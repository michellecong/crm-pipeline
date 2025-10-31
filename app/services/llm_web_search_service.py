import asyncio
import json
import logging
from typing import Optional
from datetime import datetime

from openai import OpenAI

from ..config import settings
from ..schemas.search import LLMCompanyWebSearchResponse


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
        "You are a Web Research Planner for B2B sales intelligence. "
        "Your goal: collect URLs that will help understand a B2B seller company's "
        "buyers (persona), pain points they solve, value propositions, and product offerings. "
        "\n\n"
        "Plan strategic search queries and use web_search to collect URLs. "
        "Focus on finding:\n"
        "- Official website and product pages (features, use cases, benefits)\n"
        "- Customer case studies/success stories (reveals buyer personas & pain points)\n"
        "- Recent news/announcements (funding, product launches, partnerships)\n"
        "- Industry analyst reports or authoritative third-party reviews\n"
        "\n"
        "Prefer high-authority sources. Include both official domain (with site: filter) "
        "and reputable third-party sources (Bloomberg, Reuters, WSJ, TechCrunch, industry publications). "
        "\n\n"
        "**CRITICAL REQUIREMENTS:**\n"
        "1. You MUST find and include the official website URL\n"
        "2. Output MUST be in valid JSON format matching this schema:\n"
        "{\n"
        '  "company": "string",\n'
        '  "queries_planned": ["string"],\n'
        '  "official_website": [{"url": "string", "title": "string"}],\n'
        '  "products": [{"url": "string", "title": "string"}],\n'
        '  "news": [{"url": "string", "title": "string", "published_at": "optional"}],\n'
        '  "case_studies": [{"url": "string", "title": "string"}],\n'
        '  "collected_at": "ISO timestamp"\n'
        "}\n"
        "\n"
        "The 'official_website' field MUST contain at least one entry with the company's main website."
    )

    user_prompt = (
        f"Company: \"{company_name}\"\n"
        "\n"
        "Research objective: Gather source material to later build:\n"
        "1. Buyer personas (who buys from this company?)\n"
        "2. Customer pain points (what problems do they solve?)\n"
        "3. Value propositions (why customers choose them?)\n"
        "4. Product/service details\n"
        "\n"
        "Your task NOW: Plan and execute search queries to collect URLs. Specifically find:\n"
        "- **REQUIRED**: Official homepage (must be the first query)\n"
        "- Official product/solution pages\n"
        "- Customer case studies, testimonials, success stories (look for quotes, metrics)\n"
        "- Recent news (last 12 months): funding, partnerships, product launches\n"
        "- Third-party reviews, analyst reports, or industry coverage\n"
        "\n"
        "Search strategy:\n"
        "- FIRST: Search for the company's official website\n"
        "- Use site:{official_domain} for official content\n"
        "- Use company name + keywords like 'case study', 'customer story', 'announces', 'review'\n"
        "- Target high-authority domains: reuters.com, bloomberg.com, wsj.com, ft.com, techcrunch.com, etc.\n"
        "\n"
        "Return: Valid JSON with deduplicated URLs and descriptive titles. "
        "Avoid social media unless it's official press/case content.\n"
        "\n"
        "Remember: The 'official_website' array MUST have at least one entry."
    )

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        tools=[{"type": "web_search"}]
    )

    text = _extract_output_text(response)
    return text or ""


async def llm_company_web_search_freeform(company_name: str) -> str:
    if not isinstance(company_name, str) or not company_name.strip():
        raise ValueError("Company name must be a non-empty string")
    return await asyncio.to_thread(_sync_company_web_search_freeform, company_name.strip())


def _sync_company_web_search_structured(company_name: str) -> LLMCompanyWebSearchResponse:
    """
    Structured version that returns validated JSON response.
    Ensures official website is present.
    """
    result_text = _sync_company_web_search_freeform(company_name)
    
    try:
        # Parse JSON from LLM response
        result_dict = json.loads(result_text)
        
        # Validate that official_website exists and is not empty
        if not result_dict.get("official_website"):
            raise ValueError(f"LLM did not return official website for {company_name}")
        
        # Add timestamp if not present
        if "collected_at" not in result_dict or not result_dict["collected_at"]:
            result_dict["collected_at"] = datetime.utcnow().isoformat()
        
        # Validate and parse with Pydantic
        response = LLMCompanyWebSearchResponse(**result_dict)
        
        logger.info(
            f"Successfully collected {len(response.official_website)} official URLs, "
            f"{len(response.products)} product URLs, {len(response.news)} news items, "
            f"{len(response.case_studies)} case studies for {company_name}"
        )
        
        return response
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {e}")
        logger.debug(f"Raw response: {result_text[:500]}")
        raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to validate LLM response: {e}")
        raise


async def llm_company_web_search_structured(company_name: str) -> LLMCompanyWebSearchResponse:
    """
    Async wrapper for structured company web search.
    Returns validated JSON with guaranteed official website.
    """
    if not isinstance(company_name, str) or not company_name.strip():
        raise ValueError("Company name must be a non-empty string")
    return await asyncio.to_thread(_sync_company_web_search_structured, company_name.strip())


