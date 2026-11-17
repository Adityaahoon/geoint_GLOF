import React, { useEffect, useState, useCallback } from "react";
import {
  FileText,
  Download,
  CheckSquare,
  Square,
  Play,
  Info,
} from "lucide-react";
import { api } from "../api/client";
import type { ReportItem } from "../api/types";

const REPORT_SECTIONS: { key: string; label: string; description: string }[] = [
  {
    key: "overview",
    label: "1. Executive Summary & Scientific Scope",
    description:
      "Overview of Kedarnath GLOF intelligence objectives, temporal span (2000–2026), and data availability.",
  },
  {
    key: "study_area",
    label: "2. Study Area & Geomorphic Context",
    description:
      "Mandakini River basin, Chorabari & Companion glaciers, reference elevations, and 2013 compound disaster context.",
  },
  {
    key: "methodology",
    label: "3. Remote Sensing & Analytical Methodology",
    description:
      "Spectral indices (MNDWI, NDWI, NDSI, NDVI, NBR), adaptive Otsu thresholding, and terrain slope masking.",
  },
  {
    key: "datasets",
    label: "4. Multi-Mission Satellite & Baseline Datasets",
    description:
      "Landsat 5/7/8/9, Sentinel-2, Copernicus GLO-30 DEM, and OpenStreetMap data provenance and citations.",
  },
  {
    key: "observations",
    label: "5. Glacial Lake Inventory & Empirical Observations",
    description:
      "Delineated glacial lake polygons, surface area trajectories, and elevation distributions.",
  },
  {
    key: "change_detection",
    label: "6. Multi-Decadal Change Analysis (2000–2026 YTD)",
    description:
      "Epoch-pair change statistics across baseline, 2013 disaster, recovery, and recent periods.",
  },
  {
    key: "deep_learning",
    label: "7. Deep Learning Segmentation & Model Evaluation",
    description:
      "Dataset preparation status, U-Net / DeepLabV3+ training runs, and empirical test metrics if trained.",
  },
  {
    key: "susceptibility",
    label: "8. Preliminary Multi-Criteria GLOF Susceptibility",
    description:
      "Factor weights, lake scores, missing field parameters, and epistemic uncertainty ranges.",
  },
  {
    key: "flood",
    label: "9. Hypothetical Breach Scenarios & Hydrodynamic Routing",
    description:
      "Defined breach hydrographs, literature citations, explicit assumptions, and imported HEC-RAS 2D results.",
  },
  {
    key: "exposure",
    label: "10. Potential Downstream Infrastructure Exposure",
    description:
      "OSM buildings, roads, bridges, and settlements within flowpath HAND corridors or scenario extents.",
  },
  {
    key: "limitations",
    label: "11. Scientific Limitations, Uncertainties & Caveats",
    description:
      "Sensor resolution differences, Landsat 7 SLC-off gaps, debris-covered ice, and unmeasured bathymetry.",
  },
  {
    key: "references",
    label: "12. Peer-Reviewed References & Data Citations",
    description:
      "Full bibliographic references (GAPHAZ, ICIMOD, Worni et al. 2013, Allen et al. 2019, Froehlich 2008).",
  },
];

export const ReportGenerator: React.FC = () => {
  const [title, setTitle] = useState<string>(
    "Kedarnath Basin GLOF Susceptibility & Multi-Decadal Change Assessment (2000–2026)"
  );
  const [selectedSections, setSelectedSections] = useState<string[]>(
    REPORT_SECTIONS.map((s) => s.key)
  );
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastDownloadUrl, setLastDownloadUrl] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    try {
      const list = await api.getReports();
      setReports(list);
    } catch {
      // handled gracefully
    }
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const toggleSection = (key: string) => {
    setSelectedSections((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedSections.length === 0) {
      setError("Select at least one report section.");
      return;
    }
    setGenerating(true);
    setError(null);
    setLastDownloadUrl(null);
    try {
      const res = await api.generateReport({
        title: title.trim() || undefined,
        sections: selectedSections,
      });
      if (res.download_url) {
        setLastDownloadUrl(res.download_url);
      }
      await loadReports();
    } catch (err: any) {
      setError(err?.message || "Failed to generate PDF report");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            Scientific Report Generator (PDF)
          </h1>
          <p className="text-xs text-slate-400">
            Compile empirical observations, methodology tables, uncertainty bounds, caveats, and citations into a structured technical PDF
          </p>
        </div>
      </div>

      <div className="bg-ink-900 border border-white/10 rounded-md p-3 flex items-center gap-2 text-xs text-slate-300">
        <Info className="w-4 h-4 text-glacier-400 shrink-0" />
        <span>
          Generated reports include only verified database records from completed analyses. Any unrun pipeline stages are explicitly documented as "Not yet computed" in the PDF.
        </span>
      </div>

      {error && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {error}
        </div>
      )}

      {lastDownloadUrl && (
        <div className="bg-hazard-low/10 border border-hazard-low/30 rounded-md p-3 flex items-center justify-between text-xs">
          <span className="text-hazard-low font-medium">
            PDF Report generated successfully!
          </span>
          <a
            href={lastDownloadUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-hazard-low/20 border border-hazard-low/40 text-hazard-low font-medium hover:bg-hazard-low/30"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download PDF Report</span>
          </a>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 text-xs">
        {/* Left: Report Configuration & Section Checklist (7 cols) */}
        <form
          onSubmit={handleGenerate}
          className="lg:col-span-7 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3"
        >
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <span className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-glacier-400" />
              <span>Report Title & Section Checklist</span>
            </span>
            <div className="flex items-center gap-2 text-[11px]">
              <button
                type="button"
                onClick={() =>
                  setSelectedSections(REPORT_SECTIONS.map((s) => s.key))
                }
                className="text-glacier-400 hover:underline"
              >
                Select All
              </button>
              <span className="text-slate-600">|</span>
              <button
                type="button"
                onClick={() => setSelectedSections([])}
                className="text-slate-400 hover:underline"
              >
                Clear
              </button>
            </div>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Report Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-96 overflow-y-auto pr-1">
            {REPORT_SECTIONS.map((sec) => {
              const checked = selectedSections.includes(sec.key);
              return (
                <button
                  type="button"
                  key={sec.key}
                  onClick={() => toggleSection(sec.key)}
                  className={`text-left p-2.5 rounded border transition-colors flex items-start gap-2 ${
                    checked
                      ? "bg-glacier-400/10 border-glacier-400/40"
                      : "bg-ink-950 border-white/5 opacity-60 hover:opacity-100"
                  }`}
                >
                  {checked ? (
                    <CheckSquare className="w-4 h-4 text-glacier-400 shrink-0 mt-0.5" />
                  ) : (
                    <Square className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-medium text-slate-200">{sec.label}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                      {sec.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          <button
            type="submit"
            disabled={generating || selectedSections.length === 0}
            className="w-full flex items-center justify-center gap-1.5 py-2 px-4 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-40"
          >
            <Play className="w-3.5 h-3.5" />
            <span>
              {generating
                ? "Compiling Scientific PDF Report..."
                : `Generate Technical Report (${selectedSections.length} sections)`}
            </span>
          </button>
        </form>

        {/* Right: Generated Reports Archive (5 cols) */}
        <div className="lg:col-span-5 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3">
          <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2">
            Generated PDF Reports Archive ({reports.length})
          </div>

          {reports.length > 0 ? (
            <div className="divide-y divide-white/5 max-h-[420px] overflow-y-auto">
              {reports.map((rep) => (
                <div
                  key={rep.id}
                  className="py-2.5 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="font-medium text-slate-200 truncate">
                      {rep.title}
                    </div>
                    <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                      ID #{rep.id} • {rep.created_at}
                    </div>
                  </div>
                  <a
                    href={rep.download_url || `/api/reports/${rep.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-[11px]"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>PDF</span>
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-slate-500 py-12 text-center bg-ink-950 rounded border border-white/5">
              No PDF reports generated yet. Select desired sections on the left and click "Generate Technical Report".
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
