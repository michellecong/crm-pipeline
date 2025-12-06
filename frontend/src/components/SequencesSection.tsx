import type { OutreachSequence } from "../types/api";
import "./Section.css";

interface SequencesSectionProps {
  sequences: OutreachSequence[];
}

const touchTypeLabels: Record<string, string> = {
  email: "Email",
  linkedin: "LinkedIn",
  phone: "Phone",
  video: "Video",
};

const touchTypeIcons: Record<string, string> = {
  email: "📧",
  linkedin: "💼",
  phone: "📞",
  video: "🎥",
};

export default function SequencesSection({ sequences }: SequencesSectionProps) {
  return (
    <section className="section">
      <h2 className="section-title">Outreach Sequences ({sequences.length})</h2>
      <div className="sequences-container">
        {sequences.map((sequence, index) => (
          <div key={index} className="sequence-card">
            <div className="sequence-header">
              <h3 className="sequence-name">{sequence.name}</h3>
              <span className="sequence-persona">
                Target Persona: {sequence.persona_name}
              </span>
            </div>
            <p className="sequence-objective">
              <strong>Objective:</strong>
              {sequence.objective}
            </p>
            <div className="touches-list">
              {sequence.touches.map((touch) => (
                <div key={touch.sort_order} className="touch-card">
                  <div className="touch-header">
                    <span className="touch-order">#{touch.sort_order}</span>
                    <span className="touch-type">
                      {touchTypeIcons[touch.touch_type]}{" "}
                      {touchTypeLabels[touch.touch_type]}
                    </span>
                    <span className="touch-timing">
                      Day {touch.timing_days}
                    </span>
                  </div>
                  <div className="touch-content">
                    <div className="touch-objective">
                      <strong>Objective:</strong>
                      {touch.objective}
                    </div>
                    {touch.subject_line && (
                      <div className="touch-subject">
                        <strong>Subject:</strong>
                        {touch.subject_line}
                      </div>
                    )}
                    <div className="touch-suggestion">
                      <strong>Content Suggestion:</strong>
                      <p>{touch.content_suggestion}</p>
                    </div>
                    {touch.hints && (
                      <div className="touch-hints">
                        <strong>Hints:</strong>
                        {touch.hints}
                      </div>
                    )}
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
