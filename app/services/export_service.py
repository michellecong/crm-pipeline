# services/export_service.py
"""
Export service for converting generated content to different formats (CSV, Markdown, JSON)
"""
import csv
import json
from typing import Dict, List, Optional, Literal
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting generated content in multiple formats"""
    
    @staticmethod
    def export_to_csv(data: Dict, output_path: str, content_type: str) -> str:
        """
        Export data to CSV format
        
        Args:
            data: Data dictionary containing generated content
            output_path: Path to save CSV file
            content_type: Type of content (personas, products, mappings, sequences, etc.)
            
        Returns:
            Path to saved CSV file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if content_type == "personas":
                    ExportService._export_personas_to_csv(data, f)
                elif content_type == "products":
                    ExportService._export_products_to_csv(data, f)
                elif content_type == "mappings":
                    ExportService._export_mappings_to_csv(data, f)
                elif content_type == "sequences" or content_type == "outreach":
                    ExportService._export_sequences_to_csv(data, f)
                elif content_type in ["two_stage", "three_stage", "pipeline"]:
                    ExportService._export_pipeline_to_csv(data, f)
                else:
                    raise ValueError(f"Unsupported content type for CSV export: {content_type}")
            
            logger.info(f"Exported {content_type} to CSV: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            raise
    
    @staticmethod
    def _export_personas_to_csv(data: Dict, file_handle):
        """Export personas to CSV format"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            personas = data["payload"].get("personas", [])
        else:
            result = data.get("result", {})
            personas = result.get("personas", [])
        
        if not personas:
            raise ValueError("No personas found in data")
        
        # Define CSV columns
        fieldnames = [
            "persona_name",
            "tier",
            "industry",
            "company_size_range",
            "company_type",
            "location",
            "job_titles",
            "excluded_job_titles",
            "description"
        ]
        
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        
        for persona in personas:
            job_titles = persona.get("job_titles", [])
            excluded_job_titles = persona.get("excluded_job_titles", [])
            
            writer.writerow({
                "persona_name": persona.get("persona_name", ""),
                "tier": persona.get("tier", ""),
                "industry": persona.get("industry", ""),
                "company_size_range": persona.get("company_size_range", ""),
                "company_type": persona.get("company_type", ""),
                "location": persona.get("location", ""),
                "job_titles": "; ".join(job_titles) if isinstance(job_titles, list) else str(job_titles),
                "excluded_job_titles": "; ".join(excluded_job_titles) if isinstance(excluded_job_titles, list) else str(excluded_job_titles) if excluded_job_titles else "",
                "description": persona.get("description", "")
            })
    
    @staticmethod
    def _export_products_to_csv(data: Dict, file_handle):
        """Export products to CSV format"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            products = data["payload"].get("products", [])
        else:
            result = data.get("result", {})
            products = result.get("products", [])
        
        if not products:
            raise ValueError("No products found in data")
        
        fieldnames = ["product_name", "description", "source_url"]
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        
        for product in products:
            writer.writerow({
                "product_name": product.get("product_name", ""),
                "description": product.get("description", ""),
                "source_url": product.get("source_url", "")
            })
    
    @staticmethod
    def _export_mappings_to_csv(data: Dict, file_handle):
        """Export mappings to CSV format"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            personas_with_mappings = data["payload"].get("personas_with_mappings", [])
        else:
            result = data.get("result", {})
            personas_with_mappings = result.get("personas_with_mappings", [])
        
        if not personas_with_mappings:
            raise ValueError("No mappings found in data")
        
        fieldnames = ["persona_name", "pain_point", "value_proposition"]
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        
        for persona_data in personas_with_mappings:
            persona_name = persona_data.get("persona_name", "")
            mappings = persona_data.get("mappings", [])
            
            for mapping in mappings:
                writer.writerow({
                    "persona_name": persona_name,
                    "pain_point": mapping.get("pain_point", ""),
                    "value_proposition": mapping.get("value_proposition", "")
                })
    
    @staticmethod
    def _export_sequences_to_csv(data: Dict, file_handle):
        """Export outreach sequences to CSV format"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            sequences = data["payload"].get("sequences", [])
        else:
            result = data.get("result", {})
            sequences = result.get("sequences", [])
        
        if not sequences:
            raise ValueError("No sequences found in data")
        
        fieldnames = [
            "sequence_name",
            "persona_name",
            "objective",
            "total_touches",
            "duration_days",
            "touch_order",
            "touch_type",
            "timing_days",
            "touch_objective",
            "subject_line",
            "content_suggestion",
            "hints"
        ]
        
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        
        for sequence in sequences:
            sequence_name = sequence.get("name", "")
            persona_name = sequence.get("persona_name", "")
            objective = sequence.get("objective", "")
            total_touches = sequence.get("total_touches", 0)
            duration_days = sequence.get("duration_days", 0)
            
            touches = sequence.get("touches", [])
            for touch in touches:
                writer.writerow({
                    "sequence_name": sequence_name,
                    "persona_name": persona_name,
                    "objective": objective,
                    "total_touches": total_touches,
                    "duration_days": duration_days,
                    "touch_order": touch.get("sort_order", ""),
                    "touch_type": touch.get("touch_type", ""),
                    "timing_days": touch.get("timing_days", ""),
                    "touch_objective": touch.get("objective", ""),
                    "subject_line": touch.get("subject_line", ""),
                    "content_suggestion": touch.get("content_suggestion", ""),
                    "hints": touch.get("hints", "")
                })
    
    @staticmethod
    def _export_pipeline_to_csv(data: Dict, file_handle):
        """Export full pipeline data to CSV (multiple sheets concept - flattened)"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            payload = data["payload"]
            products = payload.get("products", [])
            personas = payload.get("personas", [])
        else:
            result = data.get("result", {})
            products = result.get("products", [])
            personas = result.get("personas", [])
        
        # Export products
        if products:
            file_handle.write("=== PRODUCTS ===\n")
            product_writer = csv.DictWriter(file_handle, fieldnames=["product_name", "description", "source_url"])
            product_writer.writeheader()
            for product in products:
                product_writer.writerow({
                    "product_name": product.get("product_name", ""),
                    "description": product.get("description", ""),
                    "source_url": product.get("source_url", "")
                })
            file_handle.write("\n")
        
        # Export personas
        if personas:
            file_handle.write("=== PERSONAS ===\n")
            persona_writer = csv.DictWriter(
                file_handle,
                fieldnames=["persona_name", "tier", "industry", "location", "job_titles"]
            )
            persona_writer.writeheader()
            for persona in personas:
                job_titles = persona.get("job_titles", [])
                persona_writer.writerow({
                    "persona_name": persona.get("persona_name", ""),
                    "tier": persona.get("tier", ""),
                    "industry": persona.get("industry", ""),
                    "location": persona.get("location", ""),
                    "job_titles": "; ".join(job_titles) if isinstance(job_titles, list) else str(job_titles)
                })
            file_handle.write("\n")
    
    @staticmethod
    def export_to_markdown(data: Dict, output_path: str, content_type: str) -> str:
        """
        Export data to Markdown format
        
        Args:
            data: Data dictionary containing generated content
            output_path: Path to save Markdown file
            content_type: Type of content (personas, products, mappings, sequences, etc.)
            
        Returns:
            Path to saved Markdown file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write header
                company_name = data.get("company_name", "Unknown")
                generated_at = data.get("generated_at", datetime.now().isoformat())
                
                f.write(f"# {company_name} - {content_type.replace('_', ' ').title()}\n\n")
                f.write(f"**Generated at:** {generated_at}\n\n")
                f.write("---\n\n")
                
                # Write content based on type
                if content_type == "personas":
                    ExportService._export_personas_to_markdown(data, f)
                elif content_type == "products":
                    ExportService._export_products_to_markdown(data, f)
                elif content_type == "mappings":
                    ExportService._export_mappings_to_markdown(data, f)
                elif content_type == "sequences" or content_type == "outreach":
                    ExportService._export_sequences_to_markdown(data, f)
                elif content_type in ["two_stage", "three_stage", "pipeline"]:
                    ExportService._export_pipeline_to_markdown(data, f)
                else:
                    raise ValueError(f"Unsupported content type for Markdown export: {content_type}")
            
            logger.info(f"Exported {content_type} to Markdown: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Failed to export Markdown: {e}")
            raise
    
    @staticmethod
    def _export_personas_to_markdown(data: Dict, file_handle):
        """Export personas to Markdown format"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            personas = data["payload"].get("personas", [])
        else:
            result = data.get("result", {})
            personas = result.get("personas", [])
        
        if not personas:
            file_handle.write("No personas found.\n")
            return
        
        for i, persona in enumerate(personas, 1):
            file_handle.write(f"## Persona {i}: {persona.get('persona_name', 'Unknown')}\n\n")
            file_handle.write(f"**Tier:** {persona.get('tier', 'N/A')}\n\n")
            file_handle.write(f"**Industry:** {persona.get('industry', 'N/A')}\n\n")
            file_handle.write(f"**Company Size:** {persona.get('company_size_range', 'N/A')}\n\n")
            file_handle.write(f"**Location:** {persona.get('location', 'N/A')}\n\n")
            file_handle.write(f"**Company Type:** {persona.get('company_type', 'N/A')}\n\n")
            
            file_handle.write("### Target Job Titles\n\n")
            job_titles = persona.get("job_titles", [])
            if job_titles:
                for title in job_titles:
                    file_handle.write(f"- {title}\n")
            else:
                file_handle.write("- (No job titles specified)\n")
            file_handle.write("\n")
            
            file_handle.write("### Excluded Job Titles\n\n")
            excluded = persona.get("excluded_job_titles", [])
            if excluded:
                for title in excluded:
                    file_handle.write(f"- {title}\n")
            else:
                file_handle.write("- (No excluded titles specified)\n")
            file_handle.write("\n")
            
            file_handle.write("### Description\n\n")
            file_handle.write(f"{persona.get('description', 'N/A')}\n\n")
            file_handle.write("---\n\n")
    
    @staticmethod
    def _export_products_to_markdown(data: Dict, file_handle):
        """Export products to Markdown format"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            products = data["payload"].get("products", [])
        else:
            result = data.get("result", {})
            products = result.get("products", [])
        
        if not products:
            file_handle.write("No products found.\n")
            return
        
        for i, product in enumerate(products, 1):
            file_handle.write(f"## Product {i}: {product.get('product_name', 'Unknown')}\n\n")
            
            source_url = product.get("source_url")
            if source_url:
                file_handle.write(f"**Source:** [{source_url}]({source_url})\n\n")
            
            file_handle.write("### Description\n\n")
            file_handle.write(f"{product.get('description', 'N/A')}\n\n")
            file_handle.write("---\n\n")
    
    @staticmethod
    def _export_mappings_to_markdown(data: Dict, file_handle):
        """Export mappings to Markdown format"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            personas_with_mappings = data["payload"].get("personas_with_mappings", [])
        else:
            result = data.get("result", {})
            personas_with_mappings = result.get("personas_with_mappings", [])
        
        if not personas_with_mappings:
            file_handle.write("No mappings found.\n")
            return
        
        for persona_data in personas_with_mappings:
            persona_name = persona_data.get("persona_name", "Unknown")
            file_handle.write(f"## Persona: {persona_name}\n\n")
            
            mappings = persona_data.get("mappings", [])
            for i, mapping in enumerate(mappings, 1):
                file_handle.write(f"### Mapping {i}\n\n")
                file_handle.write(f"**Pain Point:**\n{mapping.get('pain_point', 'N/A')}\n\n")
                file_handle.write(f"**Value Proposition:**\n{mapping.get('value_proposition', 'N/A')}\n\n")
                file_handle.write("---\n\n")
    
    @staticmethod
    def _export_sequences_to_markdown(data: Dict, file_handle):
        """Export outreach sequences to Markdown format"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            sequences = data["payload"].get("sequences", [])
        else:
            result = data.get("result", {})
            sequences = result.get("sequences", [])
        
        if not sequences:
            file_handle.write("No sequences found.\n")
            return
        
        for sequence in sequences:
            file_handle.write(f"## {sequence.get('name', 'Unknown Sequence')}\n\n")
            file_handle.write(f"**Persona:** {sequence.get('persona_name', 'N/A')}\n\n")
            file_handle.write(f"**Objective:** {sequence.get('objective', 'N/A')}\n\n")
            file_handle.write(f"**Total Touches:** {sequence.get('total_touches', 0)}\n\n")
            file_handle.write(f"**Duration:** {sequence.get('duration_days', 0)} days\n\n")
            
            touches = sequence.get("touches", [])
            for touch in touches:
                file_handle.write(f"### Touch {touch.get('sort_order', '?')}: {touch.get('touch_type', 'unknown').title()}\n\n")
                file_handle.write(f"**Timing:** Day {touch.get('timing_days', 0)}\n\n")
                file_handle.write(f"**Objective:** {touch.get('objective', 'N/A')}\n\n")
                
                subject_line = touch.get("subject_line")
                if subject_line:
                    file_handle.write(f"**Subject Line:** {subject_line}\n\n")
                
                content = touch.get("content_suggestion")
                if content:
                    file_handle.write(f"**Content:**\n{content}\n\n")
                
                hints = touch.get("hints")
                if hints:
                    file_handle.write(f"**Hints:** {hints}\n\n")
                
                file_handle.write("---\n\n")
    
    @staticmethod
    def _export_pipeline_to_markdown(data: Dict, file_handle):
        """Export full pipeline data to Markdown"""
        # Support both frontend format (payload) and backend format (result)
        if "payload" in data:
            payload = data["payload"]
            products = payload.get("products", [])
            personas = payload.get("personas", [])
            mappings = payload.get("personas_with_mappings", [])
            sequences = payload.get("sequences", [])
        else:
            result = data.get("result", {})
            products = result.get("products", [])
            personas = result.get("personas", [])
            mappings = result.get("personas_with_mappings", [])
            sequences = result.get("sequences", [])
        
        # Products section
        if products:
            file_handle.write("# Products\n\n")
            ExportService._export_products_to_markdown({"result": {"products": products}}, file_handle)
            file_handle.write("\n")
        
        # Personas section
        if personas:
            file_handle.write("# Personas\n\n")
            ExportService._export_personas_to_markdown({"result": {"personas": personas}}, file_handle)
            file_handle.write("\n")
        
        # Mappings section
        if mappings:
            file_handle.write("# Pain-Point Mappings\n\n")
            ExportService._export_mappings_to_markdown({"result": {"personas_with_mappings": mappings}}, file_handle)
            file_handle.write("\n")
        
        # Sequences section
        if sequences:
            file_handle.write("# Outreach Sequences\n\n")
            ExportService._export_sequences_to_markdown({"result": {"sequences": sequences}}, file_handle)


# Singleton instance
_export_service = None


def get_export_service() -> ExportService:
    """Get or create ExportService singleton"""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service

