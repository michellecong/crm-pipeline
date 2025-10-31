# generators/product_generator.py
"""
Product catalog generator for extracting seller company's products/services
"""
from .base_generator import BaseGenerator
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)


class ProductGenerator(BaseGenerator):
    """
    Generates seller company's product catalog from web content.
    
    Analyzes company data to identify core products/services with 
    clear descriptions focused on value propositions and use cases.
    """
    
    def get_system_message(self) -> str:
        return """You are an expert B2B product marketing analyst specializing in product positioning and value proposition development.

Your task is to analyze a seller company's web content and extract their product catalog with clear, buyer-focused descriptions.

CRITICAL: Focus on CORE products/services (not every minor feature or add-on).

Your analysis should:
- Identify distinct products/services (3-10 core offerings)
- Write compelling descriptions that explain value and use cases
- Use buyer-friendly language (not technical jargon)
- Capture what makes each product valuable to customers
"""

    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        
        max_products = kwargs.get('max_products', 10)
        
        return f"""## TASK

Analyze the seller company's web content and extract their product catalog.

Generate {max_products} or fewer core products with clear, buyer-focused descriptions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **Product Count**: 3-{max_products} CORE products only
   - Focus on distinct product lines (not sub-editions or add-ons)
   - Group related features into logical products
   - Avoid listing every minor feature as a separate product

2. **Product Naming**: Use official product names from the website
   - ✓ "Sales Cloud" (official name)
   - ✗ "CRM System" (generic description)

3. **Description Requirements**:
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
OUTPUT JSON SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "products": [
    {{
      "product_name": "string (official product name)",
      "description": "string (2-4 sentences, 150-300 chars, value-focused)"
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
      "description": "Complete CRM platform for managing sales pipelines, forecasting revenue, and automating sales processes. Helps sales teams close deals faster with AI-powered insights, workflow automation, and mobile access. Scales from small teams to global enterprises with customizable features and deep integration capabilities."
    }},
    {{
      "product_name": "Service Cloud",
      "description": "Customer service platform that unifies support channels, automates case routing, and provides agents with complete customer context. Enables support teams to resolve issues faster across email, phone, chat, and social media. Includes AI-powered chatbots, knowledge base management, and real-time analytics."
    }},
    {{
      "product_name": "Marketing Cloud",
      "description": "Marketing automation platform for creating personalized campaigns, nurturing leads, and measuring ROI across channels. Helps marketing teams generate qualified leads through email marketing, landing pages, social advertising, and analytics. Integrates with CRM for seamless lead handoff to sales."
    }},
    {{
      "product_name": "Commerce Cloud",
      "description": "E-commerce platform for creating unified shopping experiences across web, mobile, social, and in-store channels. Enables retailers to personalize customer journeys, manage product catalogs, process orders, and optimize conversions. Supports B2C and B2B commerce with AI-powered recommendations."
    }},
    {{
      "product_name": "Analytics Cloud (Tableau CRM)",
      "description": "Business intelligence and analytics platform that transforms data into actionable insights through interactive dashboards and AI-powered predictions. Helps business users explore data, identify trends, and make data-driven decisions without technical expertise. Integrates seamlessly with Salesforce and external data sources."
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before submitting, verify:
✓ 3-{max_products} products (core offerings only)
✓ Official product names used (from website)
✓ Each description is 2-4 sentences (150-300 characters)
✓ Descriptions focus on value and use cases (not features)
✓ Buyer-friendly language (no technical jargon)
✓ Each product is distinct (not pricing tiers or add-ons)
✓ generation_reasoning explains product selection logic

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOW GENERATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SELLER COMPANY]
Company Name: {company_name}

[WEB CONTENT]
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyze the web content above and generate the product catalog.

CRITICAL REMINDERS:
- Extract 3-{max_products} CORE products (not every feature)
- Use official product names from the website
- Write 2-4 sentence descriptions focused on VALUE and USE CASES
- Use buyer-friendly language (avoid technical jargon)
- Each product must be DISTINCT (not pricing tiers)

Return ONLY valid JSON matching the schema above.
"""
    
    def parse_response(self, response: str) -> Dict:
        """
        Parse and validate LLM response for product catalog generation.
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
            
            # Parse JSON
            data = json.loads(cleaned_response)
            
            # Validate structure
            if "products" not in data:
                raise ValueError("Response missing 'products' key")
            
            products = data["products"]
            
            if not isinstance(products, list) or len(products) == 0:
                raise ValueError("'products' must be a non-empty array")
            
            if len(products) > 15:
                logger.warning(f"Generated {len(products)} products. Recommend focusing on 3-10 core offerings.")
            
            # Validate each product
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
                    f"({desc_len} chars)"
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

