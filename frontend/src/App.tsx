import { useState } from "react";
import { pipelineApi } from "./services/api";
import type { PipelineGenerateEnvelope } from "./types/api";
import ProductsSection from "./components/ProductsSection";
import PersonasSection from "./components/PersonasSection";
import MappingsSection from "./components/MappingsSection";
import SequencesSection from "./components/SequencesSection";
import StatisticsSection from "./components/StatisticsSection";
import "./App.css";

function App() {
  const [companyName, setCompanyName] = useState("");
  const [generateCount, setGenerateCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PipelineGenerateEnvelope | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) {
      setError("Please enter a company name");
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await pipelineApi.generatePipeline({
        company_name: companyName.trim(),
        generate_count: generateCount,
      });
      setData(result);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Generation failed, please try again later");
      }
      console.error("Pipeline generation error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>CRM Pipeline - Four-Stage Content Generation</h1>
        <p>
          Enter a company name to automatically generate products, personas,
          mappings, and sequences
        </p>
      </header>

      <main className="app-main">
        <form onSubmit={handleSubmit} className="input-form">
          <div className="form-group">
            <label htmlFor="company-name">Company Name</label>
            <input
              id="company-name"
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g., Salesforce"
              disabled={loading}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group form-group-inline">
              <label htmlFor="generate-count">
                Number of Personas to Generate
              </label>
              <input
                id="generate-count"
                type="number"
                value={generateCount}
                onChange={(e) =>
                  setGenerateCount(parseInt(e.target.value) || 5)
                }
                min={3}
                max={12}
                disabled={loading}
              />
            </div>

            <button type="submit" disabled={loading} className="submit-button">
              {loading ? "Generating..." : "Generate"}
            </button>
          </div>
        </form>

        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Generating content, please wait...</p>
          </div>
        )}

        {data && (
          <div className="results">
            {data.statistics && (
              <StatisticsSection statistics={data.statistics} />
            )}

            <ProductsSection products={data.payload.products} />

            <PersonasSection personas={data.payload.personas} />

            <MappingsSection
              personasWithMappings={data.payload.personas_with_mappings}
            />

            <SequencesSection sequences={data.payload.sequences} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
