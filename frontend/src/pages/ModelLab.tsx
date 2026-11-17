import React, { useEffect, useState, useCallback } from "react";
import {
  Cpu,
  Play,
  Layers,
  AlertTriangle,
  CheckCircle2,
  FolderOpen,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { api } from "../api/client";
import type {
  ModelDatasetsResponse,
  ModelRun,
  SatelliteComposite,
} from "../api/types";
import { useJob } from "../hooks/useJob";
import { JobProgress } from "../components/JobProgress";

export const ModelLab: React.FC = () => {
  const [datasets, setDatasets] = useState<ModelDatasetsResponse | null>(null);
  const [runs, setRuns] = useState<ModelRun[]>([]);
  const [composites, setComposites] = useState<SatelliteComposite[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // Prepare Tiles Form
  const [compositeId, setCompositeId] = useState<number | "">("");
  const [tileSize, setTileSize] = useState<number>(256);

  // Train Model Form
  const [modelType, setModelType] = useState<"unet" | "deeplabv3plus">("unet");
  const [epochs, setEpochs] = useState<number>(50);
  const [batchSize, setBatchSize] = useState<number>(8);
  const [learningRate, setLearningRate] = useState<number>(0.001);

  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadLab = useCallback(async () => {
    try {
      const [ds, rList, cList] = await Promise.all([
        api.getModelDatasets().catch(() => null),
        api.getModelRuns().catch(() => []),
        api.getComposites().catch(() => []),
      ]);
      setDatasets(ds);
      setRuns(rList);
      setComposites(cList);
      if (rList.length > 0 && selectedRunId === null) {
        setSelectedRunId(rList[0].id);
      }
      if (cList.length > 0 && compositeId === "") {
        setCompositeId(cList[0].composite_id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load Model Lab status");
    }
  }, [selectedRunId, compositeId]);

  useEffect(() => {
    loadLab();
  }, [loadLab]);

  const { job, error: jobError, isRunning } = useJob(activeJobId, () => {
    loadLab();
  });

  const handlePrepareTiles = async (e: React.FormEvent) => {
    e.preventDefault();
    if (compositeId === "") {
      setError("Please select a satellite composite to tile.");
      return;
    }
    setError(null);
    try {
      const res = await api.prepareTiles({
        composite_id: Number(compositeId),
        tile_size: tileSize,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err?.message || "Failed to start tile preparation job");
    }
  };

  const handleTrainModel = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.trainModel({
        model_type: modelType,
        epochs,
        batch_size: batchSize,
        learning_rate: learningRate,
        tile_size: tileSize,
      });
      setActiveJobId(res.job_id);
      if (res.run_id) setSelectedRunId(res.run_id);
    } catch (err: any) {
      setError(err?.message || "Training failed to start");
    }
  };

  const handleEvaluateRun = async (runId: number) => {
    setError(null);
    try {
      const res = await api.evaluateModel({ run_id: runId, split: "test" });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err?.message || "Evaluation failed to start");
    }
  };

  const selectedRun =
    runs.find((r) => r.id === selectedRunId) || runs[0] || null;
  const segStatus = datasets?.segmentation?.status || "awaiting_training_data";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            Deep Learning Model Lab (U-Net & DeepLabV3+ Segmentation)
          </h1>
          <p className="text-xs text-slate-400">
            Reproducible PyTorch training, spatial tile preparation, loss/metric curves, and confusion matrix evaluation
          </p>
        </div>
      </div>

      {/* Prominent Awaiting Training Data Banner when status !== "ready" */}
      {segStatus !== "ready" && (
        <div className="bg-amber-500/15 border border-amber-500/40 rounded-md p-3.5 space-y-2 text-xs">
          <div className="flex items-center gap-2 font-semibold text-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-300 shrink-0" />
            <span>
              Dataset Status: Awaiting Verified Training Data ({segStatus})
            </span>
          </div>
          <p className="text-amber-100/85 text-[11px] leading-relaxed">
            In accordance with scientific integrity standards, GlacioGuard AI never displays fabricated IoU, Dice, or accuracy metrics. To train a supervised U-Net or DeepLabV3+ segmentation model, follow the dataset preparation protocol below:
          </p>
          {datasets?.segmentation?.instructions &&
            datasets.segmentation.instructions.length > 0 && (
              <ol className="list-decimal list-inside text-[11px] text-amber-100/90 space-y-0.5 font-mono bg-ink-950/60 p-2.5 rounded border border-amber-500/20">
                {datasets.segmentation.instructions.map((inst, i) => (
                  <li key={i}>{inst}</li>
                ))}
              </ol>
            )}
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

      {/* Top Grid: Dataset Summary + Prepare Tiles + Train Form */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 text-xs">
        {/* Dataset Status Card */}
        <div className="lg:col-span-4 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3">
          <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2 flex items-center gap-1.5">
            <FolderOpen className="w-3.5 h-3.5 text-glacier-400" />
            <span>Segmentation Dataset Inventory</span>
          </div>

          {datasets?.segmentation ? (
            <div className="space-y-2.5 font-mono text-[11px]">
              <div className="flex items-center justify-between bg-ink-950 p-2 rounded border border-white/5">
                <span className="text-slate-400">Status</span>
                <span
                  className={`flex items-center gap-1 font-semibold ${
                    datasets.segmentation.status === "ready"
                      ? "text-hazard-low"
                      : "text-amber-300"
                  }`}
                >
                  {datasets.segmentation.status === "ready" && (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  )}
                  {datasets.segmentation.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="bg-ink-950 p-2 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Image Tiles</div>
                  <div className="text-sm font-semibold text-slate-200">
                    {datasets.segmentation.image_tiles}
                  </div>
                </div>
                <div className="bg-ink-950 p-2 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Mask Tiles</div>
                  <div className="text-sm font-semibold text-glacier-300">
                    {datasets.segmentation.mask_tiles}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-1.5 text-center">
                <div className="bg-ink-950 p-1.5 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Train</div>
                  <div className="text-slate-200 font-semibold">
                    {datasets.segmentation.splits?.train ?? 0}
                  </div>
                </div>
                <div className="bg-ink-950 p-1.5 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Val</div>
                  <div className="text-slate-200 font-semibold">
                    {datasets.segmentation.splits?.val ?? 0}
                  </div>
                </div>
                <div className="bg-ink-950 p-1.5 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Test</div>
                  <div className="text-slate-200 font-semibold">
                    {datasets.segmentation.splits?.test ?? 0}
                  </div>
                </div>
              </div>

              <div className="text-[10px] text-slate-400 truncate" title={datasets.segmentation.directory}>
                Dir: {datasets.segmentation.directory}
              </div>
              <div className="text-[10px] text-slate-500">
                Split Strategy: {datasets.segmentation.split_strategy}
              </div>
            </div>
          ) : (
            <div className="text-slate-500 py-6 text-center">
              Loading dataset summary...
            </div>
          )}
        </div>

        {/* Step 1: Prepare Tiles Form */}
        <form
          onSubmit={handlePrepareTiles}
          className="lg:col-span-4 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3"
        >
          <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-glacier-400" />
            <span>1. Prepare Spatial Tiles & Pre-Labels</span>
          </div>

          <p className="text-[11px] text-slate-400 leading-relaxed">
            Slices a multi-band composite into patches and generates initial MNDWI + Otsu candidate masks flagged as <code className="text-amber-300">unverified</code> for human inspection/QA.
          </p>

          <div>
            <label className="block text-slate-400 mb-1">
              Source Satellite Composite
            </label>
            <select
              value={compositeId}
              onChange={(e) =>
                setCompositeId(e.target.value ? Number(e.target.value) : "")
              }
              className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200 font-mono"
            >
              <option value="">Select composite...</option>
              {composites.map((c) => (
                <option key={c.composite_id} value={c.composite_id}>
                  #{c.composite_id} • {c.year} ({c.mission})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">
              Patch Tile Size (px)
            </label>
            <select
              value={tileSize}
              onChange={(e) => setTileSize(Number(e.target.value))}
              className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 font-mono text-slate-200"
            >
              <option value={128}>128 × 128</option>
              <option value={256}>256 × 256</option>
              <option value={512}>512 × 512</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={isRunning || compositeId === ""}
            className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-ink-800 hover:bg-ink-700 border border-white/15 text-slate-200 font-medium disabled:opacity-40"
          >
            <Play className="w-3.5 h-3.5 text-glacier-400" />
            <span>Generate Image & Pre-Label Tiles</span>
          </button>
        </form>

        {/* Step 2: Train Deep Learning Model Form */}
        <form
          onSubmit={handleTrainModel}
          className="lg:col-span-4 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3"
        >
          <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-glacier-400" />
            <span>2. Train Segmentation Architecture</span>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">
              Architecture
            </label>
            <select
              value={modelType}
              onChange={(e) =>
                setModelType(e.target.value as "unet" | "deeplabv3plus")
              }
              className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
            >
              <option value="unet">U-Net (Encoder-Decoder with Skip Connections)</option>
              <option value="deeplabv3plus">
                DeepLabV3+ (Atrous Spatial Pyramid Pooling)
              </option>
            </select>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-slate-400 mb-1">Epochs</label>
              <input
                type="number"
                min={1}
                max={500}
                value={epochs}
                onChange={(e) => setEpochs(Number(e.target.value))}
                className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Batch Size</label>
              <input
                type="number"
                min={1}
                max={64}
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Learn Rate</label>
              <input
                type="number"
                step="0.0001"
                value={learningRate}
                onChange={(e) => setLearningRate(Number(e.target.value))}
                className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isRunning}
            className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-40"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Launch Training Run</span>
          </button>
        </form>
      </div>

      {/* Training Runs & Evaluation Metrics Section */}
      {runs.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 text-xs">
          {/* Runs Comparison Table */}
          <div className="lg:col-span-5 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5">
            <div className="font-semibold uppercase tracking-wider text-slate-200">
              Experiment Runs & Model Comparison ({runs.length})
            </div>

            <div className="overflow-x-auto max-h-80">
              <table className="w-full text-left border-collapse font-mono text-[11px]">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                    <th className="py-1.5 px-2">Run</th>
                    <th className="py-1.5 px-2">Model</th>
                    <th className="py-1.5 px-2">Status</th>
                    <th className="py-1.5 px-2">Test IoU</th>
                    <th className="py-1.5 px-2">Dice</th>
                    <th className="py-1.5 px-2">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {runs.map((r) => {
                    const evalObj = r.evaluations?.[0];
                    return (
                      <tr
                        key={r.id}
                        onClick={() => setSelectedRunId(r.id)}
                        className={`cursor-pointer hover:bg-white/5 ${
                          selectedRun?.id === r.id ? "bg-glacier-400/15" : ""
                        }`}
                      >
                        <td className="py-1.5 px-2 text-slate-200">#{r.id}</td>
                        <td className="py-1.5 px-2 text-glacier-300">
                          {r.model_type}
                        </td>
                        <td className="py-1.5 px-2">{r.status}</td>
                        <td className="py-1.5 px-2">
                          {evalObj?.metrics?.iou != null
                            ? evalObj.metrics.iou.toFixed(3)
                            : "—"}
                        </td>
                        <td className="py-1.5 px-2">
                          {evalObj?.metrics?.dice != null
                            ? evalObj.metrics.dice.toFixed(3)
                            : "—"}
                        </td>
                        <td className="py-1.5 px-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEvaluateRun(r.id);
                            }}
                            className="text-[10px] text-glacier-400 hover:underline"
                          >
                            Evaluate
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Selected Run Curves, Metrics & 2x2 Confusion Matrix */}
          <div className="lg:col-span-7 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3">
            {selectedRun ? (
              <>
                <div className="flex items-center justify-between border-b border-white/10 pb-2">
                  <span className="font-semibold uppercase tracking-wider text-slate-200">
                    Run #{selectedRun.id} ({selectedRun.model_type}) — Training Curves & Evaluation
                  </span>
                  <span className="font-mono text-slate-400">
                    Best Epoch: {selectedRun.best_epoch ?? "—"}
                  </span>
                </div>

                {selectedRun.history && selectedRun.history.length > 0 && (
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={selectedRun.history}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                        <XAxis
                          dataKey="epoch"
                          stroke="#64748b"
                          tick={{ fontSize: 10 }}
                        />
                        <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0b1220",
                            borderColor: "rgba(255,255,255,0.15)",
                            fontSize: 11,
                          }}
                        />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="train_loss"
                          name="Train Loss"
                          stroke="#fb923c"
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="val_loss"
                          name="Val Loss"
                          stroke="#facc15"
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="val_iou"
                          name="Val IoU"
                          stroke="#5ec8e5"
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="val_dice"
                          name="Val Dice"
                          stroke="#4ade80"
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {selectedRun.evaluations &&
                  selectedRun.evaluations.map((ev, i) => (
                    <div
                      key={i}
                      className="grid grid-cols-1 md:grid-cols-12 gap-3 pt-2 border-t border-white/10"
                    >
                      {/* Metrics Table */}
                      <div className="md:col-span-7 space-y-1.5">
                        <div className="font-semibold text-slate-300 text-[11px]">
                          Split: {ev.split.toUpperCase()} ({ev.sample_count}{" "}
                          samples)
                        </div>
                        <div className="grid grid-cols-3 gap-2 font-mono text-[11px]">
                          {Object.entries(ev.metrics || {}).map(([mk, mv]) => (
                            <div
                              key={mk}
                              className="bg-ink-950 p-2 rounded border border-white/5"
                            >
                              <div className="text-[10px] uppercase text-slate-500">
                                {mk}
                              </div>
                              <div className="text-slate-100 font-semibold mt-0.5">
                                {typeof mv === "number" ? mv.toFixed(4) : "—"}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 2x2 Confusion Matrix */}
                      {ev.confusion_matrix && (
                        <div className="md:col-span-5 space-y-1.5">
                          <div className="font-semibold text-slate-300 text-[11px]">
                            2×2 Pixel Confusion Matrix
                          </div>
                          <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px] text-center">
                            <div className="bg-ink-950 p-2 rounded border border-white/5">
                              <div className="text-[10px] text-slate-500">
                                TN (Bg → Bg)
                              </div>
                              <div className="text-slate-200 font-semibold">
                                {ev.confusion_matrix[0]?.[0] ?? 0}
                              </div>
                            </div>
                            <div className="bg-ink-950 p-2 rounded border border-white/5">
                              <div className="text-[10px] text-slate-500">
                                FP (Bg → Lake)
                              </div>
                              <div className="text-amber-300 font-semibold">
                                {ev.confusion_matrix[0]?.[1] ?? 0}
                              </div>
                            </div>
                            <div className="bg-ink-950 p-2 rounded border border-white/5">
                              <div className="text-[10px] text-slate-500">
                                FN (Lake → Bg)
                              </div>
                              <div className="text-hazard-veryhigh font-semibold">
                                {ev.confusion_matrix[1]?.[0] ?? 0}
                              </div>
                            </div>
                            <div className="bg-ink-950 p-2 rounded border border-white/5">
                              <div className="text-[10px] text-slate-500">
                                TP (Lake → Lake)
                              </div>
                              <div className="text-hazard-low font-semibold">
                                {ev.confusion_matrix[1]?.[1] ?? 0}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
              </>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="bg-ink-900 border border-white/10 rounded-md p-8 text-center text-xs text-slate-500">
          No model training runs have been executed yet. Prepare and verify mask tiles above before launching a training run.
        </div>
      )}
    </div>
  );
};
