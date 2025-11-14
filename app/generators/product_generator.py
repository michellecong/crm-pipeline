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
    Generates seller company's complete product catalog from web content.
    
    Analyzes company data to identify all products/services with 
    clear descriptions focused on value propositions and use cases.
    """
    
    def get_system_message(self) -> str:
        return """You are an expert B2B product marketing analyst specializing in product positioning and value proposition development.

Your task is to analyze a seller company's web content and extract their CORE COMMERCIAL PRODUCTS with clear, buyer-focused descriptions.

Your analysis should:
- Identify distinct core products that customers purchase
- Focus on standalone commercial offerings with dedicated pricing
- Write compelling descriptions that explain value and use cases
- Use buyer-friendly language (not technical jargon)
- Exclude developer tools, APIs, marketplaces, services, and built-in features
"""

    def build_prompt(self, company_name: str, context: str, **kwargs) -> str:
        
        return f"""## TASK

Analyze the seller company's web content and extract their CORE COMMERCIAL PRODUCT CATALOG.

Generate purchasable core products with clear, buyer-focused descriptions. Exclude APIs, developer tools, marketplaces, services, and built-in features.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **Product Focus**: Extract ONLY core commercial products
   - Include distinct product lines that customers purchase
   - Focus on standalone offerings with dedicated pricing
   - Exclude APIs, SDKs, marketplaces, services, developer tools, and built-in features
   - Each product should be purchasable independently

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
✓ ONLY core commercial products included (no APIs, SDKs, marketplaces, services)
✓ Each product is purchasable independently with dedicated pricing
✓ Official product names used (from website)
✓ Each description is 2-4 sentences (150-300 characters)
✓ Descriptions focus on value and use cases (not features)
✓ Buyer-friendly language (no technical jargon)
✓ Each product is distinct (not pricing tiers, bundles, or add-ons)
✓ No developer tools, services, or built-in features included

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOW GENERATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SELLER COMPANY]
Company Name: {company_name}

[WEB CONTENT]
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyze the web content above and generate the complete product catalog.

CRITICAL REMINDERS:
- Extract ONLY core commercial products (exclude APIs, SDKs, marketplaces, services, developer tools, features)
- Focus on standalone purchasable products with dedicated pricing
- Use official product names from the website
- Write 2-4 sentence descriptions focused on VALUE and USE CASES
- Use buyer-friendly language (avoid technical jargon)
- Each product must be DISTINCT (not pricing tiers or bundles)
- Apply the exclusion criteria rigorously

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
            
            logger.info(f"Generated {len(products)} products from company content")
            
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

