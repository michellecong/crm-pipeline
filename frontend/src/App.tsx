import { useState, useEffect } from "react";
import { pipelineApi } from "./services/api";
import type { PipelineGenerateEnvelope } from "./types/api";
import ProductsSection from "./components/ProductsSection";
import PersonasSection from "./components/PersonasSection";
import MappingsSection from "./components/MappingsSection";
import SequencesSection from "./components/SequencesSection";
import StatisticsSection from "./components/StatisticsSection";
import "./App.css";

type TabType = "products" | "personas" | "mappings" | "sequences";

const STORAGE_KEY = "crm-pipeline-data";

function App() {
  const [companyName, setCompanyName] = useState("");
  const [generateCount, setGenerateCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PipelineGenerateEnvelope | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("products");
  const [showStatisticsModal, setShowStatisticsModal] = useState(false);

  // Load data from localStorage on mount
  useEffect(() => {
    const savedData = localStorage.getItem(STORAGE_KEY);
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        setData(parsed);
        // Set default tab based on available data
        if (parsed.payload?.products?.length > 0) {
          setActiveTab("products");
        }
      } catch (e) {
        console.error("Failed to parse saved data:", e);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  // Save data to localStorage whenever it changes
  useEffect(() => {
    if (data) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }
  }, [data]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!companyName.trim()) {
      setError("Please enter a company name");
      return;
    }

    if (loading) {
      return; // Prevent multiple submissions
    }

    setLoading(true);
    setError(null);
    // Don't clear data immediately - keep it visible until new data arrives

    try {
      const result = await pipelineApi.generatePipeline({
        company_name: companyName.trim(),
        generate_count: generateCount,
      });
      // Only set data if we successfully got a result
      if (result && result.payload) {
        setData(result);
        // Set default tab to products
        setActiveTab("products");
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Generation failed, please try again later");
      }
      console.error("Pipeline generation error:", err);
      // Don't clear existing data on error
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
            <div className="results-header">
              {data.statistics && (
                <button
                  className="statistics-button"
                  onClick={() => setShowStatisticsModal(true)}
                >
                  📊 View Statistics
                </button>
              )}
            </div>
            <div className="tabs-container">
              <div className="tabs-header">
                <button
                  className={`tab-button ${
                    activeTab === "products" ? "active" : ""
                  }`}
                  onClick={() => setActiveTab("products")}
                >
                  Products ({data.payload.products.length})
                </button>
                <button
                  className={`tab-button ${
                    activeTab === "personas" ? "active" : ""
                  }`}
                  onClick={() => setActiveTab("personas")}
                >
                  Personas ({data.payload.personas.length})
                </button>
                <button
                  className={`tab-button ${
                    activeTab === "mappings" ? "active" : ""
                  }`}
                  onClick={() => setActiveTab("mappings")}
                >
                  Mappings ({data.payload.personas_with_mappings.length})
                </button>
                <button
                  className={`tab-button ${
                    activeTab === "sequences" ? "active" : ""
                  }`}
                  onClick={() => setActiveTab("sequences")}
                >
                  Sequences ({data.payload.sequences.length})
                </button>
              </div>

              <div className="tabs-content">
                {activeTab === "products" && (
                  <ProductsSection products={data.payload.products} />
                )}
                {activeTab === "personas" && (
                  <PersonasSection personas={data.payload.personas} />
                )}
                {activeTab === "mappings" && (
                  <MappingsSection
                    personasWithMappings={data.payload.personas_with_mappings}
                  />
                )}
                {activeTab === "sequences" && (
                  <SequencesSection sequences={data.payload.sequences} />
                )}
              </div>
            </div>
          </div>
        )}

        {/* Statistics Modal */}
        {showStatisticsModal && data?.statistics && (
          <div
            className="modal-overlay"
            onClick={() => setShowStatisticsModal(false)}
          >
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Generation Statistics</h2>
                <button
                  className="modal-close"
                  onClick={() => setShowStatisticsModal(false)}
                >
                  ×
                </button>
              </div>
              <div className="modal-body">
                <StatisticsSection statistics={data.statistics} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
