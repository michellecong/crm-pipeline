-- ENUM TYPES
-- Persona tier classification (decision makers, influencers, end users)
CREATE TYPE persona_tier AS ENUM ('tier_1', 'tier_2', 'tier_3');

-- Touch channel types for outreach sequences
CREATE TYPE touch_channel AS ENUM ('email', 'linkedin', 'phone', 'video', 'direct_mail', 'meeting');

-- Pain point scope (company-level vs persona-specific)
CREATE TYPE pain_point_scope AS ENUM ('global', 'persona_specific');

-- Data source types
CREATE TYPE source_type AS ENUM ('website', 'file');

-- Content pack generation status
CREATE TYPE pack_status AS ENUM ('pending', 'generating', 'completed', 'failed');

-- 1. USERS TABLE

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

COMMENT ON TABLE users IS 'System users (sales team members)';
COMMENT ON COLUMN users.email IS 'Unique email address for authentication';

-- 2. COMPANIES TABLE

CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Company basic information
    name VARCHAR(255) NOT NULL,
    size INTEGER, -- Number of employees
    company_location VARCHAR(255), -- Headquarters location
    industry VARCHAR(100),
    domain TEXT, -- Company website domain (e.g., "acme.com")
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_company_per_user UNIQUE(user_id, domain)
);

CREATE INDEX idx_companies_user ON companies(user_id);
CREATE INDEX idx_companies_domain ON companies(domain);

COMMENT ON TABLE companies IS 'Target companies/accounts for content generation';
COMMENT ON COLUMN companies.domain IS 'Company website domain, used for web scraping';
COMMENT ON COLUMN companies.size IS 'Number of employees (approximate)';

-- 3. CONVERSATIONS TABLE

CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    title VARCHAR(255), -- Auto-generated or user-defined conversation title
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_company ON conversations(company_id);

COMMENT ON TABLE conversations IS 'Conversation sessions for content pack building';
COMMENT ON COLUMN conversations.title IS 'Descriptive title for the conversation (e.g., "Acme Corp Content Generation")';

-- 4. CONVERSATION MESSAGES TABLE

CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')), -- User or AI assistant
    content TEXT NOT NULL, -- Message content
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation ON conversation_messages(conversation_id);
CREATE INDEX idx_messages_created_at ON conversation_messages(conversation_id, created_at);

COMMENT ON TABLE conversation_messages IS 'Individual messages within a conversation';
COMMENT ON COLUMN conversation_messages.role IS 'Message sender: "user" or "assistant" (AI)';
COMMENT ON COLUMN conversation_messages.content IS 'Full message text content';

-- 5. DATA SOURCES TABLE

CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES conversation_messages(id) ON DELETE SET NULL, -- Message that created this source
    
    -- Source identification
    source_type source_type NOT NULL, -- 'website' or 'file'
    
    -- Source details (flexible naming to support both files and websites)
    file_name VARCHAR(255), -- Original filename (for files) or page title (for websites)
    website_url TEXT, -- URL for websites or file storage path for files
    
    -- Content metadata
    title VARCHAR(500), -- Descriptive title
    content_preview TEXT, -- First 500 characters preview
    text_length INTEGER, -- Total character count of extracted text
    total_chunks INTEGER, -- Number of chunks this source was split into
    file_size_bytes BIGINT, -- File size in bytes (for files)
    
    -- Timestamps
    scraped_at TIMESTAMPTZ, -- When website was scraped
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_sources_conversation ON data_sources(conversation_id);
CREATE INDEX idx_data_sources_message ON data_sources(message_id);
CREATE INDEX idx_data_sources_type ON data_sources(source_type);

COMMENT ON TABLE data_sources IS 'Data sources (uploaded files or scraped websites) used for content generation';
COMMENT ON COLUMN data_sources.conversation_id IS 'Conversation this data source belongs to (sources are available throughout the conversation)';
COMMENT ON COLUMN data_sources.message_id IS 'Message where this source was created (for tracking purposes)';
COMMENT ON COLUMN data_sources.website_url IS 'URL for websites or storage path for files (e.g., "/uploads/user_123/contacts.csv" or "https://acme.com")';
COMMENT ON COLUMN data_sources.content_preview IS 'Preview of content for UI display';
COMMENT ON COLUMN data_sources.text_length IS 'Total length of extracted/scraped text in characters';

-- 6. SOURCE CHUNKS TABLE

CREATE TABLE source_chunks (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    
    chunks_content TEXT NOT NULL, -- Text content of this chunk
    chunks_index INTEGER NOT NULL, -- Position in the original document (0-based)
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chunks_source ON source_chunks(source_id);
CREATE INDEX idx_chunks_source_index ON source_chunks(source_id, chunks_index);

COMMENT ON TABLE source_chunks IS 'Text chunks from data sources (for RAG - Retrieval Augmented Generation)';
COMMENT ON COLUMN source_chunks.chunks_content IS 'Text content of this chunk (typically 500-1000 characters)';
COMMENT ON COLUMN source_chunks.chunks_index IS 'Sequential position of this chunk in the original document';

-- 7. CONTENT PACKS TABLE

CREATE TABLE content_packs (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
    
    -- Version control
    version INTEGER DEFAULT 1, -- Version number for iterative refinement
    is_active BOOLEAN DEFAULT true, -- Only one active pack per company
    
    -- Generation status and metadata
    status pack_status DEFAULT 'pending',
    model_used VARCHAR(50), -- LLM model name (e.g., "gpt-4-turbo", "claude-sonnet-4")
    
    -- LLM cost tracking
    generation_time_seconds INTEGER, -- Total generation time
    prompt_tokens INTEGER, -- Input tokens used
    completion_tokens INTEGER, -- Output tokens generated
    generation_cost DECIMAL(10, 4), -- Cost in dollars
    
    -- Generated content summaries
    company_overview TEXT, -- AI-generated company overview
    pack_summary TEXT, -- Summary of the entire content pack
    data_source_summary TEXT, -- Summary of data sources used
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_version_per_company UNIQUE(company_id, version)
);

CREATE INDEX idx_packs_company ON content_packs(company_id);
CREATE INDEX idx_packs_conversation ON content_packs(conversation_id);
CREATE INDEX idx_packs_active ON content_packs(company_id, is_active) WHERE is_active = true;
CREATE INDEX idx_packs_version ON content_packs(company_id, version DESC);

COMMENT ON TABLE content_packs IS 'Generated sales content packages with versioning support';
COMMENT ON COLUMN content_packs.version IS 'Version number - allows multiple iterations per company';
COMMENT ON COLUMN content_packs.is_active IS 'Only one pack should be active (current version) per company';
COMMENT ON COLUMN content_packs.conversation_id IS 'Conversation where this pack was generated';
COMMENT ON COLUMN content_packs.model_used IS 'LLM model identifier for tracking which AI generated this content';
COMMENT ON COLUMN content_packs.generation_cost IS 'Total API cost for generating this pack (in USD)';

-- 8. PERSONAS TABLE

CREATE TABLE personas (
    id SERIAL PRIMARY KEY,
    pack_id INTEGER NOT NULL REFERENCES content_packs(id) ON DELETE CASCADE,
    
    -- Basic persona information
    name VARCHAR(255) NOT NULL, -- Person's name (if known) or role title
    tier persona_tier NOT NULL, -- Decision maker tier classification
    job_title VARCHAR(200), -- Job title
    
    -- Contact information (optional, if available from data sources)
    department VARCHAR(100), -- Department/function
    location VARCHAR(255), -- Geographic location
    email VARCHAR(255), -- Email address
    phone VARCHAR(50), -- Phone number
    linkedin_url TEXT, -- LinkedIn profile URL
    
    -- AI-generated insights
    description TEXT, -- Detailed description of the persona
    decision_power VARCHAR(50), -- Level of decision-making authority (e.g., "final decision maker", "influencer")
    
    -- Communication preferences (JSONB for flexibility)
    communication_preferences JSONB, -- Preferred channels, timing, tone, etc.
    
    -- Ordering
    sort_order INTEGER DEFAULT 0, -- For custom ordering within the pack
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_personas_pack ON personas(pack_id);
CREATE INDEX idx_personas_tier ON personas(pack_id, tier);
CREATE INDEX idx_personas_sort ON personas(pack_id, sort_order);

COMMENT ON TABLE personas IS 'Target personas (decision makers, influencers, end users) for the account';
COMMENT ON COLUMN personas.tier IS 'Priority tier: tier_1 (decision makers), tier_2 (influencers), tier_3 (end users)';
COMMENT ON COLUMN personas.decision_power IS 'Level of decision-making authority (e.g., "final decision maker", "influencer", "end user")';
COMMENT ON COLUMN personas.communication_preferences IS 'JSON object with preferred communication channels, timing, tone, etc. Example: {"preferred_channel": "email", "best_time": "Tuesday mornings", "tone": "technical"}';
COMMENT ON COLUMN personas.sort_order IS 'Custom ordering for display purposes (lower values appear first)';

-- 9. PAIN POINTS TABLE

CREATE TABLE pain_points (
    id SERIAL PRIMARY KEY,
    pack_id INTEGER NOT NULL REFERENCES content_packs(id) ON DELETE CASCADE,
    persona_id INTEGER REFERENCES personas(id) ON DELETE CASCADE, -- NULL for global pain points
    
    -- Pain point classification
    scope pain_point_scope NOT NULL DEFAULT 'global', -- 'global' (company-level) or 'persona_specific'
    
    -- Pain point details
    name VARCHAR(255), -- Short name/title for the pain point
    description TEXT NOT NULL, -- Detailed description of the pain point
    category VARCHAR(100), -- Category (e.g., "operational", "financial", "strategic")
    priority VARCHAR(20), -- Priority level (e.g., "high", "medium", "low")
    
    -- Ordering
    sort_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pain_points_pack ON pain_points(pack_id);
CREATE INDEX idx_pain_points_persona ON pain_points(persona_id);
CREATE INDEX idx_pain_points_scope ON pain_points(scope);
CREATE INDEX idx_pain_points_sort ON pain_points(pack_id, sort_order);

COMMENT ON TABLE pain_points IS 'Identified pain points for the target account';
COMMENT ON COLUMN pain_points.scope IS 'Pain point scope: "global" for company-level issues, "persona_specific" for individual persona challenges';
COMMENT ON COLUMN pain_points.persona_id IS 'Associated persona (NULL for global pain points that affect the entire company)';
COMMENT ON COLUMN pain_points.category IS 'Pain point category for grouping (e.g., "operational efficiency", "cost reduction", "scalability")';

-- 10. VALUE PROPOSITIONS TABLE

CREATE TABLE value_propositions (
    id SERIAL PRIMARY KEY,
    pack_id INTEGER NOT NULL REFERENCES content_packs(id) ON DELETE CASCADE,
    persona_id INTEGER REFERENCES personas(id) ON DELETE CASCADE, -- NULL for global value props
    
    -- Value proposition details
    name VARCHAR(255), -- Short name/title
    description TEXT NOT NULL, -- Detailed description of the value proposition
    category VARCHAR(100), -- Category (e.g., "cost_saving", "efficiency", "innovation")
    
    -- Ordering
    sort_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_value_props_pack ON value_propositions(pack_id);
CREATE INDEX idx_value_props_persona ON value_propositions(persona_id);
CREATE INDEX idx_value_props_sort ON value_propositions(pack_id, sort_order);

COMMENT ON TABLE value_propositions IS 'Value propositions tailored to address identified pain points';
COMMENT ON COLUMN value_propositions.persona_id IS 'Target persona (NULL for company-level value propositions)';
COMMENT ON COLUMN value_propositions.category IS 'Value category (e.g., "roi", "efficiency_gain", "risk_reduction")';

-- 11. PAIN-VALUE MAPPINGS TABLE

CREATE TABLE pain_value_mappings (
    id SERIAL PRIMARY KEY,
    pain_point_id INTEGER NOT NULL REFERENCES pain_points(id) ON DELETE CASCADE,
    value_proposition_id INTEGER NOT NULL REFERENCES value_propositions(id) ON DELETE CASCADE,
    
    relevance_description TEXT, -- Explanation of how the value prop addresses the pain point
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_pain_value_mapping UNIQUE(pain_point_id, value_proposition_id)
);

CREATE INDEX idx_mappings_pain ON pain_value_mappings(pain_point_id);
CREATE INDEX idx_mappings_value ON pain_value_mappings(value_proposition_id);

COMMENT ON TABLE pain_value_mappings IS 'Many-to-many relationship mapping pain points to value propositions';
COMMENT ON COLUMN pain_value_mappings.relevance_description IS 'Explanation of how this value proposition specifically addresses the pain point';

-- 12. PRODUCT OFFERINGS TABLE

CREATE TABLE product_offerings (
    id SERIAL PRIMARY KEY,
    pack_id INTEGER NOT NULL REFERENCES content_packs(id) ON DELETE CASCADE,
    
    -- Product details
    name VARCHAR(255) NOT NULL, -- Product/service name
    description TEXT, -- Product description
    
    -- Relevance to this account
    relevance_score DECIMAL(3, 2), -- Relevance score (0.00 to 1.00)
    relevance_description TEXT, -- AI-generated explanation of why this product is recommended
    
    -- Ordering
    sort_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_pack ON product_offerings(pack_id);
CREATE INDEX idx_products_relevance ON product_offerings(pack_id, relevance_score DESC);
CREATE INDEX idx_products_sort ON product_offerings(pack_id, sort_order);

COMMENT ON TABLE product_offerings IS 'Recommended products/services matched to the target account';
COMMENT ON COLUMN product_offerings.relevance_score IS 'AI-calculated relevance score (0.00 = not relevant, 1.00 = highly relevant)';
COMMENT ON COLUMN product_offerings.relevance_description IS 'AI-generated reasoning for why this product is recommended for this account';

-- 13. OUTREACH SEQUENCES TABLE

CREATE TABLE outreach_sequences (
    id SERIAL PRIMARY KEY,
    pack_id INTEGER NOT NULL REFERENCES content_packs(id) ON DELETE CASCADE,
    persona_id INTEGER REFERENCES personas(id) ON DELETE CASCADE, -- NULL for generic sequences
    
    -- Sequence metadata
    name VARCHAR(255) NOT NULL, -- Descriptive name (e.g., "VP Engineering Outreach Sequence")
    objective TEXT, -- Overall goal of the sequence
    
    -- Sequence statistics
    total_touches INTEGER, -- Total number of touchpoints in this sequence
    duration_days INTEGER, -- Total duration from first to last touch
    
    -- Ordering
    sort_orders INTEGER DEFAULT 0, -- Typo in your diagram, keeping as-is for consistency
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sequences_pack ON outreach_sequences(pack_id);
CREATE INDEX idx_sequences_persona ON outreach_sequences(persona_id);
CREATE INDEX idx_sequences_sort ON outreach_sequences(pack_id, sort_orders);

COMMENT ON TABLE outreach_sequences IS 'Multi-touch outreach sequences tailored to specific personas';
COMMENT ON COLUMN outreach_sequences.persona_id IS 'Target persona for this sequence (NULL for generic sequences applicable to multiple personas)';
COMMENT ON COLUMN outreach_sequences.total_touches IS 'Total number of touchpoints/steps in this sequence';
COMMENT ON COLUMN outreach_sequences.duration_days IS 'Total sequence duration from first touch to last (in days)';

-- 14. SEQUENCES TOUCHES TABLE

CREATE TABLE sequences_touches (
    id SERIAL PRIMARY KEY,
    sequence_id INTEGER NOT NULL REFERENCES outreach_sequences(id) ON DELETE CASCADE,
    
    -- Touch metadata
    sort_order INTEGER NOT NULL, -- Position in the sequence (1, 2, 3, ...)
    touch_type touch_channel NOT NULL, -- Communication channel
    
    -- Timing
    timing_days INTEGER NOT NULL, -- Days from the previous touch (0 for first touch)
    
    -- Touch details
    objective TEXT, -- Goal of this specific touch
    subject_line VARCHAR(500), -- Email subject line or message title
    content_suggestion TEXT, -- Suggested content/template for this touch
    hints TEXT, -- Additional hints or notes for execution
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_touch_in_sequence UNIQUE(sequence_id, sort_order)
);

CREATE INDEX idx_touches_sequence ON sequences_touches(sequence_id);
CREATE INDEX idx_touches_order ON sequences_touches(sequence_id, sort_order);

COMMENT ON TABLE sequences_touches IS 'Individual touchpoints/steps within an outreach sequence';
COMMENT ON COLUMN sequences_touches.sort_order IS 'Position in the sequence (1 = first touch, 2 = second touch, etc.)';
COMMENT ON COLUMN sequences_touches.timing_days IS 'Number of days after the previous touch to execute this step (0 for the first touch)';
COMMENT ON COLUMN sequences_touches.subject_line IS 'Suggested email subject line or message title';
COMMENT ON COLUMN sequences_touches.content_suggestion IS 'AI-generated content template or talking points for this touch';
COMMENT ON COLUMN sequences_touches.hints IS 'Execution hints (e.g., "Reference their recent blog post", "Mention mutual connection")';

-- 15. CITATIONS TABLE

CREATE TABLE citations (
    id SERIAL PRIMARY KEY,
    
    -- Polymorphic relationship (entity can be persona, pain_point, value_proposition, etc.)
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN (
        'persona',
        'pain_point',
        'value_proposition',
        'product_offering',
        'outreach_sequence',
        'company_overview'
    )),
    entity_id INTEGER NOT NULL, -- ID of the entity being cited
    
    -- Source reference
    source_chunk_id INTEGER NOT NULL REFERENCES source_chunks(id) ON DELETE CASCADE,
    
    -- Citation details
    relevance_score DECIMAL(3, 2), -- How relevant this source is to the entity (0.00 to 1.00)
    excerpt TEXT, -- Specific text excerpt from the source that supports this entity
    reasoning TEXT, -- AI explanation of why this source supports the entity
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_entity_source_citation UNIQUE(entity_type, entity_id, source_chunk_id)
);

CREATE INDEX idx_citations_entity ON citations(entity_type, entity_id);
CREATE INDEX idx_citations_chunk ON citations(source_chunk_id);

COMMENT ON TABLE citations IS 'Citations linking generated content entities back to source data (for transparency and verification)';
COMMENT ON COLUMN citations.entity_type IS 'Type of entity being cited (persona, pain_point, value_proposition, product_offering, outreach_sequence, or company_overview)';
COMMENT ON COLUMN citations.entity_id IS 'ID of the entity in its respective table (polymorphic foreign key)';
COMMENT ON COLUMN citations.source_chunk_id IS 'Reference to the specific text chunk that supports this entity';
COMMENT ON COLUMN citations.excerpt IS 'Relevant excerpt from the source chunk (typically 200-500 characters)';
COMMENT ON COLUMN citations.reasoning IS 'AI-generated explanation of how this source supports the generated content';

-- TRIGGERS FOR AUTOMATIC TIMESTAMP UPDATES

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at column
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_packs_updated_at
    BEFORE UPDATE ON content_packs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
