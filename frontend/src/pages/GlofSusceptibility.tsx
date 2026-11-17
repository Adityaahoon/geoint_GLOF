import React, { useEffect, useState, useCallback } from "react";
import {
  ShieldAlert,
  Play,
  AlertTriangle,
  Info,
  BookOpen,
  Cpu,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api } from "../api/client";
import type {
  GlofAssessment,
  GlofMethodologyResponse,
  GlofMlStatusResponse,
} from "../api/types";
import { useJob } from "../hooks/useJob";
import { JobProgress } from "../components/JobProgress";
import { GeoMap, SUSCEPTIBILITY_COLORS } from "../components/GeoMap";

export const GlofSusceptibility: React.FC = () => {
  const [methodology, setMethodology] =
    useState<GlofMethodologyResponse | null>(null);
  const [assessments, setAssessments] = useState<GlofAssessment[]>([]);
  const [mlStatus, setMlStatus] = useState<GlofMlStatusResponse | null>(null);
  const [selectedLakeId, setSelectedLakeId] = useState<number | null>(null);

  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [meth, ass, ml] = await Promise.all([
        api.getGlofMethodology().catch(() => null),
        api.getGlofAssessments().catch(() => []),
        api.getGlofMlStatus().catch(() => null),
      ]);
      setMethodology(meth);
      setAssessments(ass);
      setMlStatus(ml);
      if (ass.length > 0 && selectedLakeId === null) {
        setSelectedLakeId(ass[0].lake_id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load GLOF susceptibility data");
    }
  }, [selectedLakeId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const { job, error: jobError, isRunning } = useJob(activeJobId, () => {
    loadAll();
  });

  const handleRunAssessment = async () => {
    setError(null);
    try {
      const res = await api.runGlofAssessment();
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err?.message || "Failed to start GLOF susceptibility screening");
    }
  };

  const selectedAssessment =
    assessments.find((a) => a.lake_id === selectedLakeId) ||
    assessments[0] ||
    null;

  const isTrainedModel =
    methodology?.is_trained_model ??
    selectedAssessment?.is_trained_model ??
    false;

  const factorChartData = React.useMemo(() => {
    if (!selectedAssessment?.factors) return [];
    return Object.entries(selectedAssessment.factors).map(([key, f]) => ({
      factor: key.replace(/_/g, " "),
      weighted_score: Number(((f.score || 0) * (f.weight || 0)).toFixed(3)),
      raw_score: f.score,
      weight: f.weight,
      value: f.value,
      unit: f.unit,
      available: f.available,
    }));
  }, [selectedAssessment]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            GLOF Multi-Criteria Susceptibility Screening
          </h1>
          <p className="text-xs text-slate-400">
            Literature-grounded hazard factor weighting with explicit parameter completeness and uncertainty bounds
          </p>
        </div>
        <button
          onClick={handleRunAssessment}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 text-xs font-medium disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run GLOF Susceptibility Screening</span>
        </button>
      </div>

      {/* Mandatory Scientific Banner when is_trained_model is false */}
      {!isTrainedModel && (
        <div className="bg-amber-500/15 border border-amber-500/40 rounded-md p-3 flex items-start gap-2.5 text-xs">
          <AlertTriangle className="w-4 h-4 text-amber-300 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-amber-200">
              Preliminary multi-criteria screening – not a trained predictive model, scores are not probabilities
            </div>
            <p className="text-amber-100/85 text-[11px] mt-0.5">
              This index combines observable remote-sensing and topographic criteria using published literature weights (GAPHAZ / ICIMOD / Worni et al., 2013; Allen et al., 2019). Subsurface moraine ice-core state, bathymetric volume, and seismic dam stability cannot be observed from satellite imagery and are explicitly reported under missing parameters and uncertainty bounds.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {error}
        </div>
      )}

      {(activeJobId !== null || jobError) && (
        <JobProgress
          job={job}
          error={jobError}
          onDismiss={() => setActiveJobId(null)}
        />
      )}

      {/* Top Row: Lake Inventory Table (6 cols) + Map Coloured by Category (6 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-6 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-glacier-400" />
              <span>Screened Glacial Lakes ({assessments.length})</span>
            </h2>
          </div>

          {assessments.length > 0 ? (
            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                    <th className="py-1.5 px-2">Lake</th>
                    <th className="py-1.5 px-2">Score</th>
                    <th className="py-1.5 px-2">Category</th>
                    <th className="py-1.5 px-2">Uncertainty Range</th>
                    <th className="py-1.5 px-2">Completeness</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono text-[11px]">
                  {assessments.map((a) => {
                    const isSel = a.lake_id === selectedAssessment?.lake_id;
                    const catCol =
                      SUSCEPTIBILITY_COLORS[a.category] || "#94a3b8";
                    return (
                      <tr
                        key={a.lake_id}
                        onClick={() => setSelectedLakeId(a.lake_id)}
                        className={`cursor-pointer hover:bg-white/5 ${
                          isSel ? "bg-glacier-400/15" : ""
                        }`}
                      >
                        <td className="py-2 px-2 font-sans">
                          <div className="font-medium text-slate-200">
                            {a.name}
                          </div>
                          <div className="text-[10px] font-mono text-slate-500">
                            {a.lake_code}
                          </div>
                        </td>
                        <td className="py-2 px-2 font-semibold text-slate-100">
                          {a.score.toFixed(2)}
                        </td>
                        <td className="py-2 px-2">
                          <span
                            className="px-2 py-0.5 rounded text-[10px] font-semibold"
                            style={{
                              backgroundColor: `${catCol}20`,
                              color: catCol,
                              border: `1px solid ${catCol}50`,
                            }}
                          >
                            {a.category}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-slate-300">
                          {a.uncertainty?.score_range
                            ? `[${a.uncertainty.score_range[0].toFixed(
                                2
                              )} – ${a.uncertainty.score_range[1].toFixed(2)}]`
                            : "—"}
                        </td>
                        <td className="py-2 px-2 text-slate-300">
                          {a.uncertainty?.completeness != null
                            ? `${Math.round(a.uncertainty.completeness * 100)}%`
                            : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-slate-500 py-12 text-center bg-ink-950 rounded border border-white/5 px-4">
              No GLOF susceptibility assessments found. Detect glacial lakes first, then click "Run GLOF Susceptibility Screening" above.
            </div>
          )}
        </div>

        <div className="lg:col-span-6">
          <GeoMap
            height="430px"
            selectedLakeId={selectedAssessment?.lake_id ?? null}
            onLakeSelect={(id) => setSelectedLakeId(id)}
            defaultLayers={{
              studyArea: true,
              lakes: true,
              susceptibility: true,
              referencePoints: true,
            }}
          />
        </div>
      </div>

      {/* Selected Lake Factor Breakdown + Missing Parameters & Uncertainty */}
      {selectedAssessment && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-7 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
            <div className="flex items-center justify-between border-b border-white/10 pb-2">
              <span className="font-semibold uppercase tracking-wider text-slate-200">
                Factor Breakdown: {selectedAssessment.name} (
                {selectedAssessment.lake_code})
              </span>
              <span className="font-mono text-glacier-300">
                Composite Score: {selectedAssessment.score.toFixed(2)} (
                {selectedAssessment.category})
              </span>
            </div>

            {factorChartData.length > 0 && (
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={factorChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                    <XAxis
                      type="number"
                      stroke="#64748b"
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis
                      dataKey="factor"
                      type="category"
                      width={130}
                      stroke="#94a3b8"
                      tick={{ fontSize: 10 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0b1220",
                        borderColor: "rgba(255,255,255,0.15)",
                        fontSize: 12,
                      }}
                    />
                    <Bar
                      dataKey="weighted_score"
                      name="Weighted Contribution (score × weight)"
                      fill="#5ec8e5"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Factor Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse font-mono text-[11px]">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                    <th className="py-1 px-2">Criterion</th>
                    <th className="py-1 px-2">Observed Value</th>
                    <th className="py-1 px-2">Sub-Score</th>
                    <th className="py-1 px-2">Weight</th>
                    <th className="py-1 px-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {Object.entries(selectedAssessment.factors || {}).map(
                    ([k, f]) => (
                      <tr key={k}>
                        <td className="py-1 px-2 font-sans text-slate-200">
                          {k.replace(/_/g, " ")}
                        </td>
                        <td className="py-1 px-2 text-slate-300">
                          {f.value != null
                            ? `${
                                typeof f.value === "number"
                                  ? f.value.toFixed(2)
                                  : f.value
                              } ${f.unit || ""}`
                            : "—"}
                        </td>
                        <td className="py-1 px-2 text-glacier-300">
                          {f.score?.toFixed(2) ?? "—"}
                        </td>
                        <td className="py-1 px-2 text-slate-400">
                          {f.weight}
                        </td>
                        <td className="py-1 px-2">
                          <span
                            className={
                              f.available
                                ? "text-hazard-low"
                                : "text-amber-400"
                            }
                          >
                            {f.available ? "Observed" : "Missing"}
                          </span>
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Uncertainty & Missing Parameters */}
          <div className="lg:col-span-5 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
            <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2">
              Parameter Completeness & Epistemic Uncertainty
            </div>

            <div className="grid grid-cols-2 gap-2 font-mono">
              <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                <div className="text-[10px] text-slate-500 uppercase">
                  Uncertainty Score Range
                </div>
                <div className="text-sm font-semibold text-slate-200 mt-0.5">
                  {selectedAssessment.uncertainty?.score_range
                    ? `${selectedAssessment.uncertainty.score_range[0].toFixed(
                        2
                      )} – ${selectedAssessment.uncertainty.score_range[1].toFixed(
                        2
                      )}`
                    : "—"}
                </div>
              </div>
              <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                <div className="text-[10px] text-slate-500 uppercase">
                  Category Range
                </div>
                <div className="text-sm font-semibold text-amber-300 mt-0.5">
                  {selectedAssessment.uncertainty?.category_range?.join(" → ") ||
                    selectedAssessment.category}
                </div>
              </div>
            </div>

            <div>
              <div className="font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-amber-400" />
                <span>Unobserved / Missing Field Parameters</span>
              </div>
              {selectedAssessment.missing_parameters &&
              selectedAssessment.missing_parameters.length > 0 ? (
                <ul className="list-disc list-inside text-[11px] text-slate-300 space-y-1 bg-ink-950 p-2.5 rounded border border-white/5">
                  {selectedAssessment.missing_parameters.map((mp, i) => (
                    <li key={i}>{mp}</li>
                  ))}
                </ul>
              ) : (
                <div className="text-slate-500 text-[11px]">
                  All remote-sensing criteria populated. Field geotechnical parameters remain external.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Bottom Row: Methodology Panel + ML Status Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <span className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-glacier-400" />
              <span>
                Methodology & Literature Weights ({methodology?.method || "MCDA"}{" "}
                v{methodology?.version || "1.0"})
              </span>
            </span>
          </div>

          {methodology ? (
            <div className="space-y-3">
              <p className="text-slate-300 text-[11px]">
                {methodology.description}
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead>
                    <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                      <th className="py-1.5 px-2">Criterion</th>
                      <th className="py-1.5 px-2">Weight</th>
                      <th className="py-1.5 px-2">Scoring Rule</th>
                      <th className="py-1.5 px-2">Scientific Reference</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {methodology.criteria?.map((c) => (
                      <tr key={c.key}>
                        <td className="py-1.5 px-2 font-medium text-slate-200">
                          {c.label}
                        </td>
                        <td className="py-1.5 px-2 font-mono text-glacier-300">
                          {c.weight}
                        </td>
                        <td className="py-1.5 px-2 text-slate-300">
                          {c.scoring}
                        </td>
                        <td className="py-1.5 px-2 text-slate-400 text-[10px]">
                          {c.reference}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {methodology.limitations && methodology.limitations.length > 0 && (
                <div className="bg-ink-950 border border-white/5 rounded p-2.5 space-y-1 text-[11px]">
                  <div className="font-semibold text-amber-300">
                    Methodological Limitations
                  </div>
                  <ul className="list-disc list-inside text-slate-400 space-y-0.5">
                    {methodology.limitations.map((lim, i) => (
                      <li key={i}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-500 py-6 text-center">
              Loading methodology specification...
            </div>
          )}
        </div>

        {/* ML Status Card */}
        <div className="lg:col-span-4 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
          <div className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5 border-b border-white/10 pb-2">
            <Cpu className="w-3.5 h-3.5 text-glacier-400" />
            <span>Supervised ML Classifier Status</span>
          </div>

          {mlStatus ? (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between bg-ink-950 p-2.5 rounded border border-white/5">
                <span className="text-slate-400">Trainable Status:</span>
                <span
                  className={`font-mono font-semibold ${
                    mlStatus.trainable ? "text-hazard-low" : "text-amber-400"
                  }`}
                >
                  {mlStatus.trainable
                    ? "Ready for Training"
                    : "Awaiting Verified Event Inventory"}
                </span>
              </div>
              <div className="text-[11px] text-slate-300 leading-relaxed">
                {mlStatus.reason}
              </div>
              {mlStatus.required_data && mlStatus.required_data.length > 0 && (
                <div className="bg-ink-950 p-2.5 rounded border border-white/5 space-y-1">
                  <div className="text-[10px] font-semibold uppercase text-slate-400">
                    Required Ground-Truth Inputs:
                  </div>
                  <ul className="list-disc list-inside text-[11px] text-slate-400 space-y-0.5">
                    {mlStatus.required_data.map((req, i) => (
                      <li key={i}>{req}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-500 py-6 text-center">
              Querying `/glof/ml-status`...
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
