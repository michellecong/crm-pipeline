// TypeScript types matching backend API schemas

export interface Product {
  product_name: string;
  description: string;
  source_url?: string;
}

export type PersonaTier = "tier_1" | "tier_2" | "tier_3";

export interface BuyerPersona {
  persona_name: string;
  tier: PersonaTier;
  job_titles: string[];
  excluded_job_titles: string[];
  industry: string;
  company_size_range: string;
  company_type: string;
  location: string;
  description: string;
}

export interface PainPointMapping {
  pain_point: string;
  value_proposition: string;
}

export interface PersonaWithMappings {
  persona_name: string;
  mappings: PainPointMapping[];
}

export type TouchType = "email" | "linkedin" | "phone" | "video";

export interface SequenceTouch {
  sort_order: number;
  touch_type: TouchType;
  timing_days: number;
  objective: string;
  subject_line?: string;
  content_suggestion: string;
  hints?: string;
}

export interface OutreachSequence {
  name: string;
  persona_name: string;
  objective: string;
  touches: SequenceTouch[];
}

export interface PipelineGenerateRequest {
  company_name: string;
  generate_count?: number;
  use_llm_search?: boolean;
  provider?: "google" | "perplexity";
}

export interface PipelineStatistics {
  total_runtime_seconds: number;
  step_runtimes: Record<string, number>;
  total_tokens: number;
  step_tokens: Record<string, number>;
  token_breakdown: Record<string, {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  }>;
}

export interface PipelineArtifacts {
  products_file?: string;
  personas_file?: string;
  mappings_file?: string;
  sequences_file?: string;
}

export interface PipelinePayload {
  products: Product[];
  personas: BuyerPersona[];
  personas_with_mappings: PersonaWithMappings[];
  sequences: OutreachSequence[];
}

export interface PipelineGenerateEnvelope {
  payload: PipelinePayload;
  artifacts?: PipelineArtifacts;
  statistics?: PipelineStatistics;
}

