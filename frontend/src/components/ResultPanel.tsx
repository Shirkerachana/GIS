import { formatScore } from "../lib/geo";
import type { GeoResponse } from "../lib/types";

type Props = {
  response: GeoResponse | null;
  error: string | null;
  loading: boolean;
  onExplainTop: () => void;
  lastQuery?: string;
};

export function ResultPanel({ response, error, loading, onExplainTop, lastQuery }: Props) {
  const recommendations = response?.recommended_locations ?? [];

  return (
    <section className="flex h-full flex-col gap-4 rounded-3xl border border-white/10 bg-slate-950/75 p-5 shadow-glow backdrop-blur-xl">
      <div>
        <div className="text-xs uppercase tracking-[0.35em] text-geo-300">AI Response</div>
        <h2 className="mt-2 text-xl font-semibold text-white">Analysis Summary</h2>
      </div>

      {lastQuery && (
        <div className="rounded-2xl border border-cyan-400/30 bg-cyan-500/10 p-3">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Current Query</div>
          <div className="mt-1 text-sm text-cyan-100 font-medium">{lastQuery}</div>
        </div>
      )}

      {error && <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100">{error}</div>}

      {loading && !response && !error && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
          Loading geospatial layers and preparing the first analysis...
        </div>
      )}

      {response ? (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Result Count" value={String(response.result_count)} />
            <Stat label="Selected Tool" value={response.selected_tool} />
            <Stat label="Operation" value={response.spatial_operation} />
            <Stat label="Mode" value={response.mode} />
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h3 className="text-xs uppercase tracking-[0.2em] text-slate-400">What happened</h3>
            <p className="mt-2 text-sm leading-6 text-slate-200">{response.explanation}</p>
            {response.message && <p className="mt-2 text-sm text-amber-200">{response.message}</p>}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h3 className="text-xs uppercase tracking-[0.2em] text-slate-400">Key Findings</h3>
            <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-300">{JSON.stringify(response.summary, null, 2)}</pre>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-xs uppercase tracking-[0.2em] text-slate-400">Recommended Locations</h3>
              <button className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-200 hover:border-geo-400/60" onClick={onExplainTop}>
                Why this location?
              </button>
            </div>
            <div className="mt-3 space-y-3">
              {recommendations.length > 0 ? (
                recommendations.map((item, index) => {
                  // Check if this is a hospital candidate (has suitability_score) or a regular recommendation (has name)
                  const isCandidate = 'suitability_score' in item;
                  const displayName = isCandidate ? `Candidate ${index + 1}` : String(item.name ?? `Location ${index + 1}`);
                  const displayScore = isCandidate ? (item as any).suitability_score : (item as any).score;
                  const displayReason = isCandidate ? (item as any).reason : String(item.reason ?? "");
                  
                  return (
                    <div key={`${displayName}-${index}`} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-white">{displayName}</div>
                        <div className="rounded-full bg-geo-500/15 px-2 py-1 text-xs text-geo-200">Score {formatScore(displayScore)}</div>
                      </div>
                      <div className="mt-1 text-xs leading-5 text-slate-400">{displayReason}</div>
                    </div>
                  );
                })
              ) : (
                <div className="text-sm text-slate-400">No recommendations yet. Run a suitability query to see ranked locations.</div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h3 className="text-xs uppercase tracking-[0.2em] text-slate-400">Sources</h3>
            <ul className="mt-2 space-y-1 text-sm text-slate-300">
              {response.sources.map((source) => (
                <li key={source}>• {source}</li>
              ))}
            </ul>
          </div>
        </>
      ) : (
        <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm leading-6 text-slate-400">
          {loading ? "The backend is loading geospatial data and preparing the analysis." : "Ask a question to generate a spatial analysis, map results, and a plain-language explanation."}
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
      <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-medium text-white">{value}</div>
    </div>
  );
}
