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
        "You are a Web Research Planner for B2B sales intelligence. "
        "Your goal: collect URLs that will help understand a B2B seller company's "
        "buyers (persona), pain points they solve, value propositions, and product offerings. "
        "\n\n"
        "Plan strategic search queries and use web_search to collect URLs. "
        "Focus on finding:\n"
        "- Official product pages (features, use cases, benefits)\n"
        "- Customer case studies/success stories (reveals buyer personas & pain points)\n"
        "- Recent news/announcements (funding, product launches, partnerships)\n"
        "- Industry analyst reports or authoritative third-party reviews\n"
        "\n"
        "Prefer high-authority sources. Include both official domain (with site: filter) "
        "and reputable third-party sources (Bloomberg, Reuters, WSJ, TechCrunch, industry publications). "
        "Output: URLs with brief titles only. No summaries or content analysis at this stage."
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
        "- Official homepage and product/solution pages\n"
        "- Customer case studies, testimonials, success stories (look for quotes, metrics)\n"
        "- Recent news (last 12 months): funding, partnerships, product launches\n"
        "- Third-party reviews, analyst reports, or industry coverage\n"
        "\n"
        "Search strategy:\n"
        "- Use site:{official_domain} for official content\n"
        "- Use company name + keywords like 'case study', 'customer story', 'announces', 'review'\n"
        "- Target high-authority domains: reuters.com, bloomberg.com, wsj.com, ft.com, techcrunch.com, etc.\n"
        "\n"
        "Return: Deduplicated list of URLs with brief descriptive titles. "
        "Avoid social media unless it's official press/case content."
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


