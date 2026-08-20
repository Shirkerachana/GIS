import { useEffect, useState } from "react";
import "leaflet/dist/leaflet.css";
import { GeoMap } from "./components/GeoMap";
import { ResultPanel } from "./components/ResultPanel";
import { Sidebar } from "./components/Sidebar";
import { HospitalCandidates } from "./components/HospitalCandidates";
import { CandidateDetails } from "./components/CandidateDetails";
import { fetchHealth, fetchLayers, fetchLayer, sendQuery, getHospitalSiteSelection } from "./lib/api";
import type { GeoJsonFeatureCollection, GeoResponse, LayerSummary } from "./lib/types";

const suggestedQueries = [
  { query: "Show hospitals in Pune.", category: "Explore", icon: "🏥" },
  { query: "Show high population areas.", category: "Raster", icon: "👥" },
  { query: "Find hospitals near major roads.", category: "Vector", icon: "🛣️" },
  { query: "Find areas with poor hospital accessibility.", category: "Analysis", icon: "📍" },
  { query: "Find the best location for a new hospital.", category: "Optimization", icon: "⭐" },
];

export default function App() {
  const [layers, setLayers] = useState<LayerSummary[]>([]);
  const [layerData, setLayerData] = useState<Record<string, GeoJsonFeatureCollection | null>>({
    hospitals: null,
    roads: null,
    rivers: null,
    buildings: null,
    population: null,
    administrative_boundaries: null,
  });
  const [visible, setVisible] = useState<Record<string, boolean>>({
    hospitals: true,
    roads: true,
    rivers: true,
    buildings: false,
    population: true,
    administrative_boundaries: true,
  });
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<GeoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState(suggestedQueries[0].query);
  const [searchValue, setSearchValue] = useState("");
  const [mode, setMode] = useState("demo");
  const [focusCollection, setFocusCollection] = useState<GeoJsonFeatureCollection | null>(null);
  const [booting, setBooting] = useState(true);
  const [showingHospitalSelection, setShowingHospitalSelection] = useState(false);
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState<number | null>(null);
  const [chatHistory, setChatHistory] = useState<Array<{ query: string; time: string }>>([]);

  useEffect(() => {
    async function boot() {
      try {
        const health = await fetchHealth();
        setMode(health.active_mode === "real" ? "real" : "demo");
        const layerSummary = await fetchLayers();
        setLayers(layerSummary);

        const [hospitals, roads, rivers, population, boundaries] = await Promise.all([
          fetchLayer("hospitals"),
          fetchLayer("roads"),
          fetchLayer("rivers"),
          fetchLayer("population"),
          fetchLayer("administrative_boundaries"),
        ]);

        setLayerData((current) => ({
          ...current,
          hospitals,
          roads,
          rivers,
          population,
          administrative_boundaries: boundaries,
        }));
      } catch (bootError) {
        setError(bootError instanceof Error ? bootError.message : "Failed to initialize the dashboard.");
      } finally {
        setBooting(false);
      }
    }

    void boot();
  }, []);

  const boundary = layerData.administrative_boundaries;

  async function runQuery(text: string) {
    if (booting) {
      setError("The backend is still loading data. Please wait a moment and try again.");
      return;
    }
    setQuery(text);
    setLoading(true);
    setError(null);
    setShowingHospitalSelection(false);
    setSelectedCandidateIndex(null);

    // Add to chat history
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    setChatHistory(prev => [{ query: text, time: timeString }, ...prev.slice(0, 9)]);

    try {
      // Special handling for hospital location query
      if (
        text.toLowerCase().includes("best location") &&
        text.toLowerCase().includes("hospital")
      ) {
        const result = await getHospitalSiteSelection(50);
        setResponse(result);
        setShowingHospitalSelection(true);
        setFocusCollection(result.geojson?.features?.length ? result.geojson : null);
      } else {
        const result = await sendQuery(text, response ? { recommended_locations: response.recommended_locations, selected_location: response.recommended_locations?.[0] } : {});
        setResponse(result);
        setFocusCollection(result.geojson?.features?.length ? result.geojson : null);
      }
    } catch (queryError) {
      setError(queryError instanceof Error ? queryError.message : "The analysis could not be completed.");
    } finally {
      setLoading(false);
    }
  }

  function toggleLayer(name: string) {
    setVisible((current) => ({ ...current, [name]: !current[name] }));
  }

  function handleSearch(value: string) {
    setSearchValue(value);
    const normalized = value.trim().toLowerCase();
    if (!normalized) {
      setFocusCollection(null);
      return;
    }

    const match = Object.values(layerData).find((collection) =>
      collection?.features.some((feature) => String(feature.properties?.name ?? "").toLowerCase().includes(normalized))
    );

    setFocusCollection(match ?? null);
  }

  function explainTopLocation() {
    const top = response?.recommended_locations?.[0];
    if (!top) return;
    void runQuery("Why was this location recommended?");
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-[2000px] flex-col gap-4 p-4 xl:grid xl:grid-cols-[340px_minmax(0,1fr)_420px] xl:grid-rows-[1fr_auto]">
        {/* LEFT SIDEBAR */}
        <div className="xl:row-span-2">
          <Sidebar
            layers={layers}
            layerVisibility={visible}
            onToggleLayer={toggleLayer}
            onRunQuery={runQuery}
            onSearch={handleSearch}
            searchValue={searchValue}
            loading={loading}
            mode={mode}
            suggestedQueries={suggestedQueries}
            chatHistory={chatHistory}
          />
        </div>

        {/* CENTER - MAP */}
        <main className="space-y-4 xl:col-start-2 xl:row-start-1">
          <div className="rounded-3xl border border-white/10 bg-white/5 px-6 py-4 shadow-lg backdrop-blur-xl">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.35em] text-cyan-400 font-semibold">GeoAI Assistant</div>
                <h2 className="mt-1 text-xl font-bold text-white">Interactive Geospatial Intelligence Platform</h2>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-2 text-sm">
                <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${mode === "demo" ? "bg-amber-400/20 text-amber-300" : "bg-emerald-400/20 text-emerald-300"}`}>
                  {mode === "demo" ? "📊 Demo Mode" : "🔴 Real Data"}
                </span>
              </div>
            </div>
          </div>

          <GeoMap
            hospitals={visible.hospitals ? layerData.hospitals : null}
            roads={visible.roads ? layerData.roads : null}
            rivers={visible.rivers ? layerData.rivers : null}
            population={visible.population ? layerData.population : null}
            boundaries={visible.administrative_boundaries ? boundary : null}
            analysis={response?.intent?.operation === "find_high_population_areas" || response?.intent?.operation === "find_nearby" ? response.geojson : null}
            recommendations={response?.intent?.operation === "site_suitability" || response?.intent?.operation === "calculate_site_suitability" ? response.geojson : null}
            showLayers={visible}
            focusCollection={focusCollection}
            loading={booting || loading}
          />
        </main>

        {/* RIGHT SIDEBAR - RESULTS */}
        <div className="xl:col-start-3 xl:row-start-1 xl:row-span-2">
          {showingHospitalSelection ? (
            <div className="space-y-4">
              <HospitalCandidates
                data={response}
                loading={loading}
                onSelectCandidate={(candidate, index) => setSelectedCandidateIndex(index)}
                selectedIndex={selectedCandidateIndex}
              />
              {selectedCandidateIndex !== null && response?.recommended_locations && (
                <CandidateDetails
                  candidate={response.recommended_locations[selectedCandidateIndex] as any}
                  rank={selectedCandidateIndex}
                />
              )}
            </div>
          ) : (
            <ResultPanel 
              response={response} 
              error={error} 
              loading={booting || loading} 
              onExplainTop={explainTopLocation}
              lastQuery={query}
            />
          )}
        </div>

        {/* BOTTOM - QUERY INPUT */}
        <div className="xl:col-start-2 xl:row-start-2">
          <div className="rounded-3xl border border-white/10 bg-slate-950/80 p-4 shadow-lg backdrop-blur-xl">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-3">
              <input
                className="min-h-14 flex-1 rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/30 transition"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !loading && !booting) {
                    runQuery(query);
                  }
                }}
                placeholder='Ask about hospitals, roads, populations, or site suitability...'
              />
              <button
                className="rounded-2xl bg-cyan-500 hover:bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 transition disabled:opacity-50"
                onClick={() => runQuery(query)}
                disabled={loading || booting}
              >
                {booting ? "Loading..." : loading ? "Analyzing..." : "Send"}
              </button>
            </div>

            <div className="mt-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500 mb-2">Quick Queries</div>
              <div className="flex flex-wrap gap-2">
                {suggestedQueries.map((item) => (
                  <button
                    key={item.query}
                    onClick={() => runQuery(item.query)}
                    className="rounded-full border border-white/10 bg-white/5 hover:bg-white/10 hover:border-cyan-400/50 px-3 py-2 text-xs text-slate-200 transition flex items-center gap-1"
                    disabled={booting || loading}
                  >
                    <span>{item.icon}</span>
                    <span className="max-w-[80px] truncate">{item.query}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
