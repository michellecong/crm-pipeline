# services/content_processor.py
"""
Content processing service for cleaning and extracting useful information from scraped content
"""
import re
from typing import Dict, List
from ..services.llm_service import get_llm_service
import logging

logger = logging.getLogger(__name__)


class ContentProcessor:
    """
    Content processor - responsible for cleaning and preprocessing scraped content for B2B persona building
    
    Main functions:
    1. Rule-based cleaning: Remove useless information (image links, navigation, ads, etc.)
    2. Batch LLM processing: Extract customer persona information using focused 6-category framework
    3. Smart truncation: Control content length while preserving important information
    
    Persona extraction categories:
    1. Current Customers & Target Market (customer names, industries, sizes, markets)
    2. Products & Services (descriptions, features, value proposition, use cases)
    3. Customer Success Stories & Use Cases (testimonials, outcomes, roles)
    4. Customer Pain Points & Needs (problems, requirements, challenges, goals)
    5. Company Profile & Market Position (size, revenue, partnerships, awards)
    6. Decision Makers & Key Personnel (executives, titles, backgrounds)
    
    Anti-hallucination measures:
    - 7 critical anti-hallucination rules in system prompt
    - Mandatory source citations for all facts
    - Explicit "Not mentioned" for missing information
    - Clear boundaries on what to extract
    - Structured output format with validation checklist
    
    Recommended to use batch_process_content() method for batch processing, more efficient.
    """

    def __init__(self):
        self.llm_service = get_llm_service()

        # Define cleanup rules
        self.cleanup_patterns = [
            # Remove image links and alt text
            r'!\[.*?\]\([^)]+\)',
            # Remove duplicate line breaks
            r'\n{3,}',
            # Remove URL parameters
            r'\([^)]*\?[^)]*\)',
            # Remove technical error messages
            r'You have been blocked.*',
            # Remove navigation elements
            r'\[Skip to main content\].*?\n',
            # Remove loading and error messages
            r'Loading\.\.\..*',
            r'Load More Articles.*',
            # Remove subscription and ad content
            r'Subscribe today for only.*',
            r'CTA:SUBSCRIBE.*',
            # Remove duplicate link text
            r'\[View all\].*?\n',
            # Remove empty links
            r'\[.*?\]\(\)',
        ]

        # Define important patterns to keep (sales-related)
        self.important_patterns = [
            # Executives and decision makers
            r'.*CEO.*',
            r'.*CTO.*',
            r'.*CFO.*',
            r'.*VP.*',
            r'.*Director.*',
            r'.*Manager.*',
            r'.*Head of.*',
            r'.*Chief.*',
            # Business partnerships and development
            r'.*partnership.*',
            r'.*collaboration.*',
            r'.*acquisition.*',
            r'.*merger.*',
            r'.*investment.*',
            r'.*funding.*',
            # Financial and scale
            r'.*revenue.*',
            r'.*valuation.*',
            r'.*million.*',
            r'.*billion.*',
            r'.*employees.*',
            r'.*customers.*',
            r'.*users.*',
            r'.*market.*',
            # Pain points and challenges
            r'.*challenge.*',
            r'.*problem.*',
            r'.*issue.*',
            r'.*difficulty.*',
            r'.*struggle.*',
            r'.*pain point.*',
            # Needs and opportunities
            r'.*need.*',
            r'.*requirement.*',
            r'.*opportunity.*',
            r'.*growth.*',
            r'.*expansion.*',
            r'.*scaling.*',
            # Technology and digitalization
            r'.*digital.*',
            r'.*technology.*',
            r'.*innovation.*',
            r'.*transformation.*',
            r'.*upgrade.*',
            r'.*modernization.*',
            # Policies and compliance
            r'.*policy.*',
            r'.*regulation.*',
            r'.*compliance.*',
            r'.*standard.*',
            r'.*requirement.*',
            # Competition and market
            r'.*competitor.*',
            r'.*competition.*',
            r'.*market share.*',
            r'.*position.*',
            r'.*advantage.*',
            # Budget and procurement
            r'.*budget.*',
            r'.*procurement.*',
            r'.*purchase.*',
            r'.*vendor.*',
            r'.*supplier.*',
            # Success cases
            r'.*success.*',
            r'.*case study.*',
            r'.*achievement.*',
            r'.*milestone.*',
            # Industry trends
            r'.*trend.*',
            r'.*future.*',
            r'.*emerging.*',
            r'.*disruption.*',
        ]

    def clean_markdown(self, markdown: str) -> str:
        """
        Rule-based simple cleaning

        Args:
            markdown: Original markdown content

        Returns:
            Cleaned content
        """
        if not markdown:
            return ""

        logger.debug(f"Cleaning markdown content, original length: {len(markdown)}")

        # Apply cleanup rules
        cleaned = markdown
        for pattern in self.cleanup_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Remove extra blank lines
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)

        # Remove leading and trailing whitespace
        lines = [line.strip() for line in cleaned.split('\n')]
        cleaned = '\n'.join(line for line in lines if line)

        logger.debug(f"Cleaned markdown length: {len(cleaned)}")
        return cleaned.strip()

    def extract_important_content(self, content: str) -> str:
        """
        Extract important content

        Args:
            content: Cleaned content

        Returns:
            Important content summary
        """
        if not content:
            return ""

        important_lines = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if contains important patterns
            for pattern in self.important_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    important_lines.append(line)
                    break

        return '\n'.join(important_lines)

    def truncate_content(self, content: str, max_chars: int = 5000) -> str:
        """
        Smart content truncation

        Args:
            content: Content to truncate
            max_chars: Maximum character count

        Returns:
            Truncated content
        """
        if len(content) <= max_chars:
            return content

        logger.debug(f"Truncating content from {len(content)} to {max_chars} chars")

        # Truncate by paragraphs, maintaining integrity
        paragraphs = content.split('\n\n')
        result = []
        char_count = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if char_count + len(para) + 2 > max_chars:  # +2 for \n\n
                break
            result.append(para)
            char_count += len(para) + 2

        truncated = '\n\n'.join(result)
        logger.debug(f"Truncated content length: {len(truncated)}")
        return truncated



    async def batch_process_content(self, content_batch: List[Dict], 
                                   company_name: str) -> List[Dict]:
        """
        Batch process multiple content items for customer persona building (main processing method)
        
        This is the recommended content processing method, significantly improving efficiency through batch LLM calls:
        - 1 LLM call processes multiple content items
        - Focused 6-category persona extraction framework
        - Strong anti-hallucination measures (7 rules, citation requirements)
        - Significantly reduces API call costs
        
        Extracts:
        1. Current Customers & Target Market (customer names, industries, sizes, markets)
        2. Products & Services (descriptions, features, value proposition)
        3. Customer Success Stories & Use Cases (testimonials, outcomes, roles)
        4. Customer Pain Points & Needs (problems, requirements, challenges)
        5. Company Profile & Market Position (size, revenue, partnerships, awards)
        6. Decision Makers & Key Personnel (executives, titles, backgrounds)
        
        Args:
            content_batch: Content batch list, each element contains 
                          {'item': item, 'content': str, 'type': str}
            company_name: Company name
            
        Returns:
            Processed content list, each element contains processed persona content and statistics
        """
        if not content_batch:
            return []
        
        logger.info(f"Batch processing {len(content_batch)} content items "
                    f"for {company_name}")
        
        # Combine all content into one large prompt
        combined_content = []
        content_mapping = {}  # Used to track each content item
        
        for i, batch_item in enumerate(content_batch):
            content = batch_item['content']
            content_type = batch_item['type']
            url = batch_item['item']['url']
            
            # First perform rule-based cleaning
            cleaned_content = self.clean_markdown(content)
            if cleaned_content:
                combined_content.append(
                    f"--- Content {i+1} ({content_type}) ---\n"
                    f"URL: {url}\n{cleaned_content}"
                )
                content_mapping[i] = {
                    'url': url,
                    'type': content_type,
                    'original_length': len(content),
                    'cleaned_length': len(cleaned_content)
                }
        
        if not combined_content:
            return []
        
        # Combine all content
        full_content = "\n\n".join(combined_content)
        
        # Use LLM for batch processing
        try:
            processed_result = await self._batch_extract_with_llm(full_content, company_name, content_mapping)
            return processed_result
            
        except Exception as e:
            logger.error(f"Batch LLM processing failed: {str(e)}")
            # Fallback to rule-based cleaning
            return [
                {
                    'url': batch_item['item']['url'],
                    'processed_content': self.clean_markdown(batch_item['content']),
                    'type': batch_item['type']
                }
                for batch_item in content_batch
            ]
    
    async def _batch_extract_with_llm(self, combined_content: str, 
                                     company_name: str, 
                                     content_mapping: Dict) -> List[Dict]:
        """
        Use LLM batch extraction focused on customer persona building.
        
        Anti-hallucination measures implemented:
        - 7 critical anti-hallucination rules in system prompt
        - Explicit "Not mentioned" requirements for all missing data
        - Mandatory source citation requirements for all facts
        - Focused 6-category persona framework (vs. original 14)
        - Clear boundary instructions and validation checklist
        - Structured output format with separator markers
        
        Note: Uses default temperature (1.0) as required by gpt-5-mini model.
        Hallucination control achieved through strong prompt engineering.
        """
        system_message = """You are a B2B customer persona analyst specializing in extracting ONLY factual information from source documents.

CRITICAL ANTI-HALLUCINATION RULES (YOU MUST FOLLOW THESE):
1. Extract ONLY information explicitly stated in the source text
2. For each fact, include a direct quote or paraphrase from the source
3. If information is not present in the text, you MUST write "Not mentioned"
4. NEVER infer, assume, or generate information not in the source
5. NEVER make up customer names, statistics, or quotes
6. If you're uncertain about any information, mark it as "Uncertain: [your note]"
7. Distinguish between what customers say vs. what the company claims

PRIMARY GOAL: Extract factual intelligence to build accurate B2B customer personas.

EXTRACTION FRAMEWORK (6 Categories):

1. CURRENT CUSTOMERS & TARGET MARKET
   - Specific customer company names explicitly mentioned
   - Industries and verticals served
   - Company sizes (Enterprise/Mid-market/SMB)
   - Geographic markets served
   - Customer statistics and metrics
   - Job roles of people at customer companies

2. PRODUCTS & SERVICES
   - Main products/services and their descriptions
   - Key features and capabilities
   - Product positioning and value proposition
   - Use cases and applications
   - How the product/service works

3. CUSTOMER SUCCESS STORIES & USE CASES
   - Customer testimonials and case studies
   - Specific use cases and outcomes
   - Problems solved for customers
   - Results and metrics achieved
   - Who at the customer company uses the product (roles/departments)

4. CUSTOMER PAIN POINTS & NEEDS
   - Problems customers face (as mentioned in content)
   - Customer needs and requirements
   - Challenges the product addresses
   - Customer goals and objectives

5. COMPANY PROFILE & MARKET POSITION
   - Company size, revenue, employee count
   - Market position and competitive advantages
   - Key partnerships and integrations
   - Industry recognition and awards
   - Company history and milestones

6. DECISION MAKERS & KEY PERSONNEL
   - Executive team (names, titles)
   - Key spokespeople and their backgrounds
   - Leadership changes or announcements
   - Relevant for understanding company direction

VERIFICATION CHECKLIST before you output:
✓ Every fact has a source quote or paraphrase
✓ No information is inferred or assumed
✓ Missing information is marked "Not mentioned"
✓ Uncertain information is flagged
✓ Customer quotes are in quotation marks"""

        # Build prompt with focused 5-category persona framework
        prompt_parts = [f"""Analyze the following web content about {company_name} and extract customer persona information for B2B sales intelligence.

SOURCE CONTENT:
{combined_content}

INSTRUCTIONS:
Extract the 6 categories below for each content item separately. Be precise, factual, and include source quotes.
"""]

        # Add extraction template for each content item
        for i in range(len(content_mapping)):
            mapping = content_mapping[i]
            prompt_parts.append(f"""

═══════════════════════════════════════════════════════════
**CONTENT ITEM {i+1}** ({mapping['type']})
URL: {mapping['url']}
═══════════════════════════════════════════════════════════

1. **CURRENT CUSTOMERS & TARGET MARKET**
   Extract ONLY if explicitly mentioned:
   • Customer company names: [list with source quotes]
   • Industries and company sizes: [with source quotes]
   • Geographic markets: [regions with source quotes]
   • Job roles at customer companies: [titles with source quotes]
   • Customer statistics: [e.g., "85% of Fortune 100" with source quote]
   
   If no information found, write: "Not mentioned"

2. **PRODUCTS & SERVICES**
   Extract ONLY if explicitly mentioned:
   • Main products/services: [descriptions with source quotes]
   • Key features and capabilities: [with source quotes]
   • Product positioning and value proposition: [with source quotes]
   • Use cases and applications: [with source quotes]
   
   If no information found, write: "Not mentioned"

3. **CUSTOMER SUCCESS STORIES & USE CASES**
   Extract ONLY if explicitly mentioned:
   • Customer testimonials and case studies: [with exact quotes and attribution]
   • Specific use cases and outcomes: [with source quotes]
   • Problems solved for customers: [with source quotes]
   • Results and metrics achieved: [specific numbers with source quotes]
   • User roles at customer companies: [titles/departments with source quotes]
   
   If no information found, write: "Not mentioned"

4. **CUSTOMER PAIN POINTS & NEEDS**
   Extract ONLY if explicitly mentioned:
   • Problems customers face: [as mentioned in content with quotes]
   • Customer needs and requirements: [with source quotes]
   • Challenges the product addresses: [with source quotes]
   • Customer goals and objectives: [with source quotes]
   
   If no information found, write: "Not mentioned"

5. **COMPANY PROFILE & MARKET POSITION**
   Extract ONLY if explicitly mentioned:
   • Company size, revenue, employee count: [with source quotes]
   • Market position and competitive advantages: [with source quotes]
   • Key partnerships and integrations: [with source quotes]
   • Industry recognition and awards: [with source quotes]
   
   If no information found, write: "Not mentioned"

6. **DECISION MAKERS & KEY PERSONNEL**
   Extract ONLY if explicitly mentioned:
   • Executive team names and titles: [with source quotes]
   • Key spokespeople and their backgrounds: [with source quotes]
   • Leadership changes or announcements: [with source quotes]
   
   If no information found, write: "Not mentioned"
""")

        prompt_parts.append("""

═══════════════════════════════════════════════════════════
FINAL REMINDERS BEFORE YOU RESPOND:
═══════════════════════════════════════════════════════════
✓ Extract information SEPARATELY for each content item in the order shown above
✓ Include direct quotes (in "quotation marks") for every fact
✓ Write "Not mentioned" for any category with no information in that content item
✓ Do NOT infer or generate information not explicitly in the source
✓ Do NOT mix information between different content items
✓ Do NOT make up company names, statistics, or quotes
✓ If uncertain about anything, mark it: "Uncertain: [explain why]"

Now extract the persona information:
""")

        prompt = "".join(prompt_parts)

        try:
            response = await self.llm_service.generate_async(
                prompt=prompt,
                system_message=system_message,
                max_completion_tokens=15000  # Adjusted for 6 categories (vs original 14)
                # Using default temperature (1.0) as required by gpt-5-mini
                # Hallucination control relies on strong prompt engineering:
                # - 7 anti-hallucination rules in system message
                # - Mandatory source citations
                # - "Not mentioned" requirements
                # - Structured output format with validation checklist
            )
            
            extracted_content = response.content.strip()
            logger.info(f"Batch LLM persona extraction completed, extracted length: {len(extracted_content)}")
            
            # Parse LLM output and assign to content items
            results = self._parse_batch_llm_output(extracted_content, content_mapping)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch LLM persona extraction failed: {str(e)}")
            raise e

    def _parse_batch_llm_output(self, llm_output: str, content_mapping: Dict) -> List[Dict]:
        """
        Parse LLM batch output, assign corresponding analysis results to each content item
        
        Args:
            llm_output: Raw LLM output
            content_mapping: Content item mapping
            
        Returns:
            Parsed result list
        """
        results = []
        
        # Try to split LLM output by content items
        content_sections = self._split_llm_output_by_content(llm_output, content_mapping)
        
        for i, mapping in content_mapping.items():
            if i < len(content_sections):
                # Use corresponding analysis results
                processed_content = content_sections[i]
            else:
                # If no corresponding analysis results, use general results
                processed_content = llm_output
            
            results.append({
                'url': mapping['url'],
                'processed_content': processed_content,
                'type': mapping['type']
            })
        
        return results
    
    def _split_llm_output_by_content(self, llm_output: str, content_mapping: Dict) -> List[str]:
        """
        Split LLM output by content items
        
        Args:
            llm_output: Raw LLM output
            content_mapping: Content item mapping
            
        Returns:
            Split content list
        """
        sections = []
        
        # Try to split by "Content Item X"
        import re
        pattern = r'\*\*Content Item \d+\s*\([^)]+\)\s*-\s*[^*]+\*\*:'
        matches = list(re.finditer(pattern, llm_output))
        
        if len(matches) >= len(content_mapping):
            # If enough split points found
            for i, match in enumerate(matches):
                start = match.end()
                if i + 1 < len(matches):
                    end = matches[i + 1].start()
                else:
                    end = len(llm_output)
                
                section_content = llm_output[start:end].strip()
                sections.append(section_content)
        else:
            # If splitting fails, for single content item return entire output directly
            if len(content_mapping) == 1:
                sections = [llm_output]
            else:
                # For multiple content items, try other methods
                sections = self._fallback_split(llm_output, len(content_mapping))
        
        return sections
    
    def _fallback_split(self, llm_output: str, num_sections: int) -> List[str]:
        """
        Fallback splitting method
        
        Args:
            llm_output: Raw LLM output
            num_sections: Required number of sections
            
        Returns:
            Split content list
        """
        if num_sections <= 1:
            return [llm_output]
        
        # Split by paragraphs
        paragraphs = llm_output.split('\n\n')
        
        if len(paragraphs) >= num_sections:
            # Distribute paragraphs evenly
            section_size = len(paragraphs) // num_sections
            sections = []
            
            for i in range(num_sections):
                start = i * section_size
                if i == num_sections - 1:
                    # Last section contains all remaining paragraphs
                    end = len(paragraphs)
                else:
                    end = (i + 1) * section_size
                
                section_content = '\n\n'.join(paragraphs[start:end])
                sections.append(section_content)
            
            return sections
        else:
            # If not enough paragraphs, use complete output for each content item
            return [llm_output] * num_sections

    def get_processing_stats(self, original_content: str, processed_content: str) -> Dict:
        """
        Get processing statistics

        Args:
            original_content: Original content
            processed_content: Processed content

        Returns:
            Statistics dictionary
        """
        return {
            "original_length": len(original_content),
            "processed_length": len(processed_content),
            "compression_ratio": (
                len(processed_content) / len(original_content)
                if original_content else 0
            ),
            "reduction_percentage": (
                (1 - len(processed_content) / len(original_content)) * 100
                if original_content else 0
            )
        }


# Singleton instance
_content_processor = None


def get_content_processor() -> ContentProcessor:
    """Get or create ContentProcessor singleton"""
    global _content_processor
    if _content_processor is None:
        _content_processor = ContentProcessor()
    return _content_processor