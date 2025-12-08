import axios from "axios";
import type {
  PipelineGenerateRequest,
  PipelineGenerateEnvelope,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const pipelineApi = {
  /**
   * Generate four-stage content: products → personas → mappings → sequences
   */
  async generatePipeline(
    request: PipelineGenerateRequest
  ): Promise<PipelineGenerateEnvelope> {
    const response = await apiClient.post<PipelineGenerateEnvelope>(
      "/api/v1/llm/pipeline/generate",
      {
        company_name: request.company_name,
        generate_count: request.generate_count || 5,
        use_llm_search: request.use_llm_search,
        provider: request.provider,
      }
    );
    return response.data;
  },
};

export default apiClient;
