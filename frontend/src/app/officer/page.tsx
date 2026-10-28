"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Send,
  Map,
  History,
  Activity,
  Layers,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";

export default function OfficerDashboardPage() {
  const [metricsData, setMetricsData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getOfficerMetrics();
      setMetricsData(data);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve command metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();

    // Listen for live WebSocket broadcasts from officer layout
    const handleWsEvent = (_e: any) => {
      fetchMetrics();
    };

    window.addEventListener("officer_ws_message", handleWsEvent);
    return () => window.removeEventListener("officer_ws_message", handleWsEvent);
  }, []);

  const metrics = metricsData?.metrics || {
    submitted: 0,
    under_review: 0,
    verified: 0,
    rejected: 0,
    resolved: 0,
    unresolved: 0,
    total_reports: 0,
    active_alerts: 0,
  };

  return (
    <div className="space-y-6">
      {/* Top Controls & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-400" />
            <span>Incident Response Operations Summary</span>
          </h2>
          <p className="text-xs text-slate-400">
            Real-time status of field reports and active disaster advisories within assigned boundary
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchMetrics}
            className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Counts</span>
          </button>
          <Link
            href="/officer/alerts/new"
            className="text-xs bg-orange-600 hover:bg-orange-500 text-white font-bold px-3 py-1.5 rounded-lg flex items-center gap-1 transition"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Compose Alert</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/60 border border-red-800 p-3 rounded-lg flex items-center gap-2 text-xs text-red-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Primary Operational Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Submitted */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1 shadow-sm">
          <div className="flex items-center justify-between text-blue-400">
            <span className="text-xs font-bold uppercase tracking-wider">Submitted</span>
            <FileText className="w-4 h-4" />
          </div>
          <span className="text-2xl font-black text-white block">
            {metrics.submitted}
          </span>
          <span className="text-[10px] text-slate-400 block leading-tight">
            Awaiting officer triage
          </span>
        </div>

        {/* Under Review */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1 shadow-sm">
          <div className="flex items-center justify-between text-amber-400">
            <span className="text-xs font-bold uppercase tracking-wider">Under Review</span>
            <Clock className="w-4 h-4" />
          </div>
          <span className="text-2xl font-black text-white block">
            {metrics.under_review}
          </span>
          <span className="text-[10px] text-slate-400 block leading-tight">
            Assigned to ground officer
          </span>
        </div>

        {/* Verified */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1 shadow-sm">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-xs font-bold uppercase tracking-wider">Verified</span>
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <span className="text-2xl font-black text-white block">
            {metrics.verified}
          </span>
          <span className="text-[10px] text-slate-400 block leading-tight">
            Published to public map
          </span>
        </div>

        {/* Rejected */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1 shadow-sm">
          <div className="flex items-center justify-between text-rose-400">
            <span className="text-xs font-bold uppercase tracking-wider">Rejected</span>
            <XCircle className="w-4 h-4" />
          </div>
          <span className="text-2xl font-black text-white block">
            {metrics.rejected}
          </span>
          <span className="text-[10px] text-slate-400 block leading-tight">
            Unsubstantiated / Duplicates
          </span>
        </div>

        {/* Unresolved (Critical Intervention Metric) */}
        <div className="bg-slate-900 border-2 border-orange-600/70 rounded-xl p-4 space-y-1 shadow-sm bg-gradient-to-b from-orange-950/20 to-slate-900">
          <div className="flex items-center justify-between text-orange-400">
            <span className="text-xs font-bold uppercase tracking-wider">Unresolved</span>
            <AlertTriangle className="w-4 h-4 animate-pulse" />
          </div>
          <span className="text-2xl font-black text-orange-400 block">
            {metrics.unresolved}
          </span>
          <span className="text-[10px] text-slate-400 block leading-tight">
            Active field incidents
          </span>
        </div>

        {/* Active Alerts */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1 shadow-sm">
          <div className="flex items-center justify-between text-red-400">
            <span className="text-xs font-bold uppercase tracking-wider">Active Alerts</span>
            <ShieldAlert className="w-4 h-4" />
          </div>
          <span className="text-2xl font-black text-white block">
            {metrics.active_alerts}
          </span>
          <span className="text-[10px] text-slate-400 block leading-tight">
            Broadcasted bulletins
          </span>
        </div>
      </div>

      {/* Main Grid: Operational Quick Links & Recent Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Operational Workflows */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Operational Workflows
          </h3>

          <Link
            href="/officer/queue"
            className="bg-slate-900 hover:bg-slate-850 border border-slate-800 p-4 rounded-xl flex items-center justify-between transition group shadow-sm block"
          >
            <div className="flex items-center gap-3">
              <div className="bg-blue-600/10 p-2.5 rounded-lg border border-blue-500/20 text-blue-400 group-hover:scale-105 transition-transform">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-sm text-white block">
                  Incident Verification Queue
                </span>
                <span className="text-xs text-slate-400 block">
                  {metrics.submitted + metrics.under_review} reports awaiting officer decision
                </span>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-white transition" />
          </Link>

          <Link
            href="/officer/alerts/new"
            className="bg-slate-900 hover:bg-slate-850 border border-slate-800 p-4 rounded-xl flex items-center justify-between transition group shadow-sm block"
          >
            <div className="flex items-center gap-3">
              <div className="bg-orange-600/10 p-2.5 rounded-lg border border-orange-500/20 text-orange-400 group-hover:scale-105 transition-transform">
                <Send className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-sm text-white block">
                  Compose Disaster Alert
                </span>
                <span className="text-xs text-slate-400 block">
                  Draft or issue geo-targeted warnings
                </span>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-white transition" />
          </Link>

          <Link
            href="/officer/map"
            className="bg-slate-900 hover:bg-slate-850 border border-slate-800 p-4 rounded-xl flex items-center justify-between transition group shadow-sm block"
          >
            <div className="flex items-center gap-3">
              <div className="bg-purple-600/10 p-2.5 rounded-lg border border-purple-500/20 text-purple-400 group-hover:scale-105 transition-transform">
                <Map className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-sm text-white block">
                  Officer Operational Map
                </span>
                <span className="text-xs text-slate-400 block">
                  Inspect unverified, verified & rejected reports
                </span>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-white transition" />
          </Link>

          <Link
            href="/officer/audit"
            className="bg-slate-900 hover:bg-slate-850 border border-slate-800 p-4 rounded-xl flex items-center justify-between transition group shadow-sm block"
          >
            <div className="flex items-center gap-3">
              <div className="bg-emerald-600/10 p-2.5 rounded-lg border border-emerald-500/20 text-emerald-400 group-hover:scale-105 transition-transform">
                <History className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-sm text-white block">
                  Audit Trail & History
                </span>
                <span className="text-xs text-slate-400 block">
                  Verify officer actions and compliance records
                </span>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-white transition" />
          </Link>
        </div>

        {/* Recent Activity / Audit Feed */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <History className="w-4 h-4 text-indigo-400" />
              <span>Live Operational Event Feed</span>
            </h3>
            <span className="text-[10px] text-slate-500">
              Auto-updating via PostgreSQL & WebSockets
            </span>
          </div>

          <div className="space-y-2.5">
            {metricsData?.recent_activity?.length > 0 ? (
              metricsData.recent_activity.map((event: any) => (
                <div
                  key={event.id}
                  className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 flex items-center justify-between text-xs"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-300">
                        {event.action.replace(/_/g, " ").toUpperCase()}
                      </span>
                      <span className="text-[11px] bg-slate-800 text-slate-400 px-1.5 py-0.2 rounded font-mono">
                        {event.affected_record}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400 block">
                      Actor: {event.actor}
                    </span>
                  </div>

                  <span className="text-[11px] text-slate-500">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 text-center py-6">
                No recent activity logged yet.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
