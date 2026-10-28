"use client";

import React, { useEffect, useState } from "react";
import {
  CheckSquare,
  Filter,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  UserCheck,
  AlertTriangle,
  RefreshCw,
  Eye,
  X,
  MapPin,
  ExternalLink,
  Layers,
  Sparkles,
  CloudRain,
  Activity,
} from "lucide-react";
import { api } from "@/lib/api";
import { CitizenReport } from "@/types";

export default function VerificationQueuePage() {
  const [reports, setReports] = useState<CitizenReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [hazardFilter, setHazardFilter] = useState<string>("all");

  // Detail Modal & Action states
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [reportDetail, setReportDetail] = useState<any | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Action form inputs
  const [reviewNotes, setReviewNotes] = useState("");
  const [actionInProgress, setActionInProgress] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getOfficerQueue(statusFilter, hazardFilter);
      setReports(data);
    } catch (err: any) {
      setError(err.message || "Failed to load verification queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();

    const handleWsEvent = (_e: any) => {
      fetchReports();
    };
    window.addEventListener("officer_ws_message", handleWsEvent);
    return () => window.removeEventListener("officer_ws_message", handleWsEvent);
  }, [statusFilter, hazardFilter]);

  // Open Report Detail Inspector
  const openReportDetail = async (id: number) => {
    setSelectedReportId(id);
    setLoadingDetail(true);
    setReviewNotes("");
    setActionMessage(null);
    try {
      const detail = await api.getReportDetail(id);
      setReportDetail(detail);
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to load report detail." });
    } finally {
      setLoadingDetail(false);
    }
  };

  // Review Actions
  const handleAssignToSelf = async () => {
    if (!selectedReportId) return;
    setActionInProgress(true);
    setActionMessage(null);
    try {
      await api.assignReport(selectedReportId);
      setActionMessage({ type: "success", text: "Report taken under review successfully." });
      await openReportDetail(selectedReportId);
      await fetchReports();
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to assign report." });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleReviewDecision = async (decision: "verified" | "rejected" | "resolved") => {
    if (!selectedReportId) return;
    if (decision === "rejected" && !reviewNotes.trim()) {
      setActionMessage({ type: "error", text: "Rejection requires mandatory remarks / justification." });
      return;
    }

    setActionInProgress(true);
    setActionMessage(null);
    try {
      await api.reviewReport(selectedReportId, decision, reviewNotes);
      setActionMessage({ type: "success", text: `Report successfully marked as ${decision.toUpperCase()}.` });
      await openReportDetail(selectedReportId);
      await fetchReports();
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to submit review decision." });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleReopen = async () => {
    if (!selectedReportId) return;
    if (!reviewNotes.trim()) {
      setActionMessage({ type: "error", text: "Reopening investigation requires justification notes." });
      return;
    }

    setActionInProgress(true);
    setActionMessage(null);
    try {
      await api.reopenReport(selectedReportId, reviewNotes);
      setActionMessage({ type: "success", text: "Report investigation reopened for field verification." });
      await openReportDetail(selectedReportId);
      await fetchReports();
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to reopen report." });
    } finally {
      setActionInProgress(false);
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st.toLowerCase()) {
      case "submitted":
        return "bg-blue-950 text-blue-300 border-blue-800";
      case "under_review":
        return "bg-amber-950 text-amber-300 border-amber-800";
      case "verified":
        return "bg-emerald-950 text-emerald-300 border-emerald-800";
      case "rejected":
        return "bg-rose-950 text-rose-300 border-rose-800";
      case "resolved":
        return "bg-slate-800 text-slate-300 border-slate-700";
      default:
        return "bg-slate-800 text-slate-400";
    }
  };

  return (
    <div className="space-y-5">
      {/* Header and Filter Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-indigo-400" />
            <span>Incident Verification & Response Queue</span>
          </h2>
          <p className="text-xs text-slate-400">
            Triage, corroborate against sensor signals, and publish field emergency reports
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status filter */}
          <select
            aria-label="Filter by Status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 text-xs text-slate-200 border border-slate-800 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-orange-500"
          >
            <option value="all">All Statuses</option>
            <option value="submitted">Submitted (Awaiting Review)</option>
            <option value="under_review">Under Review</option>
            <option value="verified">Verified (Published)</option>
            <option value="rejected">Rejected</option>
            <option value="resolved">Resolved</option>
          </select>

          {/* Hazard filter */}
          <select
            aria-label="Filter by Hazard"
            value={hazardFilter}
            onChange={(e) => setHazardFilter(e.target.value)}
            className="bg-slate-950 text-xs text-slate-200 border border-slate-800 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-orange-500"
          >
            <option value="all">All Hazards</option>
            <option value="flood">Flood / Waterlogging</option>
            <option value="fire">Fire / Smoke</option>
            <option value="landslide">Landslide</option>
            <option value="blocked_road">Blocked Road</option>
          </select>

          <button
            onClick={fetchReports}
            className="text-xs bg-slate-950 hover:bg-slate-850 text-slate-300 border border-slate-800 px-3 py-1.5 rounded-lg flex items-center gap-1 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/60 border border-red-800 p-3 rounded-lg text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Reports Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">ID</th>
                <th className="py-3 px-4">Hazard</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4">Coordinates</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Submitted</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                    <span>Loading verification queue...</span>
                  </td>
                </tr>
              ) : reports.length > 0 ? (
                reports.map((rep) => (
                  <tr key={rep.id} className="hover:bg-slate-850/60 transition">
                    <td className="py-3 px-4 font-mono font-bold text-white">#{rep.id}</td>
                    <td className="py-3 px-4 uppercase font-bold text-indigo-300">
                      {rep.type}
                    </td>
                    <td className="py-3 px-4 max-w-xs truncate text-slate-200" title={rep.description}>
                      {rep.description}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      {rep.latitude.toFixed(4)}, {rep.longitude.toFixed(4)}
                    </td>
                    <td className="py-3 px-4">
                      {rep.confidence_score ? (
                        <span className="font-bold text-emerald-400">
                          {(rep.confidence_score * 100).toFixed(0)}%
                        </span>
                      ) : (
                        <span className="text-slate-500">--</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getStatusBadge(rep.status)}`}>
                        {rep.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {new Date(rep.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => openReportDetail(rep.id)}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-3 py-1 rounded text-xs transition"
                      >
                        Inspect & Review
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    No reports match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Report Detail & Review Modal */}
      {selectedReportId && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-base font-black text-white">
                  Report #{selectedReportId}
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${getStatusBadge(reportDetail?.report?.status || "")}`}>
                  {reportDetail?.report?.status}
                </span>
              </div>
              <button
                onClick={() => {
                  setSelectedReportId(null);
                  setReportDetail(null);
                }}
                className="text-slate-400 hover:text-white font-bold text-sm"
              >
                ✕
              </button>
            </div>

            {loadingDetail ? (
              <div className="py-16 text-center text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                <span>Loading report details, duplicates & observations...</span>
              </div>
            ) : reportDetail?.report ? (
              <div className="space-y-4">
                {/* Description & Location */}
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                    Citizen Submission Description:
                  </span>
                  <p className="text-sm text-slate-100 leading-relaxed">
                    {reportDetail.report.description}
                  </p>
                  <div className="pt-2 flex flex-wrap items-center gap-4 text-xs text-slate-400 border-t border-slate-900">
                    <span>
                      <strong>Hazard Type:</strong> {reportDetail.report.type.toUpperCase()}
                    </span>
                    <span>
                      <strong>GPS:</strong> {reportDetail.report.latitude.toFixed(5)}, {reportDetail.report.longitude.toFixed(5)}
                    </span>
                    <span>
                      <strong>Confidence:</strong> {(reportDetail.report.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Supporting Sensor Observations */}
                {reportDetail.observations?.length > 0 && (
                  <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800 space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                      <CloudRain className="w-3.5 h-3.5" />
                      <span>District Sensor Corroboration:</span>
                    </span>
                    <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                      {reportDetail.observations.map((obs: any, idx: number) => (
                        <div key={idx} className="bg-slate-900 p-2 rounded border border-slate-800">
                          <span className="text-[10px] text-slate-500 block uppercase">{obs.hazard_type}</span>
                          <span className="font-semibold">{JSON.stringify(obs.values)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Potential Duplicate Detection (ML) */}
                {reportDetail.potential_duplicates?.length > 0 && (
                  <div className="bg-amber-950/40 p-3 rounded-lg border border-amber-800/80 space-y-1.5">
                    <span className="text-[11px] font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                      <span>Machine Learning Duplicate Warning:</span>
                    </span>
                    <p className="text-xs text-amber-200">
                      Similar reports detected within same timeframe in this district:
                    </p>
                    <div className="space-y-1">
                      {reportDetail.potential_duplicates.map((dup: any) => (
                        <div key={dup.id} className="text-xs bg-slate-950 p-2 rounded border border-slate-800 flex justify-between">
                          <span className="text-slate-300 line-clamp-1">#{dup.id}: {dup.description}</span>
                          <span className="text-amber-400 font-bold ml-2">{(dup.similarity_score * 100).toFixed(0)}% Match</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Review Notes Input */}
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                    Officer Review Notes / Verification Remarks:
                  </label>
                  <textarea
                    rows={2}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Enter factual justification for verification, rejection, or resolution..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                {actionMessage && (
                  <div className={`p-2.5 rounded text-xs font-semibold ${
                    actionMessage.type === "success"
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      : "bg-red-950 text-red-300 border border-red-800"
                  }`}>
                    {actionMessage.text}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800">
                  {/* Take under review */}
                  {reportDetail.report.status === "submitted" && (
                    <button
                      onClick={handleAssignToSelf}
                      disabled={actionInProgress}
                      className="bg-amber-600 hover:bg-amber-500 text-white font-bold px-3 py-2 rounded text-xs transition"
                    >
                      Take Under Review
                    </button>
                  )}

                  {/* Verify */}
                  <button
                    onClick={() => handleReviewDecision("verified")}
                    disabled={actionInProgress}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-2 rounded text-xs transition flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Verify (Publish to Public Map)</span>
                  </button>

                  {/* Reject */}
                  <button
                    onClick={() => handleReviewDecision("rejected")}
                    disabled={actionInProgress}
                    className="bg-rose-700 hover:bg-rose-600 text-white font-bold px-3 py-2 rounded text-xs transition flex items-center gap-1"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>

                  {/* Resolve */}
                  {reportDetail.report.status === "verified" && (
                    <button
                      onClick={() => handleReviewDecision("resolved")}
                      disabled={actionInProgress}
                      className="bg-slate-700 hover:bg-slate-600 text-white font-bold px-3 py-2 rounded text-xs transition"
                    >
                      Mark Resolved
                    </button>
                  )}

                  {/* Reopen */}
                  {(reportDetail.report.status === "rejected" || reportDetail.report.status === "resolved") && (
                    <button
                      onClick={handleReopen}
                      disabled={actionInProgress}
                      className="bg-purple-700 hover:bg-purple-600 text-white font-bold px-3 py-2 rounded text-xs transition flex items-center gap-1"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Reopen Investigation</span>
                    </button>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
