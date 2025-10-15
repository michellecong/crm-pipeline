-- SQL script to create tables for Sales Content Packs

-- Create ENUM types
CREATE TYPE persona_tier AS ENUM ('tier_1', 'tier_2', 'tier_3');
CREATE TYPE touch_channel AS ENUM ('email', 'linkedin', 'phone', 'video', 'direct_mail', 'other');

-- 1. Companies
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_companies_domain ON companies(domain);

-- 2. Account Profiles
CREATE TABLE account_profiles (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true, -- Only one active profile per company
    model_used VARCHAR(50),
    generation_cost DECIMAL(10, 4), 
    prompt_tokens INTEGER, -- input tokens used
    completion_tokens INTEGER, -- output tokens generated
    generation_time_seconds INTEGER,
    status VARCHAR(50) DEFAULT 'draft',
    data_sources_summary TEXT, -- optional summary of data sources used
    generated_at TIMESTAMP DEFAULT NOW(), 
    created_at TIMESTAMP DEFAULT NOW(), 
    updated_at TIMESTAMP DEFAULT NOW(), 
    UNIQUE(company_id, version) -- Ensure unique versioning per company
);
CREATE INDEX idx_profiles_company ON account_profiles(company_id); -- For quick lookups by company
CREATE INDEX idx_profiles_active ON account_profiles(company_id, is_active) WHERE is_active = true; -- For fetching active profiles

-- 3. Data Sources (track where content came from)
CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES account_profiles(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'website', 'news', 'case_study', 'pdf', 'crm'
    source_url TEXT, -- URL if applicable (NULL for uploaded files)
    file_name VARCHAR(255), -- For uploaded PDFs/CSVs
    title VARCHAR(500), -- Page/document title
    content_preview TEXT, -- First 500 chars for reference
    content_length INTEGER, -- Total characters scraped
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_sources_profile ON data_sources(profile_id); -- For fetching sources by profile
CREATE INDEX idx_sources_type ON data_sources(source_type); -- For filtering by source type

-- 4. Product Offerings (Products/Services)
CREATE TABLE product_offerings (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES account_profiles(id) ON DELETE CASCADE,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    relevance_reasoning TEXT,
    sort_order INTEGER DEFAULT 0, -- For ordering products
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_products_profile ON product_offerings(profile_id); -- For fetching products by profile

-- 5. Personas
CREATE TABLE personas (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES account_profiles(id) ON DELETE CASCADE,
    persona_name VARCHAR(255) NOT NULL, -- e.g., "CTO", "Marketing Manager"
    tier persona_tier NOT NULL, -- e.g., tier_1, tier_2, tier_3
    description TEXT, 
    sort_order INTEGER DEFAULT 0, -- For ordering personas
    created_at TIMESTAMP DEFAULT NOW() 
);
CREATE INDEX idx_personas_profile ON personas(profile_id); -- For fetching personas by profile
CREATE INDEX idx_personas_tier ON personas(profile_id, tier); -- For filtering personas by tier

-- 6. Persona Constituents
CREATE TABLE persona_constituents (
    id SERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    constituent_type VARCHAR(50) NOT NULL, -- e.g., "job_title", "department", "location"
    value VARCHAR(255) NOT NULL, -- e.g., "CTO", "Engineering", "New York"    
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_constituents_type ON persona_constituents(constituent_type); -- For filtering constituents by type

-- 7. Pain Points
CREATE TABLE pain_points (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES account_profiles(id) ON DELETE CASCADE,
    persona_id INTEGER REFERENCES personas(id) ON DELETE CASCADE, 
    pain_point TEXT NOT NULL,
    category VARCHAR(100), -- e.g., "operational", "financial", "strategic"
    priority VARCHAR(20), -- e.g., "high", "medium", "low"
    sort_order INTEGER DEFAULT 0, -- For ordering pain points
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_pain_points_profile ON pain_points(profile_id);
CREATE INDEX idx_pain_points_persona ON pain_points(persona_id);

-- 8. Value Propositions
CREATE TABLE value_propositions (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES account_profiles(id) ON DELETE CASCADE,
    persona_id INTEGER REFERENCES personas(id) ON DELETE CASCADE,
    value_proposition TEXT NOT NULL, 
    category VARCHAR(100), -- e.g., "cost_saving", "efficiency", "innovation"
    sort_order INTEGER DEFAULT 0, -- For ordering value propositions
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_value_props_profile ON value_propositions(profile_id); -- For fetching value props by profile
CREATE INDEX idx_value_props_persona ON value_propositions(persona_id); -- For filtering value props by persona

-- 9. Pain-Value Mappings
-- Junction table to map pain points to value propositions
CREATE TABLE pain_value_mappings (
    id SERIAL PRIMARY KEY,
    pain_point_id INTEGER NOT NULL REFERENCES pain_points(id) ON DELETE CASCADE,
    value_prop_id INTEGER NOT NULL REFERENCES value_propositions(id) ON DELETE CASCADE,
    explanation TEXT, -- Explanation of how the value prop addresses the pain point
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(pain_point_id, value_prop_id) -- Prevent duplicate mappings
);
CREATE INDEX idx_mappings_pain ON pain_value_mappings(pain_point_id); -- For fetching mappings by pain point
CREATE INDEX idx_mappings_value ON pain_value_mappings(value_prop_id); -- For fetching mappings by value proposition

-- 10. Outreach Sequences
CREATE TABLE outreach_sequences (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES account_profiles(id) ON DELETE CASCADE,
    persona_id INTEGER REFERENCES personas(id) ON DELETE CASCADE,
    sequence_name VARCHAR(255) NOT NULL, -- A descriptive name for this outreach strategy. eg., "CTO Intro Sequence"
    objective TEXT, -- The main goal of the outreach sequence
    total_touches INTEGER, -- Total number of touchpoints in the sequence
    duration_days INTEGER, -- Total duration of the sequence in days
    sort_order INTEGER DEFAULT 0, -- For ordering sequences
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_sequences_profile ON outreach_sequences(profile_id); -- For fetching sequences by profile
CREATE INDEX idx_sequences_persona ON outreach_sequences(persona_id); -- For filtering sequences by persona

-- 11. Sequence Steps
CREATE TABLE sequence_steps (
    id SERIAL PRIMARY KEY,
    sequence_id INTEGER NOT NULL REFERENCES outreach_sequences(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL, -- The order of this step in the sequence (1, 2, 3, ...)
    touch_type touch_channel NOT NULL, -- e.g., email, linkedin, phone
    timing_days INTEGER NOT NULL, -- Days after the previous step to execute this step
    subject_line VARCHAR(500), 
    content_suggestion TEXT, 
    objective TEXT, 
    notes TEXT, 
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(sequence_id, step_number) -- Ensure unique step numbers per sequence
);