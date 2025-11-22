"""
CRM Data Loader - Handles multiple CSV files with different structures
智能处理不同CRM系统导出的多个CSV文件，自动识别、映射和合并数据
"""
import pandas as pd
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CRMDataLoader:
    """
    Intelligent CRM data loader that handles:
    - Multiple CSV files with different structures
    - Different CRM systems (Salesforce, HubSpot, Pipedrive, etc.)
    - Automatic field mapping and normalization
    - Data merging across related tables
    """
    
    # File type identification patterns
    FILE_TYPE_PATTERNS = {
        'account': ['account', 'company', 'organization', 'account'],
        'contact': ['contact', 'person', 'lead'],
        'opportunity': ['opportunity', 'deal', 'transaction', 'sales'],
        'campaign': ['campaign', 'marketing'],
        'task': ['task', 'activity', 'event']
    }
    
    # Standard field mappings for different CRM systems
    FIELD_MAPPINGS = {
        # Company/Account fields
        'company_name': {
            'salesforce': ['Name', 'Account Name'],
            'hubspot': ['Company', 'Company Name', 'name'],
            'pipedrive': ['Organization Name', 'name'],
            'generic': ['company', 'company_name', 'name', 'account_name']
        },
        'company_industry': {
            'salesforce': ['Industry', 'SicDesc'],
            'hubspot': ['Company Industry', 'Industry', 'industry'],
            'pipedrive': ['Industry Sector', 'industry'],
            'generic': ['industry', 'sector', 'vertical', 'company_industry']
        },
        'company_country': {
            'salesforce': ['BillingCountry', 'ShippingCountry', 'Country'],
            'hubspot': ['Country', 'country'],
            'pipedrive': ['Location', 'country'],
            'generic': ['country', 'billing_country', 'shipping_country', 'location']
        },
        'company_state': {
            'salesforce': ['BillingState', 'ShippingState', 'State'],
            'hubspot': ['State/Province', 'state'],
            'pipedrive': ['State', 'state'],
            'generic': ['state', 'province', 'billing_state', 'shipping_state']
        },
        'company_city': {
            'salesforce': ['BillingCity', 'ShippingCity', 'City'],
            'hubspot': ['City', 'city'],
            'pipedrive': ['City', 'city'],
            'generic': ['city', 'billing_city', 'shipping_city']
        },
        'company_size': {
            'salesforce': ['NumberOfEmployees', 'Employee Count'],
            'hubspot': ['Number of Employees', 'num_employees'],
            'pipedrive': ['Size', 'employee_count'],
            'generic': ['employee', 'size', 'headcount', 'staff', 'company_size', 'employees']
        },
        'company_revenue': {
            'salesforce': ['AnnualRevenue', 'Revenue'],
            'hubspot': ['Annual Revenue', 'revenue'],
            'pipedrive': ['Revenue', 'annual_revenue'],
            'generic': ['revenue', 'annual_revenue', 'revenue_amount']
        },
        
        # Contact fields
        'contact_firstname': {
            'salesforce': ['FirstName', 'First Name'],
            'hubspot': ['First Name', 'firstname'],
            'pipedrive': ['First Name', 'first_name'],
            'generic': ['firstname', 'first_name', 'fname']
        },
        'contact_lastname': {
            'salesforce': ['LastName', 'Last Name'],
            'hubspot': ['Last Name', 'lastname'],
            'pipedrive': ['Last Name', 'last_name'],
            'generic': ['lastname', 'last_name', 'lname']
        },
        'contact_email': {
            'salesforce': ['Email'],
            'hubspot': ['Email', 'email'],
            'pipedrive': ['Email', 'email'],
            'generic': ['email', 'email_address']
        },
        'contact_job_title': {
            'salesforce': ['Title', 'Job Title'],
            'hubspot': ['Job Title', 'title'],
            'pipedrive': ['Job Title', 'title'],
            'generic': ['title', 'job_title', 'position', 'role', 'function']
        },
        'contact_department': {
            'salesforce': ['Department'],
            'hubspot': ['Department', 'department'],
            'pipedrive': ['Department', 'department'],
            'generic': ['department', 'division', 'team']
        },
        
        # Opportunity/Deal fields
        'deal_name': {
            'salesforce': ['Name', 'Opportunity Name'],
            'hubspot': ['Deal Name', 'dealname'],
            'pipedrive': ['Deal Title', 'title'],
            'generic': ['deal_name', 'opportunity_name', 'name']
        },
        'deal_stage': {
            'salesforce': ['StageName', 'Stage'],
            'hubspot': ['Deal Stage', 'dealstage'],
            'pipedrive': ['Status', 'stage'],
            'generic': ['stage', 'pipeline', 'phase', 'status', 'deal_stage']
        },
        'deal_amount': {
            'salesforce': ['Amount', 'ExpectedRevenue'],
            'hubspot': ['Deal Value', 'amount'],
            'pipedrive': ['Value', 'amount'],
            'generic': ['amount', 'value', 'revenue', 'price', 'deal_amount']
        },
        'deal_close_date': {
            'salesforce': ['CloseDate'],
            'hubspot': ['Close Date', 'closedate'],
            'pipedrive': ['Expected Close Date', 'close_date'],
            'generic': ['close_date', 'closed_date', 'expected_close']
        },
        'deal_type': {
            'salesforce': ['Type'],
            'hubspot': ['Deal Type', 'deal_type'],
            'pipedrive': ['Deal Type', 'type'],
            'generic': ['type', 'deal_type']
        }
    }
    
    @staticmethod
    def identify_file_type(filename: str, df: pd.DataFrame) -> Optional[str]:
        """
        Identify the type of CRM file based on filename and columns
        
        Args:
            filename: CSV filename
            df: DataFrame with columns
            
        Returns:
            File type: 'account', 'contact', 'opportunity', 'campaign', 'task', or None
        """
        filename_lower = filename.lower()
        columns_lower = [col.lower() for col in df.columns]
        
        # Check filename patterns first
        for file_type, patterns in CRMDataLoader.FILE_TYPE_PATTERNS.items():
            if any(pattern in filename_lower for pattern in patterns):
                return file_type
        
        # Check column patterns as fallback
        # Account/Company indicators
        account_indicators = ['account', 'company', 'organization', 'billing', 'shipping', 'industry']
        if any(indicator in ' '.join(columns_lower) for indicator in account_indicators):
            if 'contact' not in filename_lower and 'person' not in filename_lower:
                return 'account'
        
        # Contact indicators
        contact_indicators = ['firstname', 'lastname', 'email', 'title', 'department']
        if any(indicator in ' '.join(columns_lower) for indicator in contact_indicators):
            return 'contact'
        
        # Opportunity indicators
        opportunity_indicators = ['stage', 'amount', 'closedate', 'deal', 'opportunity']
        if any(indicator in ' '.join(columns_lower) for indicator in opportunity_indicators):
            return 'opportunity'
        
        return None
    
    @staticmethod
    def detect_crm_system(df: pd.DataFrame) -> str:
        """
        Detect which CRM system the data comes from based on column names
        
        Returns:
            CRM system: 'salesforce', 'hubspot', 'pipedrive', or 'generic'
        """
        columns_lower = [col.lower() for col in df.columns]
        columns_str = ' '.join(columns_lower)
        
        # Salesforce indicators
        if any(indicator in columns_str for indicator in ['billing', 'shipping', 'stagename', 'systemmodstamp', 'recordtypeid']):
            return 'salesforce'
        
        # HubSpot indicators
        if any(indicator in columns_str for indicator in ['hs_', 'hubspot', 'dealstage', 'dealname']):
            return 'hubspot'
        
        # Pipedrive indicators
        if any(indicator in columns_str for indicator in ['pipedrive', 'org_id', 'person_id']):
            return 'pipedrive'
        
        return 'generic'
    
    @staticmethod
    def map_columns_to_standard(df: pd.DataFrame, file_type: str, crm_system: str) -> pd.DataFrame:
        """
        Map CRM-specific columns to standard field names
        
        Args:
            df: Original DataFrame
            file_type: Type of file ('account', 'contact', 'opportunity', etc.)
            crm_system: CRM system ('salesforce', 'hubspot', 'pipedrive', 'generic')
            
        Returns:
            DataFrame with standardized column names
        """
        df_mapped = df.copy()
        column_mapping = {}
        
        # Get relevant fields for this file type
        relevant_fields = {}
        if file_type == 'account':
            relevant_fields = {k: v for k, v in CRMDataLoader.FIELD_MAPPINGS.items() 
                             if k.startswith('company_')}
        elif file_type == 'contact':
            relevant_fields = {k: v for k, v in CRMDataLoader.FIELD_MAPPINGS.items() 
                             if k.startswith('contact_')}
        elif file_type == 'opportunity':
            relevant_fields = {k: v for k, v in CRMDataLoader.FIELD_MAPPINGS.items() 
                             if k.startswith('deal_')}
        
        # Find matching columns
        for standard_field, crm_mappings in relevant_fields.items():
            # Try CRM-specific mappings first
            if crm_system in crm_mappings:
                for crm_field in crm_mappings[crm_system]:
                    if crm_field in df.columns:
                        column_mapping[crm_field] = standard_field
                        break
            
            # Fallback to generic mappings
            if standard_field not in column_mapping.values():
                for crm_field in crm_mappings.get('generic', []):
                    if crm_field in df.columns:
                        column_mapping[crm_field] = standard_field
                        break
        
        # Apply mapping
        df_mapped = df_mapped.rename(columns=column_mapping)
        
        return df_mapped
    
    @staticmethod
    def load_and_normalize_csv(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a CSV file and normalize it to standard format
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Dictionary with normalized data and metadata, or None if failed
        """
        try:
            filename = Path(file_path).name
            
            # Read CSV (handle large files and encoding issues)
            df = None
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, low_memory=False, nrows=10000, encoding=encoding)
                    if encoding != 'utf-8':
                        logger.debug(f"Read {filename} with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"Failed to read {filename} with {encoding}: {e}")
                    continue
            
            if df is None:
                logger.warning(f"Failed to read {filename} with all attempted encodings")
                return None
            
            if df.empty:
                logger.warning(f"Empty file: {filename}")
                return None
            
            # Identify file type and CRM system
            file_type = CRMDataLoader.identify_file_type(filename, df)
            crm_system = CRMDataLoader.detect_crm_system(df)
            
            logger.info(f"Loaded {filename}: type={file_type}, crm={crm_system}, rows={len(df)}")
            
            # Map columns to standard
            df_normalized = CRMDataLoader.map_columns_to_standard(df, file_type or 'generic', crm_system)
            
            return {
                'file_type': file_type,
                'crm_system': crm_system,
                'filename': filename,
                'original_columns': df.columns.tolist(),
                'normalized_columns': df_normalized.columns.tolist(),
                'data': df_normalized,
                'row_count': len(df_normalized)
            }
            
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None
    
    @staticmethod
    def load_all_crm_files(crm_data_dir: str = "crm-data") -> Dict[str, List[Dict[str, Any]]]:
        """
        Load all CSV files from crm-data directory and organize by type
        
        Args:
            crm_data_dir: Directory containing CRM CSV files
            
        Returns:
            Dictionary organized by file type: {
                'account': [...],
                'contact': [...],
                'opportunity': [...],
                ...
            }
        """
        crm_files = {}
        data_dir = Path(crm_data_dir)
        
        if not data_dir.exists():
            logger.warning(f"CRM data directory not found: {crm_data_dir}")
            return crm_files
        
        # Find all CSV files
        csv_files = list(data_dir.glob("*.csv"))
        
        if not csv_files:
            logger.warning(f"No CSV files found in {crm_data_dir}")
            return crm_files
        
        logger.info(f"Found {len(csv_files)} CSV files in {crm_data_dir}")
        
        # Load and normalize each file
        for csv_file in csv_files:
            normalized_data = CRMDataLoader.load_and_normalize_csv(str(csv_file))
            
            if normalized_data:
                file_type = normalized_data['file_type'] or 'unknown'
                
                if file_type not in crm_files:
                    crm_files[file_type] = []
                
                crm_files[file_type].append(normalized_data)
        
        # Log summary
        for file_type, files in crm_files.items():
            total_rows = sum(f['row_count'] for f in files)
            logger.info(f"Loaded {len(files)} {file_type} file(s) with {total_rows} total rows")
        
        return crm_files
    
    @staticmethod
    def merge_crm_data(crm_files: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Merge data from multiple CRM files into a unified format for persona generation
        
        Args:
            crm_files: Dictionary of loaded CRM files organized by type
            
        Returns:
            Merged data summary with statistics and text representation
        """
        merged_data = {
            'accounts': [],
            'contacts': [],
            'opportunities': [],
            'statistics': {}
        }
        
        # Merge accounts
        if 'account' in crm_files:
            for account_file in crm_files['account']:
                df = account_file['data']
                # Extract key fields
                accounts = df.to_dict('records')
                merged_data['accounts'].extend(accounts)
        
        # Merge contacts
        if 'contact' in crm_files:
            for contact_file in crm_files['contact']:
                df = contact_file['data']
                contacts = df.to_dict('records')
                merged_data['contacts'].extend(contacts)
        
        # Merge opportunities
        if 'opportunity' in crm_files:
            for opp_file in crm_files['opportunity']:
                df = opp_file['data']
                opportunities = df.to_dict('records')
                merged_data['opportunities'].extend(opportunities)
        
        # Generate statistics
        merged_data['statistics'] = CRMDataLoader._generate_statistics(merged_data)
        
        # Generate text summary for LLM
        merged_data['text_summary'] = CRMDataLoader._generate_text_summary(merged_data)
        
        return merged_data
    
    @staticmethod
    def _generate_statistics(merged_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate statistics from merged CRM data"""
        stats = {}
        
        # Account statistics
        if merged_data['accounts']:
            accounts_df = pd.DataFrame(merged_data['accounts'])
            
            # Industry distribution
            if 'company_industry' in accounts_df.columns:
                stats['industry_distribution'] = accounts_df['company_industry'].value_counts().head(20).to_dict()
            
            # Location distribution
            location_cols = ['company_country', 'company_state', 'company_city']
            for col in location_cols:
                if col in accounts_df.columns:
                    stats[f'{col}_distribution'] = accounts_df[col].value_counts().head(20).to_dict()
                    break
            
            # Company size statistics
            if 'company_size' in accounts_df.columns:
                size_col = accounts_df['company_size']
                if pd.api.types.is_numeric_dtype(size_col):
                    non_null = size_col.dropna()
                    if len(non_null) > 0:
                        stats['company_size_stats'] = {
                            'mean': round(float(non_null.mean()), 2),
                            'median': round(float(non_null.median()), 2),
                            'min': round(float(non_null.min()), 2),
                            'max': round(float(non_null.max()), 2),
                            'count': int(len(non_null))
                        }
        
        # Contact statistics
        if merged_data['contacts']:
            contacts_df = pd.DataFrame(merged_data['contacts'])
            
            # Job title distribution
            if 'contact_job_title' in contacts_df.columns:
                stats['job_title_distribution'] = contacts_df['contact_job_title'].value_counts().head(30).to_dict()
            
            # Department distribution
            if 'contact_department' in contacts_df.columns:
                stats['department_distribution'] = contacts_df['contact_department'].value_counts().head(20).to_dict()
        
        # Opportunity statistics
        if merged_data['opportunities']:
            opps_df = pd.DataFrame(merged_data['opportunities'])
            
            # Deal stage distribution
            if 'deal_stage' in opps_df.columns:
                stats['deal_stage_distribution'] = opps_df['deal_stage'].value_counts().head(20).to_dict()
            
            # Deal amount statistics
            if 'deal_amount' in opps_df.columns:
                amount_col = opps_df['deal_amount']
                if pd.api.types.is_numeric_dtype(amount_col):
                    non_null = amount_col.dropna()
                    if len(non_null) > 0:
                        stats['deal_amount_stats'] = {
                            'mean': round(float(non_null.mean()), 2),
                            'median': round(float(non_null.median()), 2),
                            'min': round(float(non_null.min()), 2),
                            'max': round(float(non_null.max()), 2),
                            'count': int(len(non_null))
                        }
        
        # Overall counts
        stats['total_accounts'] = len(merged_data['accounts'])
        stats['total_contacts'] = len(merged_data['contacts'])
        stats['total_opportunities'] = len(merged_data['opportunities'])
        
        return stats
    
    @staticmethod
    def _generate_text_summary(merged_data: Dict[str, Any]) -> str:
        """Generate text summary for LLM consumption"""
        stats = merged_data['statistics']
        summary_parts = []
        
        summary_parts.append("=== CRM CUSTOMER DATA SUMMARY ===\n")
        
        # Overall counts
        summary_parts.append(f"Total Accounts: {stats.get('total_accounts', 0)}")
        summary_parts.append(f"Total Contacts: {stats.get('total_contacts', 0)}")
        summary_parts.append(f"Total Opportunities: {stats.get('total_opportunities', 0)}\n")
        
        # Industry distribution
        if 'industry_distribution' in stats:
            summary_parts.append("--- Industry Distribution ---")
            for industry, count in list(stats['industry_distribution'].items())[:10]:
                summary_parts.append(f"  {industry}: {count}")
            summary_parts.append("")
        
        # Location distribution
        for col in ['company_country_distribution', 'company_state_distribution', 'company_city_distribution']:
            if col in stats:
                location_type = col.replace('_distribution', '').replace('company_', '')
                summary_parts.append(f"--- {location_type.title()} Distribution ---")
                for location, count in list(stats[col].items())[:10]:
                    summary_parts.append(f"  {location}: {count}")
                summary_parts.append("")
                break
        
        # Company size stats
        if 'company_size_stats' in stats:
            size_stats = stats['company_size_stats']
            summary_parts.append("--- Company Size Statistics ---")
            summary_parts.append(f"  Mean: {size_stats['mean']} employees")
            summary_parts.append(f"  Median: {size_stats['median']} employees")
            summary_parts.append(f"  Range: {size_stats['min']} - {size_stats['max']} employees")
            summary_parts.append("")
        
        # Job title distribution
        if 'job_title_distribution' in stats:
            summary_parts.append("--- Top Job Titles ---")
            for title, count in list(stats['job_title_distribution'].items())[:15]:
                summary_parts.append(f"  {title}: {count}")
            summary_parts.append("")
        
        # Deal stage distribution
        if 'deal_stage_distribution' in stats:
            summary_parts.append("--- Deal Stage Distribution ---")
            for stage, count in stats['deal_stage_distribution'].items():
                summary_parts.append(f"  {stage}: {count}")
            summary_parts.append("")
        
        # Deal amount stats
        if 'deal_amount_stats' in stats:
            amount_stats = stats['deal_amount_stats']
            summary_parts.append("--- Deal Amount Statistics ---")
            summary_parts.append(f"  Mean: ${amount_stats['mean']:,.0f}")
            summary_parts.append(f"  Median: ${amount_stats['median']:,.0f}")
            summary_parts.append(f"  Range: ${amount_stats['min']:,.0f} - ${amount_stats['max']:,.0f}")
            summary_parts.append("")
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def load_crm_data_for_persona(crm_data_dir: str = "crm-data") -> Optional[str]:
        """
        Main entry point: Load all CRM data and return text summary for persona generation
        
        Args:
            crm_data_dir: Directory containing CRM CSV files
            
        Returns:
            Text summary string for LLM, or None if no data found
        """
        # Load all files
        crm_files = CRMDataLoader.load_all_crm_files(crm_data_dir)
        
        if not crm_files:
            logger.info("No CRM data files found")
            return None
        
        # Merge data
        merged_data = CRMDataLoader.merge_crm_data(crm_files)
        
        if not merged_data['statistics'].get('total_accounts', 0) and \
           not merged_data['statistics'].get('total_contacts', 0) and \
           not merged_data['statistics'].get('total_opportunities', 0):
            logger.warning("No valid CRM data found after merging")
            return None
        
        return merged_data['text_summary']








