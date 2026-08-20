export type LayerName = "hospitals" | "roads" | "rivers" | "buildings" | "population" | "administrative_boundaries";

export type GeoJsonFeature = {
  type: "Feature";
  id?: string | number;
  properties: Record<string, unknown>;
  geometry: GeoJSON.Geometry;
};

export type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
  name?: string;
};

export type LayerSummary = {
  name: LayerName;
  featureCount: number;
  description: string;
};

export type GeoIntent = {
  operation: string;
  target_layer?: LayerName | null;
  reference_layer?: LayerName | null;
  distance_km?: number | null;
  filters?: Record<string, unknown>;
  wants_rag?: boolean;
  supported?: boolean;
};

export type Candidate = {
  rank: number;
  location: [number, number];
  suitability_score: number;
  factors: {
    population_coverage: {
      score: number;
      weight: number;
      description: string;
    };
    road_accessibility: {
      score: number;
      weight: number;
      description: string;
      nearest_road_km?: number;
    };
    healthcare_gap: {
      score: number;
      weight: number;
      description: string;
      nearest_hospital_km: number;
    };
  };
  reason: string;
  coordinates: {
    lon: number;
    lat: number;
  };
};

export type GeoResponse = {
  query: string;
  mode: "demo" | "real";
  intent: GeoIntent;
  explanation: string;
  summary: Record<string, unknown>;
  selected_tool: string;
  spatial_operation: string;
  result_count: number;
  sources: string[];
  recommended_locations: Array<Record<string, unknown> | Candidate>;
  geojson: GeoJsonFeatureCollection;
  supported: boolean;
  message?: string | null;
};

export type HealthResponse = {
  status: string;
  service: string;
  requested_mode: string;
  active_mode: string;
  demo_mode: boolean;
  real_data_ready: boolean;
  layers: string[];
};
