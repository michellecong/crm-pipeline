import pandas as pd
import io
from typing import Dict, Any

class CRMService:
    """
    Service for processing CRM CSV files
    """
    
    # Configuration constants
    MAX_ROWS_FOR_FULL_PROCESSING = 5000
    SAMPLE_SIZE = 1000
    TOP_VALUES_LIMIT = 10
    
    @staticmethod
    def parse_csv(file_content: bytes) -> Dict[str, Any]:
        """
        Parse CSV content and extract data
        
        Args:
            file_content: Raw bytes of CSV file
            
        Returns:
            Dictionary containing full content and summary
            
        Raises:
            ValueError: If CSV parsing fails
        """
        try:
            # Parse CSV
            df = pd.read_csv(io.BytesIO(file_content))
            
            # Check if DataFrame is empty or has no rows
            if df.empty or len(df) == 0:
                raise ValueError("CSV file is empty or has no data rows")
            
            # Convert to text format
            full_content = df.to_string(index=False)
            
            # Generate summary
            summary = CRMService._generate_summary(df)
            
            return {
                "full_content": full_content,
                "summary": summary
            }
            
        except pd.errors.EmptyDataError:
            raise ValueError("CSV file is empty or has no data")
        except pd.errors.ParserError as e:
            raise ValueError(f"CSV parsing error: {str(e)}")
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")
    
    @staticmethod
    def _generate_summary(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate basic summary statistics from DataFrame
        
        Args:
            df: Parsed DataFrame
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": df.columns.tolist(),
            "preview": df.head(5).to_dict('records')
        }
        
        # Add column analysis
        summary.update(CRMService._analyze_common_columns(df))
        
        return summary
    
    @staticmethod
    def _analyze_common_columns(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Intelligently identify and analyze CRM columns
        Handles both categorical and numeric columns appropriately
        
        Args:
            df: Parsed DataFrame
            
        Returns:
            Dictionary with column analysis
        """
        analysis = {}
        
        # Column configuration with keywords and types
        column_config = {
            'industry': {
                'keywords': ['industry', 'sector', 'vertical'],
                'type': 'categorical'
            },
            'location': {
                'keywords': ['country', 'location', 'region', 'state', 'city'],
                'type': 'categorical'
            },
            'department': {
                'keywords': ['department', 'division', 'team'],
                'type': 'categorical'
            },
            'job_title': {
                'keywords': ['function', 'title', 'role', 'position', 'job'],
                'type': 'categorical'
            },
            'deal_stage': {
                'keywords': ['stage', 'pipeline', 'phase', 'status'],
                'type': 'categorical'
            },
            'deal_amount': {
                'keywords': ['amount', 'value', 'revenue', 'price', 'deal_amount'],
                'type': 'numeric'
            },
            'company_size': {
                'keywords': ['employee', 'size', 'headcount', 'staff', 'company_size'],
                'type': 'numeric'
            }
        }
        
        # Track matched columns to avoid duplicates
        matched_columns = set()
        
        for key, config in column_config.items():
            keywords = config['keywords']
            col_type = config['type']
            
            for col in df.columns:
                # Skip if column already matched
                if col in matched_columns:
                    continue
                
                col_lower = col.lower()
                
                # Check if any keyword matches (substring match)
                if any(keyword in col_lower for keyword in keywords):
                    try:
                        # Handle numeric columns
                        if col_type == 'numeric' and pd.api.types.is_numeric_dtype(df[col]):
                            non_null_values = df[col].dropna()
                            if len(non_null_values) > 0:
                                analysis[f"{key}_stats"] = {
                                    'mean': round(float(non_null_values.mean()), 2),
                                    'median': round(float(non_null_values.median()), 2),
                                    'min': round(float(non_null_values.min()), 2),
                                    'max': round(float(non_null_values.max()), 2),
                                    'count': int(len(non_null_values))  # ← 确保是 int
                                }
                                matched_columns.add(col)
                        # Handle categorical columns
                        else:
                            value_counts = df[col].value_counts().head(CRMService.TOP_VALUES_LIMIT)
                            if len(value_counts) > 0:
                                analysis[f"{key}_distribution"] = value_counts.to_dict()
                                matched_columns.add(col)
                        
                        break  # Only match first column for each category
                        
                    except Exception:
                        # Skip problematic columns silently
                        continue
        
        return analysis