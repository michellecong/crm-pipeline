import type { PersonaWithMappings } from "../types/api";
import "./Section.css";

interface MappingsSectionProps {
  personasWithMappings: PersonaWithMappings[];
}

export default function MappingsSection({
  personasWithMappings,
}: MappingsSectionProps) {
  return (
    <section className="section">
      <h2 className="section-title">
        Pain-Point Mappings ({personasWithMappings.length} personas)
      </h2>
      <div className="mappings-container">
        {personasWithMappings.map((personaMapping, index) => (
          <div key={index} className="mapping-group">
            <h3 className="mapping-persona-name">
              {personaMapping.persona_name}
            </h3>
            <div className="mappings-list">
              {personaMapping.mappings.map((mapping, mapIndex) => (
                <div key={mapIndex} className="mapping-card">
                  <div className="mapping-pain-point">
                    <strong>Pain Point:</strong>
                    <p>{mapping.pain_point}</p>
                  </div>
                  <div className="mapping-arrow">→</div>
                  <div className="mapping-value-prop">
                    <strong>Value Proposition:</strong>
                    <p>{mapping.value_proposition}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
