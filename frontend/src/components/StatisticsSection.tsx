import type { PipelineStatistics } from "../types/api";
import "./Section.css";

interface StatisticsSectionProps {
  statistics: PipelineStatistics;
}

export default function StatisticsSection({
  statistics,
}: StatisticsSectionProps) {
  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds.toFixed(2)}s`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${mins}m ${secs}s`;
  };

  const formatTokens = (tokens: number) => {
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  };

  return (
    <section className="section statistics-section">
      <h2 className="section-title">Generation Statistics</h2>
      <div className="statistics-grid">
        <div className="stat-card">
          <div className="stat-label">Total Runtime</div>
          <div className="stat-value">
            {formatTime(statistics.total_runtime_seconds)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Tokens</div>
          <div className="stat-value">
            {formatTokens(statistics.total_tokens)}
          </div>
        </div>
      </div>

      <div className="step-statistics">
        <h3>Step Statistics</h3>
        <div className="step-stats-grid">
          {Object.entries(statistics.step_runtimes).map(([step, runtime]) => (
            <div key={step} className="step-stat-card">
              <div className="step-name">{step}</div>
              <div className="step-details">
                <div>Runtime: {formatTime(runtime)}</div>
                <div>
                  Tokens: {formatTokens(statistics.step_tokens[step] || 0)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
