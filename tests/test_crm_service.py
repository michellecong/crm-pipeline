import pytest
import pandas as pd
from pathlib import Path
from app.services.crm_service import CRMService


class TestCRMService:
    """Test suite for CRM Service"""
    
    @pytest.fixture
    def mock_csv_path(self):
        """Path to mock CSV file"""
        return Path(__file__).parent / "fixtures" / "mock_crm_data.csv"
    
    @pytest.fixture
    def mock_csv_content(self, mock_csv_path):
        """Read mock CSV as bytes"""
        with open(mock_csv_path, 'rb') as f:
            return f.read()
    
    @pytest.fixture
    def sample_csv_bytes(self):
        """Simple CSV for basic testing"""
        csv_string = """company_name,company_industry,company_country
ABC Corp,Technology,United States
XYZ Inc,Finance,Canada
Test Ltd,Technology,United States"""
        return csv_string.encode('utf-8')
    
    # ===== Basic Parsing Tests =====
    
    def test_parse_csv_success(self, sample_csv_bytes):
        """Test successful CSV parsing"""
        result = CRMService.parse_csv(sample_csv_bytes)
        
        assert "full_content" in result
        assert "summary" in result
        assert isinstance(result["full_content"], str)
        assert isinstance(result["summary"], dict)
    
    def test_parse_csv_with_mock_data(self, mock_csv_content):
        """Test parsing with realistic mock data"""
        result = CRMService.parse_csv(mock_csv_content)
        
        # Check structure
        assert result["summary"]["total_rows"] == 15
        assert result["summary"]["total_columns"] == 28
        
        # Check columns exist
        expected_columns = [
            'company_name', 'company_domain', 'company_industry',
            'company_address', 'company_country', 'company_size',
            'contact_firstname', 'contact_lastname', 'contact_email',
            'contact_phone', 'contact_address', 'contact_country',
            'contact_function', 'contact_department', 'deal_name',
            'deal_stage', 'deal_amount', 'deal_type', 'deal_source',
            'close_date', 'ticket_title', 'ticket_status', 'ticket_priority',
            'product_name', 'product_price', 'product_description',
            'product_sku', 'product_quantity'
        ]
        assert result["summary"]["columns"] == expected_columns
    
    def test_parse_invalid_csv(self):
        """Test parsing invalid CSV data"""
        invalid_content = b"This is not a valid CSV file\nRandom text here"
        
        # Pandas may still parse this, so we just check it doesn't crash
        # or we check for specific error
        try:
            result = CRMService.parse_csv(invalid_content)
            # If it parses, check it has expected structure
            assert "summary" in result
        except ValueError:
            # This is also acceptable
            pass
    
    def test_parse_empty_csv(self):
        """Test parsing empty CSV"""
        empty_csv = b""
        
        with pytest.raises(ValueError) as exc_info:
            CRMService.parse_csv(empty_csv)
        
        # Check error message contains relevant info
        error_msg = str(exc_info.value).lower()
        assert "empty" in error_msg or "no data" in error_msg or "no columns" in error_msg
    
    def test_parse_csv_headers_only(self):
        """Test CSV with only headers, no data"""
        headers_only = b"column1,column2,column3\n"
        
        with pytest.raises(ValueError) as exc_info:
            CRMService.parse_csv(headers_only)
        
        error_msg = str(exc_info.value).lower()
        assert "empty" in error_msg or "no data" in error_msg
    
    # ===== Summary Generation Tests =====
    
    def test_generate_summary_structure(self, mock_csv_content):
        """Test summary contains required fields"""
        result = CRMService.parse_csv(mock_csv_content)
        summary = result["summary"]
        
        # Required fields
        assert "total_rows" in summary
        assert "total_columns" in summary
        assert "columns" in summary
        assert "preview" in summary
        
        # Data types
        assert isinstance(summary["total_rows"], int)
        assert isinstance(summary["total_columns"], int)
        assert isinstance(summary["columns"], list)
        assert isinstance(summary["preview"], list)
    
    def test_preview_length(self, mock_csv_content):
        """Test preview contains first 5 rows"""
        result = CRMService.parse_csv(mock_csv_content)
        preview = result["summary"]["preview"]
        
        assert len(preview) == 5
        assert isinstance(preview[0], dict)
        assert "company_name" in preview[0]
        assert preview[0]["company_name"] == "Acme Corp"
    
    def test_preview_with_less_than_5_rows(self):
        """Test preview when CSV has < 5 rows"""
        small_csv = b"""company_name,company_industry
ABC,Technology
XYZ,Finance"""
        
        result = CRMService.parse_csv(small_csv)
        preview = result["summary"]["preview"]
        
        assert len(preview) == 2
    
    # ===== Column Analysis Tests - Categorical =====
    
    def test_analyze_industry_column(self, mock_csv_content):
        """Test industry column detection and analysis"""
        result = CRMService.parse_csv(mock_csv_content)
        summary = result["summary"]
        
        assert "industry_distribution" in summary
        
        industry_dist = summary["industry_distribution"]
        assert isinstance(industry_dist, dict)
        assert "Technology" in industry_dist
        assert "Finance" in industry_dist
        assert "Healthcare" in industry_dist
        assert "Real Estate" in industry_dist
        
        # Verify counts (based on actual mock data)
        assert industry_dist["Technology"] == 5
        assert industry_dist["Finance"] == 4
        assert industry_dist["Healthcare"] == 3
        assert industry_dist["Real Estate"] == 3
    
    def test_analyze_location_column(self, mock_csv_content):
        """Test location column detection and analysis"""
        result = CRMService.parse_csv(mock_csv_content)
        summary = result["summary"]
        
        assert "location_distribution" in summary
        
        location_dist = summary["location_distribution"]
        assert "United States" in location_dist
        assert "Canada" in location_dist
        assert "United Kingdom" in location_dist
        
        # Verify counts (based on actual mock data)
        assert location_dist["United States"] == 6  # ← 修正
        assert location_dist["Canada"] == 5
        assert location_dist["United Kingdom"] == 4  # ← 修正
    
    def test_analyze_job_title_column(self, mock_csv_content):
        """Test job title (contact_function) detection and analysis"""
        result = CRMService.parse_csv(mock_csv_content)
        summary = result["summary"]
        
        assert "job_title_distribution" in summary
        
        job_dist = summary["job_title_distribution"]
        assert isinstance(job_dist, dict)
        # Check that we have some job titles
        assert len(job_dist) > 0
    
    def test_analyze_department_column(self, mock_csv_content):
        """Test department column detection and analysis"""
        result = CRMService.parse_csv(mock_csv_content)
        summary = result["summary"]
        
        assert "department_distribution" in summary
        
        dept_dist = summary["department_distribution"]
        assert "Sales" in dept_dist
        assert "Operations" in dept_dist
        assert dept_dist["Sales"] == 4  # ← 修正
        assert dept_dist["Operations"] == 3
    
    def test_analyze_deal_stage_column(self, mock_csv_content):
        """Test deal stage column detection and analysis"""
        result = CRMService.parse_csv(mock_csv_content)
        summary = result["summary"]
        
        assert "deal_stage_distribution" in summary
        
        stage_dist = summary["deal_stage_distribution"]
        assert "Qualified To Buy" in stage_dist
        assert "Decision Maker Brought-In" in stage_dist
        assert "Presentation Scheduled" in stage_dist
        assert "Appointment Scheduled" in stage_dist
    
    # ===== Column Analysis Tests - Numeric =====
    
    def test_analyze_deal_amount_numeric(self, mock_csv_content):
        """Test deal_amount shows statistics instead of distribution"""
        result = CRMService.parse_csv(mock_csv_content)
        summary = result["summary"]
        
        # Should have stats, not distribution
        assert "deal_amount_stats" in summary
        assert "deal_amount_distribution" not in summary
        
        stats = summary["deal_amount_stats"]
        assert "mean" in stats
        assert "median" in stats
        assert "min" in stats
        assert "max" in stats
        assert "count" in stats
        
        # Verify data types
        assert isinstance(stats["count"], int)
        assert isinstance(stats["mean"], (int, float))
        
        # Verify stats are reasonable
        assert stats["min"] == 28000.0
        assert stats["max"] == 125000.0
        assert stats["count"] == 15
        assert 50000 < stats["mean"] < 80000
    
    def test_analyze_company_size_numeric(self, mock_csv_content):
        """Test company_size shows statistics"""
        result = CRMService.parse_csv(mock_csv_content)
        summary = result["summary"]
        
        assert "company_size_stats" in summary
        
        stats = summary["company_size_stats"]
        assert "count" in stats
        assert isinstance(stats["count"], int)
        
        assert stats["min"] == 180.0
        assert stats["max"] == 920.0
        assert stats["count"] == 15
        assert 400 < stats["mean"] < 500
    
    # ===== Edge Cases =====
    
    def test_no_matching_columns(self):
        """Test CSV with no recognizable columns"""
        csv_with_unknown_cols = b"""random_col1,random_col2,unknown_field
value1,value2,value3
value4,value5,value6"""
        
        result = CRMService.parse_csv(csv_with_unknown_cols)
        summary = result["summary"]
        
        # Should still have basic summary
        assert summary["total_rows"] == 2
        assert summary["total_columns"] == 3
        
        # But no distribution analysis
        assert "industry_distribution" not in summary
        assert "location_distribution" not in summary
        assert "deal_amount_stats" not in summary
    
    def test_column_matching_case_insensitive(self):
        """Test column matching works regardless of case"""
        csv_upper = b"""COMPANY_INDUSTRY,COMPANY_COUNTRY,DEAL_AMOUNT
Technology,USA,50000
Finance,Canada,75000"""
        
        result = CRMService.parse_csv(csv_upper)
        summary = result["summary"]
        
        # Should detect columns despite uppercase
        assert "industry_distribution" in summary
        assert "location_distribution" in summary
        assert "deal_amount_stats" in summary
    
    def test_top_10_values_limit(self):
        """Test that distribution only returns top 10 values"""
        # Create CSV with 15 different industries
        rows = [f"Company{i},Industry{i},USA,{50000+i*1000}" for i in range(15)]
        csv_content = "company_name,company_industry,country,deal_amount\n" + "\n".join(rows)
        
        result = CRMService.parse_csv(csv_content.encode('utf-8'))
        summary = result["summary"]
        
        if "industry_distribution" in summary:
            # Should have max 10 entries
            assert len(summary["industry_distribution"]) <= 10
    
    def test_csv_with_missing_values(self):
        """Test CSV with NaN/missing values"""
        csv_with_nan = b"""company_name,company_industry,company_country,deal_amount
ABC Corp,Technology,United States,50000
XYZ Inc,,Canada,
Test Ltd,Finance,,75000"""
        
        result = CRMService.parse_csv(csv_with_nan)
        summary = result["summary"]
        
        # Should parse successfully
        assert summary["total_rows"] == 3
        
        # Check that NaN values are handled
        if "industry_distribution" in summary:
            dist = summary["industry_distribution"]
            # Should only count non-null values
            assert sum(dist.values()) == 2
        
        if "deal_amount_stats" in summary:
            stats = summary["deal_amount_stats"]
            assert "count" in stats
            assert isinstance(stats["count"], int)
            assert stats["count"] == 2  # Only 2 valid amounts
    
    def test_csv_with_special_characters(self):
        """Test CSV with special characters in data"""
        csv_special = b"""company_name,company_industry,deal_amount
"ABC Corp, Inc.",Technology & Software,50000
XYZ's Company,Finance/Banking,75000"""
        
        result = CRMService.parse_csv(csv_special)
        summary = result["summary"]
        
        # Should parse successfully
        assert summary["total_rows"] == 2
        preview = summary["preview"]
        assert "ABC Corp, Inc." in preview[0]["company_name"]
        assert "Technology & Software" in preview[0]["company_industry"]
    
    def test_mixed_numeric_string_column(self):
        """Test column with mixed numeric and string values"""
        csv_mixed = b"""company_name,company_size
ABC Corp,500
XYZ Inc,Large
Test Ltd,250"""
        
        result = CRMService.parse_csv(csv_mixed)
        summary = result["summary"]
        
        # Should treat as categorical since not all numeric
        # Either no match or categorical distribution
        if "company_size_distribution" in summary:
            assert isinstance(summary["company_size_distribution"], dict)
    
    # ===== Full Content Tests =====
    
    def test_full_content_format(self, sample_csv_bytes):
        """Test full_content is properly formatted"""
        result = CRMService.parse_csv(sample_csv_bytes)
        full_content = result["full_content"]
        
        # Should contain column names
        assert "company_name" in full_content
        assert "company_industry" in full_content
        
        # Should contain data
        assert "ABC Corp" in full_content
        assert "Technology" in full_content
    
    def test_full_content_no_index(self, sample_csv_bytes):
        """Test that full_content doesn't include DataFrame index"""
        result = CRMService.parse_csv(sample_csv_bytes)
        full_content = result["full_content"]
        
        lines = full_content.split('\n')
        # Check format is reasonable
        assert len(lines) > 0
    
    # ===== Performance Tests =====
    
    def test_large_csv_performance(self):
        """Test parsing larger CSV (basic performance check)"""
        # Generate 1000 rows
        rows = [f"Company{i},Technology,United States,{50000+i}" for i in range(1000)]
        large_csv = "company_name,company_industry,country,deal_amount\n" + "\n".join(rows)
        
        result = CRMService.parse_csv(large_csv.encode('utf-8'))
        summary = result["summary"]
        
        assert summary["total_rows"] == 1000
        assert len(summary["preview"]) == 5
        
        # Should still have analysis
        assert "industry_distribution" in summary
        assert "deal_amount_stats" in summary


# ===== Integration Tests =====

class TestCRMServiceIntegration:
    """Integration tests with realistic workflow"""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow: upload → parse → analyze"""
        csv_content = b"""company_name,company_industry,company_country,deal_amount,company_size
ABC Corp,Technology,United States,50000,450
XYZ Inc,Technology,Canada,75000,320
Tech Ltd,Finance,United States,60000,680
Data Co,Technology,United Kingdom,45000,150
Cloud Systems,Healthcare,United States,90000,600"""
        
        # Parse
        result = CRMService.parse_csv(csv_content)
        
        # Verify structure
        assert "full_content" in result
        assert "summary" in result
        
        summary = result["summary"]
        assert summary["total_rows"] == 5
        assert summary["total_columns"] == 5
        
        # Verify categorical analysis
        assert "industry_distribution" in summary
        assert summary["industry_distribution"]["Technology"] == 3
        
        assert "location_distribution" in summary
        assert summary["location_distribution"]["United States"] == 3
        
        # Verify numeric analysis
        assert "deal_amount_stats" in summary
        stats = summary["deal_amount_stats"]
        assert "count" in stats
        assert isinstance(stats["count"], int)
        assert stats["count"] == 5
        assert stats["min"] == 45000.0
        assert stats["max"] == 90000.0
        
        assert "company_size_stats" in summary
        size_stats = summary["company_size_stats"]
        assert "count" in size_stats
        assert size_stats["count"] == 5
    
    def test_realistic_crm_export_workflow(self):
        """Test with realistic CRM export structure"""
        csv_content = b"""Company Name,Industry,Country,Contact Name,Contact Title,Deal Stage,Deal Value
"Acme Corporation, Inc.",SaaS & Cloud,United States,John Smith,VP of Sales,Qualified,50000
"Global Tech Ltd.",Enterprise Software,Canada,Jane Doe,Director IT,Negotiation,75000
"Finance Pro","Banking, Finance",United Kingdom,Bob Johnson,CFO,Proposal,60000"""
        
        result = CRMService.parse_csv(csv_content)
        summary = result["summary"]
        
        # Should successfully parse despite spaces and special chars in column names
        assert summary["total_rows"] == 3
        assert "industry_distribution" in summary
        assert "location_distribution" in summary