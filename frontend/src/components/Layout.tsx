import React, { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Satellite,
  Waves,
  TrendingUp,
  AlertOctagon,
  MountainSnow,
  ShieldAlert,
  Droplets,
  Building2,
  FileSpreadsheet,
  Cpu,
  FileText,
  Settings,
  Database,
  Globe,
  RefreshCw,
  X,
} from "lucide-react";
import { useAppContext } from "../context/AppContext";

const NAV_ITEMS = [
  { to: "/", label: "Overview Dashboard", icon: LayoutDashboard },
  { to: "/satellite", label: "Historical Satellite Explorer", icon: Satellite },
  { to: "/lakes", label: "Glacial Lake Detection", icon: Waves },
  { to: "/change-analysis", label: "Historical Change Analysis", icon: TrendingUp },
  { to: "/disaster-impact", label: "2013 Disaster Impact", icon: AlertOctagon },
  { to: "/glacier", label: "Glacier Monitoring", icon: MountainSnow },
  { to: "/susceptibility", label: "GLOF Susceptibility", icon: ShieldAlert },
  { to: "/flood-simulation", label: "Flood Simulation (HEC-RAS)", icon: Droplets },
  { to: "/exposure", label: "Infrastructure Exposure", icon: Building2 },
  { to: "/workspace", label: "GeoTIFF Workspace", icon: FileSpreadsheet },
  { to: "/model-lab", label: "Deep Learning Model Lab", icon: Cpu },
  { to: "/reports", label: "Report Generator", icon: FileText },
];

export const Layout: React.FC = () => {
  const {
    health,
    studyArea,
    selectedYear,
    setSelectedYear,
    refreshHealth,
  } = useAppContext();

  const [showSettings, setShowSettings] = useState(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-ink-950 text-slate-200">
      {/* Permanent Left Sidebar */}
      <aside className="w-60 shrink-0 bg-ink-900 border-r border-white/10 flex flex-col justify-between">
        <div>
          <div className="h-14 px-4 flex items-center gap-2.5 border-b border-white/10">
            <div className="w-7 h-7 rounded bg-glacier-400/15 border border-glacier-400/40 flex items-center justify-center text-glacier-400 font-bold text-sm">
              GG
            </div>
            <div className="leading-tight">
              <div className="font-semibold text-sm text-slate-100 tracking-tight">
                GlacioGuard AI
              </div>
              <div className="text-[10px] font-mono text-glacier-400 uppercase tracking-wider">
                GEOINT GLOF Platform
              </div>
            </div>
          </div>

          <nav className="p-2 space-y-0.5 overflow-y-auto max-h-[calc(100vh-120px)]">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-glacier-400/15 text-glacier-300 border border-glacier-400/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent"
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="truncate">{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="p-3 border-t border-white/10 text-[11px] text-slate-500 space-y-1">
          <div className="flex items-center justify-between">
            <span>Temporal Span</span>
            <span className="font-mono text-slate-300">2000–2026 YTD</span>
          </div>
          <div className="flex items-center justify-between">
            <span>CRS / UTM</span>
            <span className="font-mono text-slate-300">
              EPSG:{studyArea?.utm_epsg ?? 32644}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 shrink-0 bg-ink-900 border-b border-white/10 px-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="truncate">
              <span className="text-xs font-semibold text-slate-200">
                {studyArea?.name || "Kedarnath & Mandakini Basin, Uttarakhand, India"}
              </span>
              {studyArea?.bbox && (
                <span className="ml-2 text-[11px] font-mono text-slate-400 hidden xl:inline">
                  [{studyArea.bbox.map((v) => v.toFixed(2)).join(", ")}]
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {/* Global Year Selector */}
            <div className="flex items-center gap-1.5 bg-ink-950 border border-white/10 rounded px-2.5 py-1 text-xs">
              <span className="text-slate-400">Reference Year:</span>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="bg-transparent text-glacier-300 font-mono font-medium focus:outline-none cursor-pointer"
              >
                {Array.from({ length: 27 }, (_, i) => 2000 + i).map((yr) => (
                  <option key={yr} value={yr} className="bg-ink-900 text-slate-200">
                    {yr} {yr === 2026 ? "(YTD)" : yr === 2013 ? "(Disaster)" : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Connection Status Pills */}
            <div className="hidden md:flex items-center gap-1.5 text-[11px] font-mono">
              <span
                className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
                  health?.database?.ok
                    ? "bg-hazard-low/10 border-hazard-low/30 text-hazard-low"
                    : "bg-slate-800 border-white/10 text-slate-400"
                }`}
                title={`Database: ${health?.database?.dialect || "unknown"}`}
              >
                <Database className="w-3 h-3" />
                DB: {health?.database?.ok ? "OK" : "Offline"}
              </span>

              <span
                className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
                  health?.gee?.available
                    ? "bg-hazard-low/10 border-hazard-low/30 text-hazard-low"
                    : "bg-amber-500/10 border-amber-500/30 text-amber-300"
                }`}
                title={health?.gee?.error || `GEE Mode: ${health?.gee?.mode || "N/A"}`}
              >
                <Globe className="w-3 h-3" />
                GEE: {health?.gee?.available ? "Connected" : "Fallback"}
              </span>

              <span
                className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
                  health?.stac?.available
                    ? "bg-glacier-400/10 border-glacier-400/30 text-glacier-300"
                    : "bg-slate-800 border-white/10 text-slate-400"
                }`}
                title={`STAC Providers: ${health?.stac?.providers?.join(", ") || " Planetary Computer / AWS"}`}
              >
                STAC: {health?.stac?.available ? "OpenData" : "N/A"}
              </span>

              <span
                className="px-2 py-0.5 rounded border bg-ink-950 border-white/10 text-slate-300"
                title={`PyTorch ${health?.torch?.version || ""}`}
              >
                PyTorch: {health?.torch?.device || (health?.torch?.available ? "cpu" : "N/A")}
              </span>
            </div>

            <button
              onClick={() => setShowSettings(true)}
              className="p-1.5 rounded bg-ink-950 border border-white/10 text-slate-400 hover:text-slate-200 hover:border-white/20"
              title="System Diagnostics & Status"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Page Outlet */}
        <main className="flex-1 overflow-y-auto p-4">
          <Outlet />
        </main>
      </div>

      {/* System Diagnostics Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-[1000] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-ink-900 border border-white/15 rounded-md w-full max-w-lg p-4 space-y-4 text-xs shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
              <div className="font-semibold text-sm text-slate-100">
                System Health & Data Diagnostics
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {health ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                    <div className="text-slate-400 text-[10px] uppercase">Database</div>
                    <div className="font-mono text-slate-200 mt-0.5">
                      {health.database.dialect} ({health.database.ok ? "Connected" : "Error"})
                    </div>
                  </div>
                  <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                    <div className="text-slate-400 text-[10px] uppercase">Google Earth Engine</div>
                    <div className="font-mono text-slate-200 mt-0.5">
                      {health.gee.available ? `Ready (${health.gee.mode})` : "Unavailable (Using STAC)"}
                    </div>
                    {health.gee.error && (
                      <div className="text-[10px] text-amber-400 mt-0.5 truncate" title={health.gee.error}>
                        {health.gee.error}
                      </div>
                    )}
                  </div>
                  <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                    <div className="text-slate-400 text-[10px] uppercase">STAC Open Data</div>
                    <div className="font-mono text-slate-200 mt-0.5">
                      {health.stac.providers?.join(", ") || "Available"}
                    </div>
                  </div>
                  <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                    <div className="text-slate-400 text-[10px] uppercase">ML Runtime</div>
                    <div className="font-mono text-slate-200 mt-0.5">
                      Torch: {health.torch.available ? `${health.torch.device} (${health.torch.version})` : "No"} | XGB:{" "}
                      {health.xgboost.available ? "Yes" : "No"}
                    </div>
                  </div>
                </div>

                <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                  <div className="text-slate-400 text-[10px] uppercase mb-1">
                    Ingested Data Inventory
                  </div>
                  <div className="grid grid-cols-4 gap-2 font-mono">
                    <div>
                      <span className="text-slate-500">DEM:</span>{" "}
                      <span className={health.data.dem ? "text-hazard-low" : "text-amber-400"}>
                        {health.data.dem ? "Yes" : "No"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">OSM:</span>{" "}
                      <span className={health.data.osm ? "text-hazard-low" : "text-amber-400"}>
                        {health.data.osm ? "Yes" : "No"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Composites:</span>{" "}
                      <span className="text-glacier-300">{health.data.composites}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Lakes:</span>{" "}
                      <span className="text-glacier-300">{health.data.lakes}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-slate-400 py-4 text-center">
                Unable to reach `/api/health`. Verify backend server is running on port 8000.
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
              <button
                onClick={refreshHealth}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-glacier-400/15 border border-glacier-400/30 text-glacier-300 hover:bg-glacier-400/25"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Refresh Status</span>
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className="px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 text-slate-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
