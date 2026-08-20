import { useState } from "react";
import type { GeoResponse, Candidate } from "../lib/types";
import "./HospitalCandidates.css";

interface HospitalCandidatesProps {
  data: GeoResponse | null;
  loading: boolean;
  onSelectCandidate: (candidate: Candidate, index: number) => void;
  selectedIndex: number | null;
}

export function HospitalCandidates({
  data,
  loading,
  onSelectCandidate,
  selectedIndex,
}: HospitalCandidatesProps) {
  const candidates = (data?.recommended_locations || []) as Candidate[];

  if (loading) {
    return (
      <div className="hospital-candidates loading">
        <div className="spinner"></div>
        <p>Analyzing candidate locations...</p>
      </div>
    );
  }

  if (!data || candidates.length === 0) {
    return (
      <div className="hospital-candidates empty">
        <p>No candidates found. Click "Find Best Hospital Location" to get started.</p>
      </div>
    );
  }

  return (
    <div className="hospital-candidates">
      <div className="candidates-header">
        <h3>Top 5 Recommended Hospital Locations</h3>
        <div className="scoring-info">
          <small>
            Score calculation: Population Coverage (40%) + Road Accessibility (30%) + Healthcare Gap (30%)
          </small>
        </div>
      </div>

      <div className="candidates-list">
        {candidates.map((candidate: any, idx: number) => (
          <div
            key={idx}
            className={`candidate-card ${selectedIndex === idx ? "selected" : ""}`}
            onClick={() => onSelectCandidate(candidate, idx)}
          >
            <div className="candidate-rank-score">
              <div className="rank-badge">#{candidate.rank || idx + 1}</div>
              <div className="score-display">
                <div className="score-value">{candidate.suitability_score || 0}%</div>
                <div className="score-label">Suitability</div>
              </div>
            </div>

            <div className="candidate-factors">
              <div className="factor-item">
                <div className="factor-label">Population</div>
                <div className="factor-score">
                  {candidate.factors?.population_coverage?.score || 0}%
                </div>
              </div>
              <div className="factor-item">
                <div className="factor-label">Road Access</div>
                <div className="factor-score">
                  {candidate.factors?.road_accessibility?.score || 0}%
                </div>
              </div>
              <div className="factor-item">
                <div className="factor-label">Healthcare Gap</div>
                <div className="factor-score">
                  {candidate.factors?.healthcare_gap?.score || 0}%
                </div>
              </div>
            </div>

            <div className="candidate-location">
              <small className="coordinates">
                ({candidate.coordinates?.lon || 0}, {candidate.coordinates?.lat || 0})
              </small>
            </div>

            <div className="candidate-reason">
              <small>{candidate.reason}</small>
            </div>
          </div>
        ))}
      </div>

      <div className="disclaimer">
        <p>
          <strong>⚠️ Disclaimer:</strong> AI-generated suitability analysis for demonstration
          purposes and not a substitute for professional planning. This is not an actual medical,
          government, or official urban-planning recommendation.
        </p>
        <p>
          <strong>Data Sources:</strong> Population distribution from WorldPop 2025 (1km
          resolution). Existing hospitals, roads, and other features from OpenStreetMap.
        </p>
      </div>
    </div>
  );
}
