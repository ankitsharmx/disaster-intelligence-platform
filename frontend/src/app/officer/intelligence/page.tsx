"use client";

import React, { useEffect, useState } from "react";
import {
  Cpu,
  ShieldAlert,
  AlertTriangle,
  Layers,
  CheckCircle2,
  BarChart3,
  Search,
  RefreshCw,
  FileText,
  Activity,
  Info,
  MapPin,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api";

export default function OfficerIntelligencePage() {
  const [districtId, setDistrictId] = useState<number>(2); // Default Mumbai Suburban
  const [districtRisk, setDistrictRisk] = useState<any | null>(null);
  const [mlBenchmark, setMlBenchmark] = useState<any | null>(null);
  const [duplicateClusters, setDuplicateClusters] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Confidence Evaluator Sandbox State
  const [testDesc, setTestDesc] = useState(
    "Severe flash flooding near Milan subway underpass with trapped cars and water entering low-lying shops."
  );
  const [testLat, setTestLat] = useState(19.098);
  const [testLon, setTestLon] = useState(72.843);
  const [testMedia, setTestMedia] = useState(true);
  const [testSensor, setTestSensor] = useState(true);
  const [confidenceResult, setConfidenceResult] = useState<any | null>(null);
  const [evaluatingConfidence, setEvaluatingConfidence] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [riskRes, mlRes, dupRes] = await Promise.all([
        api.getDistrictRisk(districtId),
        api.getMLBenchmark(),
        api.getDuplicateClusters(districtId),
      ]);
      setDistrictRisk(riskRes);
      setMlBenchmark(mlRes);
      setDuplicateClusters(dupRes);
    } catch (err: any) {
      setError(err.message || "Failed to load intelligence data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [districtId]);

  const handleEvaluateConfidence = async (e: React.FormEvent) => {
    e.preventDefault();
    setEvaluatingConfidence(true);
    try {
      const res = await api.evaluateReportConfidence({
        description: testDesc,
        latitude: testLat,
        longitude: testLon,
        has_media: testMedia,
        nearby_sensor_active: testSensor,
        hazard_type: "flood",
      });
      setConfidenceResult(res);
    } catch (err: any) {
      console.error(err);
    } finally {
      setEvaluatingConfidence(false);
    }
  };

  const districts = [
    { id: 1, name: "Mumbai City (Coastal Plains)" },
    { id: 2, name: "Mumbai Suburban (Urban Lowlands)" },
    { id: 3, name: "Thane (Creek & Foothills)" },
    { id: 4, name: "Pune (River Basin & Plateau)" },
    { id: 5, name: "Raigad (Western Ghats Scarps)" },
    { id: 6, name: "Ratnagiri (Coastal Hills)" },
  ];

  return (
    <div className="space-y-6">
      {/* Header with District Selector & Reload */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-cyan-600/20 text-cyan-400 p-2.5 rounded-lg border border-cyan-800/50">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Disaster Intelligence & Machine Learning Engine</span>
              <span className="text-xs bg-cyan-950 text-cyan-400 px-2.5 py-0.5 rounded-full border border-cyan-800 font-mono">
                Phase 5 Python Core
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Deterministic rule engines, explainable credibility scoring, and scikit-learn model benchmark
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">District:</span>
            <select
              value={districtId}
              onChange={(e) => setDistrictId(Number(e.target.value))}
              className="bg-transparent text-xs text-white font-bold focus:outline-none cursor-pointer"
            >
              {districts.map((d) => (
                <option key={d.id} value={d.id} className="bg-slate-900 text-white">
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Mandatory Indicative Risk Notice */}
      <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-3.5 flex items-start gap-3 text-amber-200 text-xs">
        <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block text-amber-300">
            Indicative Risk & Ethical Policy Notice:
          </span>
          All risk assessments and ML classifications computed here are indicative estimates derived from IMD meteorological criteria, CWC hydrological stages, and GSI terrain slope factors. They are not official government warnings. Official public alerts are drafted and authorized separately via the Alert Composer.
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 p-4 rounded-xl text-xs">
          {error}
        </div>
      )}

      {/* SECTION 1: Indicative Multi-Hazard Risk Synthesis */}
      {districtRisk && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Flood Risk Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="bg-blue-600/20 text-blue-400 p-2 rounded-lg border border-blue-800/40">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Indicative Flood Risk</h3>
                  <span className="text-[11px] text-slate-400 font-mono">
                    Method: {districtRisk.hazards.flood.method}
                  </span>
                </div>
              </div>

              <span
                className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider border ${
                  districtRisk.hazards.flood.riskLevel === "CRITICAL"
                    ? "bg-rose-950 text-rose-300 border-rose-800 animate-pulse"
                    : districtRisk.hazards.flood.riskLevel === "HIGH"
                    ? "bg-orange-950 text-orange-300 border-orange-800"
                    : districtRisk.hazards.flood.riskLevel === "MEDIUM"
                    ? "bg-amber-950 text-amber-300 border-amber-800"
                    : "bg-emerald-950 text-emerald-300 border-emerald-800"
                }`}
              >
                {districtRisk.hazards.flood.riskLevel}
              </span>
            </div>

            {/* Contributing Factors */}
            <div className="grid grid-cols-3 gap-2.5 text-center">
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Rainfall Factor</span>
                <span className="text-xs font-bold text-white capitalize">
                  {districtRisk.hazards.flood.factors.rainfall}
                </span>
              </div>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">River Stage</span>
                <span className="text-xs font-bold text-white capitalize">
                  {districtRisk.hazards.flood.factors.riverLevel.replace("_", " ")}
                </span>
              </div>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Vulnerability</span>
                <span className="text-xs font-bold text-white capitalize">
                  {districtRisk.hazards.flood.factors.historicalFloods.replace("_", " ")}
                </span>
              </div>
            </div>

            {/* Metrics */}
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5">
              <div className="flex justify-between text-slate-300">
                <span>Rainfall 1-Hour:</span>
                <span className="font-mono font-bold text-white">
                  {districtRisk.hazards.flood.metrics.rainfall_1h_mm} mm
                </span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Rainfall 24-Hour:</span>
                <span className="font-mono font-bold text-white">
                  {districtRisk.hazards.flood.metrics.rainfall_24h_mm} mm
                </span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>River Water Level:</span>
                <span className="font-mono font-bold text-white">
                  {districtRisk.hazards.flood.metrics.water_level_meters} m (Danger: {districtRisk.hazards.flood.metrics.danger_mark_meters} m)
                </span>
              </div>
            </div>

            <div className="text-xs text-slate-300 bg-blue-950/20 border border-blue-900/40 p-2.5 rounded-lg">
              <span className="font-bold text-blue-300 block mb-1">Recommended Action:</span>
              {districtRisk.hazards.flood.recommendedAction}
            </div>
          </div>

          {/* Landslide Risk Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="bg-amber-600/20 text-amber-400 p-2 rounded-lg border border-amber-800/40">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Indicative Landslide Risk</h3>
                  <span className="text-[11px] text-slate-400 font-mono">
                    Method: {districtRisk.hazards.landslide.method}
                  </span>
                </div>
              </div>

              <span
                className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider border ${
                  districtRisk.hazards.landslide.riskLevel === "CRITICAL"
                    ? "bg-rose-950 text-rose-300 border-rose-800 animate-pulse"
                    : districtRisk.hazards.landslide.riskLevel === "HIGH"
                    ? "bg-orange-950 text-orange-300 border-orange-800"
                    : districtRisk.hazards.landslide.riskLevel === "MEDIUM"
                    ? "bg-amber-950 text-amber-300 border-amber-800"
                    : "bg-emerald-950 text-emerald-300 border-emerald-800"
                }`}
              >
                {districtRisk.hazards.landslide.riskLevel}
              </span>
            </div>

            {/* Contributing Factors */}
            <div className="grid grid-cols-3 gap-2.5 text-center">
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Terrain Slope</span>
                <span className="text-xs font-bold text-white capitalize">
                  {districtRisk.hazards.landslide.factors.terrainSlope.replace(/_/g, " ")}
                </span>
              </div>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Antecedent Rain</span>
                <span className="text-xs font-bold text-white capitalize">
                  {districtRisk.hazards.landslide.factors.rainfallAccumulation.replace(/_/g, " ")}
                </span>
              </div>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Soil Moisture</span>
                <span className="text-xs font-bold text-white">
                  {districtRisk.hazards.landslide.factors.soilSaturation}
                </span>
              </div>
            </div>

            {/* Metrics */}
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5">
              <div className="flex justify-between text-slate-300">
                <span>Antecedent 72-Hour Rain:</span>
                <span className="font-mono font-bold text-white">
                  {districtRisk.hazards.landslide.metrics.rainfall_72h_mm} mm
                </span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Maximum Scarp Slope:</span>
                <span className="font-mono font-bold text-white">
                  {districtRisk.hazards.landslide.metrics.max_slope_deg}° (Avg: {districtRisk.hazards.landslide.metrics.avg_slope_deg}°)
                </span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>ML Model Concordance:</span>
                <span className="font-mono font-bold text-cyan-400">
                  {districtRisk.ml_comparative_baseline.predicted_risk_level} (RF Prob: {Math.round(districtRisk.ml_comparative_baseline.probabilities[districtRisk.ml_comparative_baseline.predicted_risk_level] * 100)}%)
                </span>
              </div>
            </div>

            <div className="text-xs text-slate-300 bg-amber-950/20 border border-amber-900/40 p-2.5 rounded-lg">
              <span className="font-bold text-amber-300 block mb-1">Recommended Action:</span>
              {districtRisk.hazards.landslide.recommendedAction}
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: scikit-learn ML Model Benchmark vs Rule-Based Engine */}
      {mlBenchmark && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-indigo-400" />
                <span>scikit-learn Classifier Benchmark vs Deterministic Rule Engine</span>
              </h3>
              <p className="text-xs text-slate-400">
                Stratified 80/20 train/test split on {mlBenchmark.dataset_summary.total_samples} samples ({mlBenchmark.dataset_summary.geographic_coverage})
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Concordance Rate:</span>
              <span className="bg-emerald-950 text-emerald-300 font-mono font-black px-2.5 py-1 rounded border border-emerald-800">
                {mlBenchmark.rule_vs_ml_concordance.test_set_concordance_pct}%
              </span>
            </div>
          </div>

          {/* Metric KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-400 block font-medium">Test Set Accuracy</span>
              <span className="text-2xl font-black text-white font-mono">
                {Math.round(mlBenchmark.random_forest_metrics.accuracy * 1000) / 10}%
              </span>
              <span className="text-[10px] text-slate-500 block mt-1">RandomForestClassifier</span>
            </div>
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-400 block font-medium">Macro F1-Score</span>
              <span className="text-2xl font-black text-cyan-400 font-mono">
                {mlBenchmark.random_forest_metrics.macro_f1}
              </span>
              <span className="text-[10px] text-slate-500 block mt-1">Balanced across classes</span>
            </div>
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-400 block font-medium">Macro Precision</span>
              <span className="text-2xl font-black text-indigo-400 font-mono">
                {mlBenchmark.random_forest_metrics.macro_precision}
              </span>
              <span className="text-[10px] text-slate-500 block mt-1">Low false alarm rate</span>
            </div>
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-400 block font-medium">Macro Recall</span>
              <span className="text-2xl font-black text-emerald-400 font-mono">
                {mlBenchmark.random_forest_metrics.macro_recall}
              </span>
              <span className="text-[10px] text-slate-500 block mt-1">High disaster capture</span>
            </div>
          </div>

          {/* Confusion Matrix and Feature Importances */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
            {/* Confusion Matrix */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
              <span className="text-xs font-bold text-white block">
                Test Set Confusion Matrix (4x4 Multiclass)
              </span>
              <div className="overflow-x-auto">
                <table className="w-full text-center text-xs">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-800">
                      <th className="p-2 text-left">Actual \ Pred</th>
                      {mlBenchmark.random_forest_metrics.confusion_matrix.labels.map((l: string) => (
                        <th key={l} className="p-2 font-mono">{l}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {mlBenchmark.random_forest_metrics.confusion_matrix.matrix.map((row: number[], rIdx: number) => (
                      <tr key={rIdx} className="border-b border-slate-900">
                        <td className="p-2 text-left font-bold text-slate-300 font-mono">
                          {mlBenchmark.random_forest_metrics.confusion_matrix.labels[rIdx]}
                        </td>
                        {row.map((cell: number, cIdx: number) => {
                          const isDiag = rIdx === cIdx;
                          return (
                            <td
                              key={cIdx}
                              className={`p-2 font-mono font-bold ${
                                isDiag
                                  ? cell > 0
                                    ? "bg-emerald-950/60 text-emerald-300"
                                    : "text-slate-500"
                                  : cell > 0
                                  ? "bg-rose-950/50 text-rose-300"
                                  : "text-slate-600"
                              }`}
                            >
                              {cell}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Top Feature Importances */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
              <span className="text-xs font-bold text-white block">
                Top Gini Feature Importances (Random Forest)
              </span>
              <div className="space-y-2">
                {mlBenchmark.feature_importances.slice(0, 6).map((f: any) => (
                  <div key={f.feature} className="space-y-1">
                    <div className="flex justify-between text-xs text-slate-300">
                      <span className="font-mono">{f.feature}</span>
                      <span className="font-bold text-indigo-400">{Math.round(f.importance * 100)}%</span>
                    </div>
                    <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-indigo-500 h-1.5 rounded-full"
                        style={{ width: `${Math.min(100, f.importance * 250)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: Duplicate Report Clusters Inspector */}
      {duplicateClusters && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="bg-purple-600/20 text-purple-400 p-2 rounded-lg border border-purple-800/40">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Spatio-Temporal Duplicate Clusters</h3>
                <span className="text-xs text-slate-400">
                  {duplicateClusters.duplicate_clusters_count} suspected duplicate groups identified out of {duplicateClusters.total_active_reports} active submissions
                </span>
              </div>
            </div>

            <span className="text-xs text-slate-400 bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
              Policy: Grouped for review, never auto-deleted
            </span>
          </div>

          {duplicateClusters.duplicate_clusters.length === 0 ? (
            <div className="text-center py-6 text-slate-400 text-xs bg-slate-950 rounded-xl border border-slate-800/60">
              No duplicate clusters detected in active review queue.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {duplicateClusters.duplicate_clusters.map((c: any) => (
                <div key={c.cluster_id} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">
                      Cluster #{c.cluster_id} — Primary Report #{c.primary_report_id}
                    </span>
                    <span className="text-[11px] bg-purple-950 text-purple-300 px-2 py-0.5 rounded border border-purple-800 font-bold">
                      {c.member_count} Corroborating Reports
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 italic line-clamp-2">
                    &ldquo;{c.sample_descriptions[0]}&rdquo;
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-900 pt-2 font-mono">
                    <span>Radius: {c.radius_meters}m</span>
                    <span>Centroid: [{c.centroid[0]}, {c.centroid[1]}]</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SECTION 4: Interactive Report Credibility Scoring Sandbox */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
        <div className="border-b border-slate-800 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span>Interactive Report Credibility & Confidence Evaluator</span>
          </h3>
          <p className="text-xs text-slate-400">
            Simulate report attributes to inspect explainable multi-signal weight breakdown
          </p>
        </div>

        <form onSubmit={handleEvaluateConfidence} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2 space-y-3">
            <div>
              <label className="text-xs text-slate-300 block mb-1 font-medium">Incident Description:</label>
              <textarea
                value={testDesc}
                onChange={(e) => setTestDesc(e.target.value)}
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-300 block mb-1">Latitude:</label>
                <input
                  type="number"
                  step="0.0001"
                  value={testLat}
                  onChange={(e) => setTestLat(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white"
                />
              </div>
              <div>
                <label className="text-xs text-slate-300 block mb-1">Longitude:</label>
                <input
                  type="number"
                  step="0.0001"
                  value={testLon}
                  onChange={(e) => setTestLon(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white"
                />
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs text-slate-300 pt-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={testMedia}
                  onChange={(e) => setTestMedia(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0"
                />
                <span>Photographic Evidence Attached</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={testSensor}
                  onChange={(e) => setTestSensor(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0"
                />
                <span>Nearby Sensor Corroboration</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={evaluatingConfidence}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition"
            >
              {evaluatingConfidence ? "Evaluating..." : "Evaluate Confidence"}
            </button>
          </div>

          {/* Results Panel */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
            {confidenceResult ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                  <span className="text-xs text-slate-400">Calculated Credibility:</span>
                  <span
                    className={`text-xs font-black px-2.5 py-0.5 rounded border ${
                      confidenceResult.confidence_level === "HIGH"
                        ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                        : confidenceResult.confidence_level === "MEDIUM"
                        ? "bg-amber-950 text-amber-300 border-amber-800"
                        : "bg-rose-950 text-rose-300 border-rose-800"
                    }`}
                  >
                    {confidenceResult.confidence_level} ({Math.round(confidenceResult.confidence_score * 100)}%)
                  </span>
                </div>

                <div className="space-y-2 max-h-44 overflow-y-auto text-[11px]">
                  {confidenceResult.contributing_factors.map((f: any, idx: number) => (
                    <div key={idx} className="flex items-start justify-between gap-2 border-b border-slate-900/50 pb-1">
                      <span className="text-slate-300">{f.detail}</span>
                      <span
                        className={`font-mono font-bold shrink-0 ${
                          f.delta > 0
                            ? "text-emerald-400"
                            : f.delta < 0
                            ? "text-rose-400"
                            : "text-slate-500"
                        }`}
                      >
                        {f.delta > 0 ? `+${f.delta}` : f.delta}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-center text-xs text-slate-500">
                Click &ldquo;Evaluate Confidence&rdquo; to compute multi-signal breakdown.
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
