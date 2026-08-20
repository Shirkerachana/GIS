import axios from "axios";
import type { GeoResponse, HealthResponse, LayerSummary, GeoJsonFeatureCollection } from "./types";

const apiBaseUrl = import.meta.env.DEV ? "http://localhost:8000" : window.location.origin;

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
});

export async function fetchHealth() {
  const { data } = await api.get("/api/health");
  return data as HealthResponse;
}

export async function fetchLayers() {
  const { data } = await api.get("/api/layers");
  return data.items as LayerSummary[];
}

export async function fetchLayer(layer: string) {
  const { data } = await api.get(`/api/${layer}`);
  return data as GeoJsonFeatureCollection;
}

export async function sendQuery(query: string, context: Record<string, unknown> = {}) {
  const { data } = await api.post("/api/chat", { query, context });
  return data as GeoResponse;
}

export async function analyzeNearby(payload: {
  target_layer: string;
  reference_layer: string;
  distance_km: number;
  filters?: Record<string, unknown>;
}) {
  const { data } = await api.post("/api/analysis/nearby", payload);
  return data as GeoResponse;
}

export async function analyzeSuitability(payload: {
  weights?: Record<string, number>;
  candidate_count?: number;
}) {
  const { data } = await api.post("/api/analysis/suitability", payload);
  return data as GeoResponse;
}

export async function getHospitalSiteSelection(candidateCount: number = 50) {
  const { data } = await api.get("/api/analysis/hospital-site-selection", {
    params: { candidate_count: candidateCount },
  });
  return data as GeoResponse;
}
