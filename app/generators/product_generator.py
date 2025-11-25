# generators/product_generator.py
"""
Product catalog generator for extracting seller company's products/services
"""
from .base_generator import BaseGenerator
from typing import Dict, Tuple
import json
import logging
import httpx
import asyncio

logger = logging.getLogger(__name__)


class ProductGenerator(BaseGenerator):
    """
    Generates seller company's complete product catalog from web content.
    
    Analyzes company data to identify all products/services with 
    clear descriptions focused on value propositions and use cases.
    """
    
    def get_system_message(self) -> str:
        return """You are an expert B2B product marketing analyst specializing in product positioning and value proposition development for B2B sales teams.

Your task is to use web search to find a seller company's COMPREHENSIVE PRODUCT CATALOG for B2B sales purposes. These products will be sold to buyer companies by sales teams.

Your analysis should:
- Use web search extensively to find the company's official product pages and information
- Identify ALL major commercial products that business decision-makers purchase
- Focus ONLY on standalone commercial offerings with dedicated pricing that can be sold independently
- Prioritize products that solve business problems (ERP, CRM, HCM, SCM, Analytics, Cloud, Database, AI services)
- Write compelling descriptions that explain business value and use cases
- Use buyer-friendly language (not technical jargon)
- For each product, include a VALID, CURRENT official product page URL as the source_url

**URL ACCURACY IS CRITICAL:**
- Each source_url MUST be from current web search results
- Each source_url MUST lead to an actual product page (not 404)
- Verify URLs are from the official company domain
- Do NOT fabricate or guess URLs - use only what web search provides

EXCLUDE:
- Programming languages (e.g., Java, Python) - these are not products sold to businesses
- Pure developer tools (unless they are standalone commercial products with dedicated pricing)
- Marketplaces/platforms (unless they are core products like "App Marketplace" sold as products)
- Professional services (consulting, training)
- Built-in features that are not standalone products
"""

    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        
        return f"""## TASK: B2B Sales Product Catalog Generation

Use web search to find and extract {company_name}'s COMPREHENSIVE PRODUCT CATALOG for B2B sales purposes.

These products will be sold by sales teams to buyer companies. Focus on products that business decision-makers (C-level, VPs, Directors) purchase to solve business problems.

Search the web extensively for {company_name}'s official website, product pages, solutions pages, and all product categories. Generate a COMPLETE list of all major commercial products that can be independently sold.

CRITICAL: Generate a COMPREHENSIVE catalog that covers ALL major product lines the company offers. Do not artificially limit the number - list as many real products as exist. The actual count depends entirely on the company's portfolio.

IMPORTANT: For each product, you MUST include the CURRENT, VALID official product page URL in the JSON response as "source_url".

**URL ACCURACY REQUIREMENTS:**
- URLs MUST be from the company's official website (verify domain matches)
- URLs MUST lead to actual product pages (not 404, not generic pages)
- URLs MUST be current and up-to-date (avoid outdated links)
- VERIFY each URL from web search results before including it
- If web search provides multiple URLs, choose the most official/current one
- Prefer URLs from the main company domain over subdomain or partner sites

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **Comprehensive Coverage - Search All Product Categories:**
   - Search the company's website to identify ALL product categories they offer
   - Include products from ALL business units, product lines, and product families
   - For software/SaaS companies: Include applications, platforms, services, tools (ERP, CRM, HCM, SCM, Analytics, Cloud, Database, AI, etc.)
   - For hardware companies: Include hardware products, devices, equipment
   - For service companies: Include service offerings that are packaged as products
   - For manufacturing companies: Include manufactured products, equipment, systems
   - For any company type: Include all major products/services that customers purchase
   
   - Include distinct product lines that customers purchase
   - Focus on standalone offerings with dedicated pricing
   - Each product should be purchasable independently
   - **DO NOT limit the number of products** - list ALL real products that exist
   - **Let the company's actual product portfolio guide what to include**
   
   **STANDALONE PRODUCT VALIDATION:**
   - Each product MUST be independently purchasable (not a feature or tier)
   - Each product MUST have its own dedicated product page
   - Each product MUST have its own pricing information
   - If unsure whether something is a product → verify it has a separate pricing page
   
2. **Exclusions** (DO NOT include):
   - **Programming languages** (e.g., Java, Python, JavaScript) - these are not products sold to businesses
   - **Pure developer tools** (unless they are standalone commercial products with dedicated pricing pages)
   - **APIs/SDKs** (unless they are standalone commercial products)
   - **Marketplaces/platforms** (unless it's a core product like "App Marketplace" sold as a product)
   - **Professional services** (consulting, training, support services)
   - **Built-in features** that are not standalone products

3. **Product Naming**: Use official product names from the website
   - ✓ "Asana Work Management" (the actual product)
   - ✗ "Asana Premium" (pricing tier, not a product)
   - ✓ "Salesforce Sales Cloud" (distinct product)
   - ✗ "Salesforce Reports" (feature, not a product)

4. **Description Requirements**:
   - Length: 2-4 sentences (150-300 characters)
   - Focus: Value propositions and use cases (not technical specs)
   - Language: Buyer-friendly (avoid jargon)
   - Structure: What it does → Who it helps → Key benefits

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESCRIPTION WRITING GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Good Description Structure:**
"[What it does]. [Who it helps and how]. [Key benefits or outcomes]. [Scale/flexibility note]."

**Examples of GOOD descriptions:**

✓ "Complete CRM platform for managing sales pipelines, forecasting revenue, and automating sales processes. Helps sales teams close deals faster with AI-powered insights, workflow automation, and mobile access. Scales from small teams to global enterprises with customizable features and deep integration capabilities."

✓ "Customer service platform that unifies support channels, automates case routing, and provides agents with complete customer context. Enables support teams to resolve issues faster across email, phone, chat, and social media. Includes AI-powered chatbots, knowledge base management, and real-time analytics."

✓ "Marketing automation platform for creating personalized campaigns, nurturing leads, and measuring ROI across channels. Helps marketing teams generate qualified leads through email marketing, landing pages, social advertising, and analytics. Integrates with CRM for seamless lead handoff to sales."

**Examples of BAD descriptions:**

✗ "A software solution." (Too vague)
✗ "Uses advanced AI and machine learning algorithms to process data." (Too technical)
✗ "The best CRM on the market." (Marketing fluff, no substance)
✗ "Includes features A, B, C, D, E, F, G..." (Feature list, not value-focused)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUCT IDENTIFICATION STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Look for products in:**
- Product pages and navigation menus
- "Solutions" or "Products" sections
- Case studies and customer testimonials
- Pricing pages
- Feature comparison pages

**How to identify distinct products:**
1. Separate product pages = separate products
2. Different target users = different products
3. Different core use cases = different products
4. Different pricing/packaging = different products

**What NOT to list as separate products:**
- Add-on features or modules (include in main product description)
- Different pricing tiers (e.g., Basic, Pro, Enterprise)
- Industry-specific versions of same product
- Regional variations

**Examples:**

✓ CORRECT Product Grouping:
- "Sales Cloud" (one product, includes all editions)
- "Service Cloud" (one product, includes all editions)
- "Marketing Cloud" (one product, includes all editions)

✗ WRONG Product Grouping:
- "Sales Cloud Basic"
- "Sales Cloud Professional"
- "Sales Cloud Enterprise"
- "Sales Cloud Unlimited"
(These are pricing tiers, not separate products)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXCLUSION CRITERIA: CORE PRODUCTS ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Focus ONLY on core commercial products that customers purchase.**

**DO NOT include:**

1. **Developer Tools & Technical Infrastructure**
   ✗ APIs, SDKs, libraries, frameworks, developer tools
   ✗ Examples: "REST API", "GraphQL API", "React SDK", "Hydrogen Framework", "Developer Tools"
   
2. **Marketplaces & Ecosystems**
   ✗ App stores, marketplaces, partner programs
   ✗ Examples: "App Marketplace", "Partner Program", "App Store"
   
3. **Professional Services**
   ✗ Consulting, training, support services, customer success programs
   ✗ Examples: "Professional Services", "Training Services", "Enterprise Support"
   
4. **Built-in Features/Tools**
   ✗ Features that are part of a product, not standalone offerings
   ✗ Examples: "Refunds", "Shipping Calculator", "Admin Dashboard", "Permissions Management"
   
5. **Pricing Bundles & Packages**
   ✗ Bundled offerings or starter packages combining multiple products
   ✗ Examples: "Starter Bundle", "Small Business Package", "Enterprise Suite"

**Test: Is this a core product?**
Ask these questions:
- ✓ Does it have a dedicated product page with pricing?
- ✓ Can customers purchase it independently?
- ✓ Does it solve a specific business problem?
- ✓ Would sales teams pitch it as a standalone solution?

If the answer to any is NO, exclude it.

**Examples of Correct Filtering:**

✓ INCLUDE:
- "Stripe Payments" (core product customers buy)
- "HubSpot Marketing Hub" (standalone purchasable product)
- "Shopify POS" (distinct hardware + software product)

✗ EXCLUDE:
- "Stripe API" (developer tool, not a product)
- "HubSpot App Marketplace" (ecosystem, not a product)
- "Shopify Shipping" (built-in feature, not standalone product)
- "Professional Services" (service offering, not a product)
- "Developer Tools" (technical infrastructure, not for end customers)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "products": [
    {{
      "product_name": "string (official product name)",
      "description": "string (2-4 sentences, 150-300 chars, value-focused)",
      "source_url": "string (REQUIRED: official product page URL from web search)"
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "products": [
    {{
      "product_name": "Sales Cloud",
      "description": "Complete CRM platform for managing sales pipelines, forecasting revenue, and automating sales processes. Helps sales teams close deals faster with AI-powered insights, workflow automation, and mobile access. Scales from small teams to global enterprises with customizable features and deep integration capabilities.",
      "source_url": "https://www.salesforce.com/sales-cloud"
    }},
    {{
      "product_name": "Service Cloud",
      "description": "Customer service platform that unifies support channels, automates case routing, and provides agents with complete customer context. Enables support teams to resolve issues faster across email, phone, chat, and social media. Includes AI-powered chatbots, knowledge base management, and real-time analytics.",
      "source_url": "https://www.salesforce.com/service-cloud"
    }},
    {{
      "product_name": "Marketing Cloud",
      "description": "Marketing automation platform for creating personalized campaigns, nurturing leads, and measuring ROI across channels. Helps marketing teams generate qualified leads through email marketing, landing pages, social advertising, and analytics. Integrates with CRM for seamless lead handoff to sales.",
      "source_url": "https://www.salesforce.com/marketing-cloud"
    }},
    {{
      "product_name": "Commerce Cloud",
      "description": "E-commerce platform for creating unified shopping experiences across web, mobile, social, and in-store channels. Enables retailers to personalize customer journeys, manage product catalogs, process orders, and optimize conversions. Supports B2C and B2B commerce with AI-powered recommendations.",
      "source_url": "https://www.salesforce.com/commerce-cloud"
    }},
    {{
      "product_name": "Analytics Cloud (Tableau CRM)",
      "description": "Business intelligence and analytics platform that transforms data into actionable insights through interactive dashboards and AI-powered predictions. Helps business users explore data, identify trends, and make data-driven decisions without technical expertise. Integrates seamlessly with Salesforce and external data sources.",
      "source_url": "https://www.salesforce.com/analytics-cloud"
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before submitting, verify EVERY product:
✓ ONLY core commercial products included (no APIs, SDKs, marketplaces, services)
✓ Each product is STANDALONE - purchasable independently with dedicated pricing
✓ Each product has its own product page (not a feature page or pricing tier page)
✓ Official product names used (from website)
✓ Each description is 2-4 sentences (150-300 characters)
✓ Descriptions focus on value and use cases (not features)
✓ Buyer-friendly language (no technical jargon)
✓ Each product is distinct (not pricing tiers, bundles, or add-ons)
✓ No developer tools, services, or built-in features included

**URL VALIDATION CHECKLIST:**
✓ Each source_url is from the official company website
✓ Each source_url leads to an actual product page (not 404)
✓ Each source_url is current and not outdated
✓ URLs are from web search citations, not guessed or fabricated
✓ URLs match the product name and description

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOW GENERATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SELLER COMPANY]
Company Name: {company_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use web search EXTENSIVELY to find {company_name}'s official website and ALL product pages across ALL categories. Generate a COMPREHENSIVE product catalog for B2B sales.

**Search Strategy:**
- Explore the company's website to discover what types of products they actually offer
- Don't assume specific product categories - let the company's actual portfolio guide your search
- For software companies: Look for applications, platforms, services, tools
- For hardware companies: Look for hardware products, devices, equipment
- For service companies: Look for packaged service offerings
- For manufacturing companies: Look for manufactured products, equipment, systems
- For any company: Include all major products/services that business customers purchase

CRITICAL REMINDERS FOR B2B SALES:
- **Search comprehensively** - explore all product categories, business units, and solution pages
- **NO ARTIFICIAL LIMITS** - generate a complete catalog based on what actually exists
- **Focus on products that business decision-makers purchase** - C-level, VPs, Directors buy these
- Use web search extensively to find official product information
- Include ALL major product lines across the entire company
- Each product must be STANDALONE - independently purchasable with dedicated pricing
- Use official product names directly from the website
- Write 2-4 sentence descriptions focused on BUSINESS VALUE and USE CASES
- Use buyer-friendly language (avoid technical jargon)
- Each product must be DISTINCT (not pricing tiers, editions, or bundles)

**URL ACCURACY IS CRITICAL:**
- **MANDATORY**: Include a VALID, CURRENT official product page URL as "source_url"
- Verify URLs are from web search citations, not fabricated
- Ensure URLs lead to actual product pages (not 404 or generic pages)
- Use the most official/current URL when multiple options exist
- Double-check URLs match the product name and are from the company's domain

**EXCLUDE:**
- Programming languages (Java, Python, etc.) - not products sold to businesses
- Pure developer tools (unless standalone commercial products)
- APIs/SDKs (unless standalone products)
- Marketplaces/platforms (unless core products)
- Professional services (consulting, training)
- Built-in features (not standalone products)
- Pricing tiers presented as separate products
- Mobile apps (iOS/Android) listed as separate products

**AVOID OUTDATED/INVALID URLs:**
- ❌ DO NOT use URLs that return 404 errors
- ❌ DO NOT fabricate or guess URL patterns
- ❌ DO NOT use outdated URLs from old web pages
- ✅ USE URLs directly from current web search results
- ✅ USE URLs from the company's official product catalog pages
- ✅ VERIFY URLs match the actual product being described

**CRITICAL: You MUST return valid JSON in the exact format specified above.**
- Even if web search results are not ideal, use your knowledge of the company to generate a product catalog
- If search results are about product management features (not the company's products), use your general knowledge
- Always return valid JSON - never return explanatory text or error messages
- The response must start with {{ and end with }}

Return ONLY valid JSON matching the schema above. 

**FINAL REQUIREMENTS:**
- Each product MUST include a "source_url" field with a VALID, CURRENT official product page URL
- Generate a COMPREHENSIVE list covering ALL products the company actually offers
- Do not artificially limit the count - list as many real standalone products as exist
- Verify all URLs are accurate and lead to actual product pages
"""
    
    async def generate(self, company_name: str, context: str, **kwargs) -> Dict:
        """Main generation method - uses Perplexity web search instead of context"""
        import time
        start_time = time.time()
        
        try:
            # For products, we don't use context - let Perplexity search the web
            prompt = self.build_prompt(company_name, "", **kwargs)
            system_message = self.get_system_message()
            
            # Use Perplexity for web search
            response = await self.llm_service.generate_async(
                prompt=prompt,
                system_message=system_message,
                temperature=1.0,
                max_completion_tokens=10000,
                provider="perplexity"  # Use Perplexity for web search
            )
            
            # Parse response and match citations to products
            parsed_result = self.parse_response(response.content, response.citations)
            parsed_result["model"] = response.model
            
            # Add token usage and timing information
            parsed_result["usage"] = {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens
            }
            parsed_result["generation_time_seconds"] = time.time() - start_time
            
            # Validate product URLs (warn about invalid/hallucinated URLs)
            if parsed_result.get("products"):
                await self._validate_product_urls(parsed_result["products"])
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise
    
    def parse_response(self, response: str, citations: list = None) -> Dict:
        """
        Parse and validate LLM response for product catalog generation.
        Also handles source_url matching from citations if not provided in JSON.
        """
        try:
            logger.debug(f"RAW LLM RESPONSE: {response[:2000]}")
            
            # Clean markdown code block markers
            cleaned_response = response.strip()
            
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            
            # Check if response is empty or not JSON-like
            if not cleaned_response or not cleaned_response.strip():
                logger.error("LLM returned empty response")
                raise ValueError("LLM returned empty response. Please try again.")
            
            # Check if response looks like JSON (starts with {)
            if not cleaned_response.strip().startswith('{'):
                logger.error(f"LLM response is not JSON format. First 500 chars: {cleaned_response[:500]}")
                # Try to extract JSON from the response if it's embedded in text
                import re
                json_match = re.search(r'\{[\s\S]*"products"[\s\S]*\}', cleaned_response)
                if json_match:
                    logger.info("Found JSON embedded in text, extracting...")
                    cleaned_response = json_match.group(0)
                else:
                    raise ValueError(
                        f"LLM did not return valid JSON. Response appears to be text explanation. "
                        f"Please ensure the prompt explicitly requires JSON output. "
                        f"Response preview: {cleaned_response[:200]}..."
                    )
            
            # Parse JSON
            try:
                data = json.loads(cleaned_response)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parsing failed at position {json_err.pos}: {json_err.msg}")
                logger.error(f"Problematic section: {cleaned_response[max(0, json_err.pos-100):json_err.pos+100]}")
                raise ValueError(
                    f"Invalid JSON format in LLM response. "
                    f"Error: {json_err.msg} at position {json_err.pos}. "
                    f"Please ensure the prompt explicitly requires valid JSON output."
                )
            
            # Validate structure
            if "products" not in data:
                raise ValueError("Response missing 'products' key")
            
            products = data["products"]
            
            if not isinstance(products, list) or len(products) == 0:
                raise ValueError("'products' must be a non-empty array")
            
            logger.info(f"Generated {len(products)} products from web search")
            
            # Extract citation URLs for fallback matching
            citation_urls = []
            if citations:
                citation_urls = [c.get("url", "") for c in citations if c.get("url")]
                logger.debug(f"Available citation URLs: {len(citation_urls)}")
            
            # Validate each product and ensure source_url is present
            for i, product in enumerate(products):
                logger.debug(f"Validating product {i}: {product.get('product_name', 'Unknown')}")
                
                # Validate required fields
                if "product_name" not in product or not product["product_name"]:
                    raise ValueError(f"Product {i} missing 'product_name'")
                
                if "description" not in product or not product["description"]:
                    raise ValueError(f"Product {i} missing 'description'")
                
                # Validate product_name
                if len(product["product_name"].strip()) < 2:
                    raise ValueError(f"Product {i} name too short: '{product['product_name']}'")
                
                # Ensure source_url is present
                if not product.get("source_url"):
                    # Try to match from citations
                    product_name_lower = product["product_name"].lower()
                    matched_url = self._match_url_from_citations(product_name_lower, citation_urls)
                    if matched_url:
                        product["source_url"] = matched_url
                        logger.info(f"Matched source_url for '{product['product_name']}': {matched_url}")
                    else:
                        logger.warning(f"Product '{product['product_name']}' has no source_url and no matching citation found")
                
                # Validate description length
                desc_len = len(product["description"])
                if desc_len < 50:
                    logger.warning(
                        f"Product {i} '{product['product_name']}' has short description: {desc_len} chars. "
                        f"Recommend 150-300 chars for better context."
                    )
                elif desc_len > 500:
                    logger.warning(
                        f"Product {i} '{product['product_name']}' has long description: {desc_len} chars. "
                        f"Recommend 150-300 chars for conciseness."
                    )
                
                logger.info(
                    f"Product {i} validated: '{product['product_name']}' "
                    f"({desc_len} chars, source_url: {bool(product.get('source_url'))})"
                )
            
            logger.info(f"Successfully validated {len(products)} products")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse product JSON: {e}")
            logger.error(f"Raw response: {response[:500]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        
        except ValueError as e:
            logger.error(f"Product validation failed: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error parsing product response: {e}")
            raise ValueError(f"Failed to parse product response: {e}")
    
    def _match_url_from_citations(self, product_name: str, citation_urls: list) -> str:
        """
        Try to match a product name to a citation URL.
        Returns the first URL that contains keywords from the product name.
        """
        if not citation_urls:
            return None
        
        # Extract keywords from product name
        keywords = [word.lower() for word in product_name.split() if len(word) > 3]
        
        # Try to find a URL that contains product name keywords
        for url in citation_urls:
            url_lower = url.lower()
            # Check if URL contains any product name keywords
            if any(keyword in url_lower for keyword in keywords):
                return url
        
        # Fallback: return first citation URL if no match found
        return citation_urls[0] if citation_urls else None
    
    async def _validate_url(self, url: str, timeout: float = 5.0) -> Tuple[bool, int]:
        """
        Validate if a URL is reachable.
        
        Returns:
            Tuple: (is_valid, status_code) where is_valid is True if URL returns 2xx or 3xx status
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                response = await client.head(url)
                is_valid = response.status_code < 400
                return (is_valid, response.status_code)
        except httpx.TimeoutException:
            logger.warning(f"URL validation timeout for: {url}")
            return (False, 0)
        except Exception as e:
            logger.debug(f"URL validation failed for {url}: {str(e)}")
            return (False, 0)
    
    async def _validate_product_urls(self, products: list) -> None:
        """
        Validate all product URLs and log warnings for invalid ones.
        """
        logger.info(f"Validating {len(products)} product URLs...")
        
        validation_tasks = []
        for product in products:
            if product.get("source_url"):
                validation_tasks.append(self._validate_url(product["source_url"]))
            else:
                validation_tasks.append(asyncio.create_task(asyncio.sleep(0, result=(False, 0))))
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        invalid_count = 0
        for i, (product, result) in enumerate(zip(products, results)):
            if isinstance(result, Exception):
                logger.warning(f"⚠️  Product '{product['product_name']}': URL validation error - {str(result)}")
                invalid_count += 1
            elif result:
                is_valid, status_code = result
                if not is_valid:
                    logger.warning(
                        f"⚠️  Product '{product['product_name']}': Invalid URL (status {status_code}) - "
                        f"{product.get('source_url', 'N/A')}"
                    )
                    invalid_count += 1
                else:
                    logger.debug(f"✓ Product '{product['product_name']}': URL valid (status {status_code})")
        
        if invalid_count > 0:
            logger.warning(
                f"⚠️  {invalid_count}/{len(products)} product URLs are invalid or unreachable. "
                f"This likely means the AI hallucinated URLs. Consider manually verifying URLs."
            )
        else:
            logger.info(f"✓ All {len(products)} product URLs are valid")

