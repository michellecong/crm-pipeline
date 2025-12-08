# routers/export.py
"""
Export router for downloading generated content in different formats
"""
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse
from typing import Literal, Optional
from pathlib import Path
from datetime import datetime
import json
import logging

from ..services.export_service import get_export_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/export/{file_path:path}",
    summary="Export generated content in different formats",
    description="Export generated content (personas, products, mappings, sequences) in JSON, CSV, or Markdown format"
)
async def export_content(
    file_path: str,
    format: Literal["json", "csv", "markdown"] = Query(
        default="json",
        description="Export format: json, csv, or markdown"
    )
):
    """
    Export generated content from a saved JSON file to different formats.
    
    Args:
        file_path: Path to the generated JSON file (relative to data/generated/)
        format: Export format (json, csv, markdown)
    
    Returns:
        FileResponse with the exported file
    """
    try:
        # Normalize file path - support multiple input formats
        # 1. Just filename: "asana_personas_2025-11-24T21-04-48.json"
        # 2. Relative path: "data/generated/asana_personas_2025-11-24T21-04-48.json"
        # 3. Full path from project root
        
        # Remove leading slash if present
        file_path = file_path.lstrip('/')
        
        # If it's just a filename or doesn't start with data/generated/, add the prefix
        if not file_path.startswith("data/generated/"):
            # Check if it's just a filename (no slashes)
            if '/' not in file_path:
                file_path = f"data/generated/{file_path}"
            else:
                # It's a relative path, try to normalize
                if file_path.startswith("generated/"):
                    file_path = f"data/{file_path}"
        
        json_file = Path(file_path)
        
        # Validate file exists
        if not json_file.exists():
            # Provide helpful error message with available files
            generated_dir = Path("data/generated")
            available_files = []
            if generated_dir.exists():
                available_files = [f.name for f in generated_dir.glob("*.json")][:10]  # Show first 10
            
            error_msg = f"File not found: {file_path}"
            if available_files:
                error_msg += f"\n\nAvailable files in data/generated/:\n" + "\n".join(f"  - {f}" for f in available_files[:5])
                if len(available_files) > 5:
                    error_msg += f"\n  ... and {len(available_files) - 5} more files"
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Determine content type from generator_type
        generator_type = data.get("generator_type", "unknown")
        content_type = generator_type
        
        # Handle special cases
        if generator_type in ["baseline", "two_stage", "three_stage", "pipeline"]:
            content_type = "pipeline"
        
        # Generate output filename
        company_name = data.get("company_name", "unknown")
        timestamp = json_file.stem.split('_')[-1] if '_' in json_file.stem else "export"
        
        export_service = get_export_service()
        
        if format == "json":
            # Return original JSON file
            return FileResponse(
                path=str(json_file),
                filename=json_file.name,
                media_type="application/json"
            )
        
        elif format == "csv":
            # Export to CSV
            output_file = json_file.parent / f"{json_file.stem}.csv"
            export_service.export_to_csv(data, str(output_file), content_type)
            return FileResponse(
                path=str(output_file),
                filename=output_file.name,
                media_type="text/csv"
            )
        
        else:  # format == "markdown"
            # Export to Markdown
            output_file = json_file.parent / f"{json_file.stem}.md"
            export_service.export_to_markdown(data, str(output_file), content_type)
            return FileResponse(
                path=str(output_file),
                filename=output_file.name,
                media_type="text/markdown"
            )
    
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.post(
    "/export/convert",
    summary="Convert data directly to different formats",
    description="Convert provided data directly to CSV, Markdown, or JSON format. Supports both frontend format (with 'payload') and backend format (with 'result')."
)
async def convert_content(
    data: dict,
    format: Literal["csv", "markdown", "json"] = Query(
        default="csv",
        description="Export format: csv, markdown, or json"
    ),
    content_type: Optional[str] = Query(
        default=None,
        description="Content type (personas, products, mappings, sequences, pipeline). Auto-detected if not provided. Use 'pipeline' to export all sections."
    )
):
    """
    Convert data directly to CSV, Markdown, or JSON format.
    
    This endpoint accepts data in the request body and converts it to the requested format.
    Supports both frontend format (PipelineGenerateEnvelope with 'payload') and backend format (with 'result').
    The export service automatically handles both formats - no normalization needed!
    
    Args:
        data: Data dictionary (frontend format with 'payload' or backend format with 'result')
        format: Export format (csv, markdown, or json)
        content_type: Content type (personas, products, mappings, sequences, pipeline). 
                     If not provided, auto-detected from data structure.
                     Use 'pipeline' to export all sections together.
    
    Returns:
        FileResponse with the converted file
    """
    try:
        from tempfile import NamedTemporaryFile
        import json as json_lib
        
        # Auto-detect content type if not provided
        if not content_type:
            if "payload" in data:
                # Frontend format - detect from payload
                payload = data["payload"]
                if payload.get("personas") and len(payload.get("personas", [])) > 0:
                    content_type = "personas"
                elif payload.get("products") and len(payload.get("products", [])) > 0:
                    content_type = "products"
                elif payload.get("personas_with_mappings") and len(payload.get("personas_with_mappings", [])) > 0:
                    content_type = "mappings"
                elif payload.get("sequences") and len(payload.get("sequences", [])) > 0:
                    content_type = "sequences"
                else:
                    content_type = "pipeline"
            else:
                # Backend format - use generator_type
                generator_type = data.get("generator_type", "unknown")
                content_type = "pipeline" if generator_type in ["baseline", "two_stage", "three_stage", "pipeline"] else generator_type
        
        company_name = data.get("company_name", "export")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_service = get_export_service()
        
        if format == "json":
            # Extract requested section or return full pipeline
            if content_type and content_type != "pipeline":
                # Extract single section
                if "payload" in data:
                    payload = data["payload"]
                    # Map content_type to payload key and result key
                    section_map = {
                        "personas": ("personas", "personas"),
                        "products": ("products", "products"),
                        "mappings": ("personas_with_mappings", "personas_with_mappings"),
                        "sequences": ("sequences", "sequences")
                    }
                    payload_key, result_key = section_map.get(content_type, (None, content_type))
                    json_data = {
                        "company_name": company_name,
                        "generator_type": content_type,
                        "generated_at": datetime.now().isoformat(),
                        "result": {result_key: payload.get(payload_key, [])} if payload_key else {}
                    }
                else:
                    # Backend format
                    result = data.get("result", {})
                    json_data = {
                        "company_name": company_name,
                        "generator_type": content_type,
                        "generated_at": datetime.now().isoformat(),
                        "result": {content_type: result.get(content_type, [])}
                    }
            else:
                # Return full pipeline data
                json_data = data
            
            # Create temporary file for JSON
            temp_file = NamedTemporaryFile(
                mode='w',
                suffix=".json",
                delete=False,
                encoding='utf-8'
            )
            temp_path = temp_file.name
            json_lib.dump(json_data, temp_file, indent=2, ensure_ascii=False)
            temp_file.close()
            
            filename = f"{company_name}_{content_type or 'pipeline'}_{timestamp}.json"
            return FileResponse(
                path=temp_path,
                filename=filename,
                media_type="application/json"
            )
        
        elif format == "csv":
            suffix = ".csv"
            media_type = "text/csv"
        elif format == "markdown":
            suffix = ".md"
            media_type = "text/markdown"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}. Use 'csv', 'markdown', or 'json'."
            )
        
        # Create temporary file for CSV/Markdown
        temp_file = NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            delete=False,
            encoding='utf-8'
        )
        temp_path = temp_file.name
        temp_file.close()
        
        # Export to file - export_service now handles both formats directly!
        if format == "csv":
            export_service.export_to_csv(data, temp_path, content_type)
        else:
            export_service.export_to_markdown(data, temp_path, content_type)
        
        # Generate filename
        filename = f"{company_name}_{content_type}_{timestamp}{suffix}"
        
        return FileResponse(
            path=temp_path,
            filename=filename,
            media_type=media_type
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversion failed: {str(e)}"
        )

