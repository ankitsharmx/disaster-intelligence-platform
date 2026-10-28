"use client";

import React, { useEffect, useState } from "react";
import {
  History,
  Filter,
  Search,
  RefreshCw,
  Eye,
  X,
  FileCode,
  ShieldCheck,
  User,
} from "lucide-react";
import { api } from "@/lib/api";

export default function AuditTrailPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [actionFilter, setActionFilter] = useState<string>("");
  const [actorFilter, setActorFilter] = useState<string>("");
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);

  const fetchAuditEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuditEvents(
        actionFilter || undefined,
        actorFilter || undefined
      );
      setEvents(data);
    } catch (err: any) {
      setError(err.message || "Failed to load audit records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditEvents();
  }, [actionFilter]);

  return (
    <div className="space-y-5">
      {/* Header and Filter Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-400" />
            <span>Immutable Administrative Audit Trail</span>
          </h2>
          <p className="text-xs text-slate-400">
            Compliance and accountability records for all incident reviews, alert broadcasts, and user actions
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Action Filter */}
          <select
            aria-label="Filter Audit Logs by Action"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-slate-950 text-xs text-slate-200 border border-slate-800 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-semibold"
          >
            <option value="">All Actions</option>
            <option value="report_decision_verified">Verified Reports</option>
            <option value="report_decision_rejected">Rejected Reports</option>
            <option value="report_reopened">Reopened Reports</option>
            <option value="report_assigned">Officer Assignments</option>
            <option value="alert_issued">Alerts Issued</option>
            <option value="alert_cancelled">Alerts Cancelled</option>
            <option value="report_submitted">Citizen Submissions</option>
          </select>

          {/* Actor Filter Input */}
          <input
            type="text"
            placeholder="Filter by actor email..."
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchAuditEvents()}
            className="bg-slate-950 text-xs text-slate-200 border border-slate-800 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />

          <button
            onClick={fetchAuditEvents}
            className="text-xs bg-slate-950 hover:bg-slate-850 text-slate-300 border border-slate-800 px-3 py-1.5 rounded-lg flex items-center gap-1 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Search</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/60 border border-red-800 p-3 rounded-lg text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Events Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Log ID</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Affected Record</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                    <span>Loading audit records...</span>
                  </td>
                </tr>
              ) : events.length > 0 ? (
                events.map((evt) => (
                  <tr key={evt.id} className="hover:bg-slate-850/60 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-400">#{evt.id}</td>
                    <td className="py-3 px-4">
                      <span className="font-bold text-indigo-300 bg-indigo-950/60 border border-indigo-800/80 px-2 py-0.5 rounded text-[11px]">
                        {evt.action.replace(/_/g, " ").toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-200">
                      {evt.actor}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      {evt.affected_record}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {new Date(evt.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedEvent(evt)}
                        className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded text-xs transition"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    No audit records match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Detail Inspector Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileCode className="w-5 h-5 text-indigo-400" />
                <span className="font-bold text-sm text-white">
                  Audit Record #{selectedEvent.id}
                </span>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-white font-bold text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs text-slate-300">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1">
                <p><strong>Action:</strong> {selectedEvent.action}</p>
                <p><strong>Actor:</strong> {selectedEvent.actor}</p>
                <p><strong>Target Record:</strong> {selectedEvent.affected_record}</p>
                <p><strong>Recorded At:</strong> {new Date(selectedEvent.timestamp).toLocaleString()}</p>
              </div>

              <div>
                <span className="text-[11px] font-bold uppercase text-slate-400 block mb-1">
                  Metadata & Parameters:
                </span>
                <pre className="bg-slate-950 border border-slate-800 p-3 rounded-lg text-[11px] font-mono text-emerald-300 overflow-x-auto">
                  {JSON.stringify(selectedEvent.details, null, 2)}
                </pre>
              </div>
            </div>

            <button
              onClick={() => setSelectedEvent(null)}
              className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-2 rounded text-xs transition"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
