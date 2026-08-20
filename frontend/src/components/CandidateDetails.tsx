import "./CandidateDetails.css";
import type { Candidate } from "../lib/types";

interface CandidateDetailsProps {
  candidate: Candidate | null;
  rank: number | null;
}

export function CandidateDetails({ candidate, rank }: CandidateDetailsProps) {
  if (!candidate || rank === null) {
    return (
      <div className="candidate-details empty">
        <p>Select a candidate to view details</p>
      </div>
    );
  }

  const factors = candidate.factors;
  const locationStr = `${candidate.coordinates.lat.toFixed(4)}°N, ${candidate.coordinates.lon.toFixed(4)}°E`;

  return (
    <div className="candidate-details">
      <div className="details-header">
        <h3>Candidate #{rank + 1} - Details</h3>
        <div className="overall-score">
          <div className="score-circle">
            <div className="score-value">{candidate.suitability_score}%</div>
            <div className="score-text">Suitability</div>
          </div>
        </div>
      </div>

      <div className="details-location">
        <h4>Location</h4>
        <div className="location-box">
          <div className="coord-row">
            <span className="coord-label">Latitude:</span>
            <span className="coord-value">{candidate.coordinates.lat.toFixed(6)}</span>
          </div>
          <div className="coord-row">
            <span className="coord-label">Longitude:</span>
            <span className="coord-value">{candidate.coordinates.lon.toFixed(6)}</span>
          </div>
          <div className="coord-text">{locationStr}</div>
        </div>
      </div>

      <div className="details-factors">
        <h4>Scoring Breakdown</h4>

        {/* Population Coverage Factor */}
        <div className="factor-detail">
          <div className="factor-header">
            <div className="factor-name">
              <span className="factor-icon">👥</span>
              Population Coverage
            </div>
            <div className="factor-weight">40% weight</div>
          </div>
          <div className="factor-description">{factors.population_coverage.description}</div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${factors.population_coverage.score}%` }}
            >
              <span className="progress-text">{factors.population_coverage.score}%</span>
            </div>
          </div>
          <div className="factor-interpretation">
            {factors.population_coverage.score > 70
              ? "✓ Excellent - Located in a high-population density area"
              : factors.population_coverage.score > 40
                ? "○ Good - Located in a moderate-population area"
                : "✗ Lower - Located in a low-population area"}
          </div>
        </div>

        {/* Road Accessibility Factor */}
        <div className="factor-detail">
          <div className="factor-header">
            <div className="factor-name">
              <span className="factor-icon">🛣️</span>
              Road Accessibility
            </div>
            <div className="factor-weight">30% weight</div>
          </div>
          <div className="factor-description">{factors.road_accessibility.description}</div>
          {factors.road_accessibility.nearest_road_km !== undefined && (
            <div className="detail-metric">
              Nearest major road: <strong>{factors.road_accessibility.nearest_road_km} km</strong>
            </div>
          )}
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${factors.road_accessibility.score}%` }}
            >
              <span className="progress-text">{factors.road_accessibility.score}%</span>
            </div>
          </div>
          <div className="factor-interpretation">
            {factors.road_accessibility.score > 70
              ? "✓ Excellent - Very close to major roads"
              : factors.road_accessibility.score > 40
                ? "○ Good - Reasonably accessible by road"
                : "✗ Lower - Some distance from major roads"}
          </div>
        </div>

        {/* Healthcare Gap Factor */}
        <div className="factor-detail">
          <div className="factor-header">
            <div className="factor-name">
              <span className="factor-icon">🏥</span>
              Healthcare Gap
            </div>
            <div className="factor-weight">30% weight</div>
          </div>
          <div className="factor-description">{factors.healthcare_gap.description}</div>
          <div className="detail-metric">
            Nearest existing hospital: <strong>{factors.healthcare_gap.nearest_hospital_km} km</strong>
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${factors.healthcare_gap.score}%` }}
            >
              <span className="progress-text">{factors.healthcare_gap.score}%</span>
            </div>
          </div>
          <div className="factor-interpretation">
            {factors.healthcare_gap.score > 70
              ? "✓ Excellent - Significant gap from existing hospitals"
              : factors.healthcare_gap.score > 40
                ? "○ Good - Moderate gap from existing hospitals"
                : "✗ Lower - Close to existing hospitals"}
          </div>
        </div>
      </div>

      <div className="details-recommendation">
        <h4>Recommendation</h4>
        <div className="reason-box">{candidate.reason}</div>
      </div>

      <div className="details-methodology">
        <h4>Methodology</h4>
        <div className="methodology-text">
          <p>
            This candidate site was evaluated using a transparent, multi-factor scoring approach:
          </p>
          <ul>
            <li>
              <strong>Population Coverage (40%):</strong> Measures proximity to high-population
              density areas using WorldPop 2025 raster data at 1km resolution.
            </li>
            <li>
              <strong>Road Accessibility (30%):</strong> Calculates distance to major road
              networks from OpenStreetMap data.
            </li>
            <li>
              <strong>Healthcare Gap (30%):</strong> Identifies underserved areas by measuring
              distance from existing hospitals in OpenStreetMap.
            </li>
          </ul>
          <p>
            The final score is a weighted sum of these three factors, normalized to a 0-100 scale.
          </p>
        </div>
      </div>

      <div className="details-disclaimer">
        <p>
          <strong>⚠️ Important Disclaimer:</strong>
        </p>
        <p>
          This AI-generated suitability analysis is for demonstration purposes only and is NOT a
          substitute for professional urban planning, medical facility planning, or government
          recommendations. Any actual hospital site selection should involve:
        </p>
        <ul>
          <li>Professional urban planners and geographic consultants</li>
          <li>Medical facility experts and healthcare administrators</li>
          <li>Government planning authorities and regulatory bodies</li>
          <li>Environmental impact assessments</li>
          <li>Community engagement and public hearings</li>
          <li>Detailed site-specific surveys and feasibility studies</li>
        </ul>
        <p>
          This analysis uses real datasets (OpenStreetMap, WorldPop) but represents a simplified
          model of a complex planning decision.
        </p>
      </div>
    </div>
  );
}
