import type { LayerSummary } from "../lib/types";

type Props = {
  layers: LayerSummary[];
  layerVisibility: Record<string, boolean>;
  onToggleLayer: (layer: string) => void;
  onRunQuery: (query: string) => void;
  onSearch: (value: string) => void;
  searchValue: string;
  loading: boolean;
  mode: string;
  suggestedQueries: Array<{ query: string; category: string; icon: string }>;
  chatHistory: Array<{ query: string; time: string }>;
};

export function Sidebar({ layers, layerVisibility, onToggleLayer, onRunQuery, onSearch, searchValue, loading, mode, suggestedQueries, chatHistory }: Props) {
  return (
    <aside className="flex h-full flex-col gap-4 rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-lg backdrop-blur-xl overflow-hidden flex-col">
      {/* Header */}
      <div>
        <div className="text-xs uppercase tracking-[0.35em] text-cyan-400 font-semibold">GeoAI Assistant</div>
        <h1 className="mt-2 text-lg font-bold text-white">Geospatial Intelligence</h1>
        <p className="mt-2 text-xs leading-5 text-slate-400">
          Natural language spatial reasoning with GIS tools and AI.
        </p>
      </div>

      {/* Search */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
        <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Search Location</label>
        <input
          className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400"
          value={searchValue}
          onChange={(event) => onSearch(event.target.value)}
          placeholder="Hospital, road, river..."
        />
      </div>

      {/* Suggested Queries */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Suggested Queries</h2>
          <span className={`rounded-full px-2 py-0.5 text-[9px] uppercase tracking-[0.15em] font-medium ${mode === "demo" ? "bg-amber-400/20 text-amber-300" : "bg-emerald-400/20 text-emerald-300"}`}>
            {mode === "demo" ? "Demo" : "Real"}
          </span>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
          {suggestedQueries.map((item) => (
            <button
              key={item.query}
              className="w-full rounded-lg border border-white/10 bg-slate-900/70 hover:bg-slate-900 hover:border-cyan-400/30 px-2 py-2 text-left text-xs text-slate-200 transition"
              onClick={() => onRunQuery(item.query)}
              disabled={loading}
              title={item.query}
            >
              <div className="flex items-start gap-2">
                <span className="text-sm flex-shrink-0">{item.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-white text-xs truncate">{item.category}</div>
                  <div className="text-slate-400 text-[11px] truncate">{item.query}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Data Layers */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 mb-2">Data Layers</h2>
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {layers.map((layer) => (
            <label key={layer.name} className="flex items-center gap-2 rounded-lg bg-slate-900/70 hover:bg-slate-900 px-2 py-2 text-xs text-slate-200 transition cursor-pointer">
              <input
                type="checkbox"
                checked={layerVisibility[layer.name] ?? true}
                onChange={() => onToggleLayer(layer.name)}
                className="h-3 w-3 accent-cyan-400"
              />
              <div className="min-w-0 flex-1">
                <div className="font-medium capitalize text-white truncate">{layer.name.replace(/_/g, " ")}</div>
                <div className="text-[10px] text-slate-400">{layer.featureCount} features</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Chat History */}
      {chatHistory.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 mb-2">Chat History</h2>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {chatHistory.map((item, idx) => (
              <button
                key={idx}
                className="w-full text-left rounded-lg bg-slate-900/50 hover:bg-slate-900 p-2 transition"
                onClick={() => onRunQuery(item.query)}
                title={item.query}
              >
                <div className="text-xs text-slate-300 truncate">{item.query}</div>
                <div className="text-[9px] text-slate-500">{item.time}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Status */}
      {loading && (
        <div className="rounded-2xl border border-cyan-400/30 bg-cyan-500/10 p-3 text-xs text-cyan-100 animate-pulse">
          ⚡ Running spatial analysis...
        </div>
      )}
    </aside>
  );
}
