import type { BuyerPersona } from "../types/api";
import "./Section.css";

interface PersonasSectionProps {
  personas: BuyerPersona[];
}

const tierLabels: Record<string, string> = {
  tier_1: "Tier 1",
  tier_2: "Tier 2",
  tier_3: "Tier 3",
};

const tierColors: Record<string, string> = {
  tier_1: "#4CAF50",
  tier_2: "#FF9800",
  tier_3: "#9E9E9E",
};

export default function PersonasSection({ personas }: PersonasSectionProps) {
  return (
    <section className="section">
      <h2 className="section-title">Buyer Personas ({personas.length})</h2>
      <div className="personas-grid">
        {personas.map((persona, index) => (
          <div key={index} className="persona-card">
            <div className="persona-header">
              <h3 className="persona-name">{persona.persona_name}</h3>
              <span
                className="tier-badge"
                style={{ backgroundColor: tierColors[persona.tier] }}
              >
                {tierLabels[persona.tier]}
              </span>
            </div>

            <div className="persona-info">
              <div className="info-row">
                <span className="info-label">Industry:</span>
                <span>{persona.industry}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Company Size:</span>
                <span>{persona.company_size_range}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Company Type:</span>
                <span>{persona.company_type}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Location:</span>
                <span>{persona.location}</span>
              </div>
            </div>

            <p className="persona-description">{persona.description}</p>

            <div className="persona-tags">
              <div className="tags-group">
                <strong>Target Job Titles:</strong>
                <div className="tags">
                  {persona.job_titles.map((title, i) => (
                    <span key={i} className="tag tag-positive">
                      {title}
                    </span>
                  ))}
                </div>
              </div>
              <div className="tags-group">
                <strong>Excluded Job Titles:</strong>
                <div className="tags">
                  {persona.excluded_job_titles.map((title, i) => (
                    <span key={i} className="tag tag-negative">
                      {title}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
