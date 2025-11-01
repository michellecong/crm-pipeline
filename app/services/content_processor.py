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
    Content processor - responsible for cleaning and preprocessing scraped content
    
    Main functions:
    1. Rule-based cleaning: Remove useless information (image links, navigation, ads, etc.)
    2. Batch LLM processing: Process multiple content items at once, extract key information
    3. Smart truncation: Control content length while preserving important information
    
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
        Batch process multiple content items (main processing method)
        
        This is the recommended content processing method, significantly improving efficiency through batch LLM calls:
        - 1 LLM call processes multiple content items
        - Unified sales analysis framework
        - Significantly reduces API call costs
        
        Args:
            content_batch: Content batch list, each element contains 
                          {'item': item, 'content': str, 'type': str}
            company_name: Company name
            
        Returns:
            Processed content list, each element contains processed content and statistics
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
        """Use LLM batch extraction (main processing method)"""
        system_message = """You are a professional B2B sales intelligence analyst, skilled at extracting the most valuable information for sales teams from web content.

Your tasks:
1. Extract company basic information (mission, vision, products, services, business model)
2. Identify personnel information (executive names, positions, departments, decision makers, key contacts)
3. Extract business information (partners, business development, financial data, company size, market position)
4. Identify technology direction and industry trends
5. Analyze company pain points and challenges
6. Identify business needs and opportunities
7. Discover problems and difficulties faced by the company
8. Understand company development changes and transformation
9. Pay attention to new policies and regulatory impacts
10. Identify competitive landscape and market position
11. Analyze customer success stories and failure lessons
12. Understand budget cycles and procurement processes
13. Identify technology upgrades and digital transformation needs
14. Analyze industry regulations and compliance requirements

Requirements:
- Remove all useless information (image links, navigation, ads, duplicate content, technical error messages)
- Maintain accuracy and completeness of information
- Return concise, structured text with significant content compression
- Focus on information most valuable for B2B sales and business development
- Pay special attention to information that helps salespeople understand customer pain points and needs
- For technical documents, extract core functions, APIs, product features and other key information
- Remove redundant technical details, duplicate links, navigation elements
- Compression ratio target: reduce content length by at least 30%
- Extract information for each content item separately, maintaining clear structure"""

        # Dynamically build prompt
        prompt_parts = [f"""Please extract the most valuable information for sales analysis from the following multiple content sources about {company_name}:

{combined_content}

Please extract the following key information for each content item separately and output in the order of content items:"""]

        # Add analysis framework for each content item
        for i in range(len(content_mapping)):
            mapping = content_mapping[i]
            prompt_parts.append(f"""
**Content Item {i+1} ({mapping['type']}) - {mapping['url']}:**
1. **Company Basic Information**: Mission, vision, main products and services, business model
2. **Personnel Information**: Executive names, positions, departments, decision makers, key contacts
3. **Business Information**: Partners, business development, financial data, company size, market position
4. **Technology Direction**: Technology focus, R&D direction, industry trends, tech stack
5. **Pain Points and Challenges**: Main problems faced by the company, business pain points, technical challenges
6. **Business Needs**: Business growth needs, efficiency improvement needs, cost control needs
7. **Development Changes**: Company transformation, business expansion, strategic adjustments, organizational changes
8. **Policy Impact**: New policies, regulatory changes, compliance requirements, industry standards
9. **Competitive Landscape**: Competitors, market positioning, competitive advantages, threats
10. **Success Cases**: Customer cases, project achievements, business accomplishments
11. **Budget and Procurement**: Budget cycles, procurement processes, decision processes, supplier relationships
12. **Digital Transformation**: Digital needs, technology upgrades, system integration needs
13. **Industry Regulation**: Regulatory requirements, compliance challenges, industry standard changes
14. **Market Opportunities**: Emerging markets, business opportunities, partnership opportunities""")

        prompt_parts.append("""
Requirements:
- Remove image links, navigation elements, duplicate content, ads
- Maintain information accuracy and completeness
- Return structured text for easy use by sales teams
- Focus on information that helps understand customer pain points and needs
- Pay special attention to sales opportunities and business development potential
- Strictly output analysis results separately in the order of content items

Extracted key information:""")

        prompt = "".join(prompt_parts)

        try:
            response = await self.llm_service.generate_async(
                prompt=prompt,
                system_message=system_message,
                max_completion_tokens=15000,
                temperature=1
            )
            
            extracted_content = response.content.strip()
            logger.info(f"Batch LLM extraction completed, extracted length: {len(extracted_content)}")
            
            # Parse LLM output, assign corresponding analysis results to each content item
            results = self._parse_batch_llm_output(extracted_content, content_mapping)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch LLM extraction failed: {str(e)}")
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