"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Send,
  AlertTriangle,
  Calendar,
  Building2,
  MapPin,
  CheckCircle2,
  Clock,
  Radio,
  Eye,
  AlertCircle,
  FileText,
} from "lucide-react";
import { api } from "@/lib/api";
import { District } from "@/types";

export default function AlertComposerPage() {
  const router = useRouter();
  const [districts, setDistricts] = useState<District[]>([]);
  const [officerMetrics, setOfficerMetrics] = useState<any | null>(null);

  // Form State
  const [title, setTitle] = useState("");
  const [type, setType] = useState("flood");
  const [severity, setSeverity] = useState("high");
  const [issuer, setIssuer] = useState("District Disaster Operations Command");
  const [description, setDescription] = useState("");
  const [selectedDistrictId, setSelectedDistrictId] = useState<number>(2);
  const [validFrom, setValidFrom] = useState(new Date().toISOString().slice(0, 16));
  const [validTo, setValidTo] = useState(
    new Date(Date.now() + 6 * 3600 * 1000).toISOString().slice(0, 16)
  );
  const [isOfficial, setIsOfficial] = useState(false); // Default to simulated exercise alert

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [dists, metrics] = await Promise.all([
          api.getDistricts(),
          api.getOfficerMetrics(),
        ]);
        setDistricts(dists);
        setOfficerMetrics(metrics);

        // Pre-select officer's assigned district
        if (metrics.jurisdiction.assigned_district_id) {
          setSelectedDistrictId(metrics.jurisdiction.assigned_district_id);
        } else if (dists.length > 0) {
          setSelectedDistrictId(dists[0].id);
        }
      } catch (err: any) {
        console.error("Failed to load initial data", err);
      }
    }
    loadData();
  }, []);

  const handleSubmitAlert = async (asDraft: boolean) => {
    if (!title.trim() || !description.trim()) {
      setError("Please provide an alert title and emergency advisory instructions.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await api.createAlert({
        title,
        type,
        severity,
        issuer,
        description,
        valid_from: new Date(validFrom).toISOString(),
        valid_to: new Date(validTo).toISOString(),
        district_ids: [selectedDistrictId],
        is_official: isOfficial,
        as_draft: asDraft,
      });

      setSuccessMessage(
        asDraft
          ? "Alert drafted successfully. Saved to draft bulletins."
          : "Disaster Alert issued & broadcasted live to citizen portal!"
      );

      // Reset
      setTitle("");
      setDescription("");
    } catch (err: any) {
      setError(err.message || "Failed to create alert.");
    } finally {
      setSubmitting(false);
    }
  };

  const selectedDistObj = districts.find((d) => d.id === selectedDistrictId);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Send className="w-5 h-5 text-orange-500" />
            <span>Emergency Alert Composer</span>
          </h2>
          <p className="text-xs text-slate-400">
            Authoritative bulletin creation with geographic targeting and live broadcast preview
          </p>
        </div>

        {/* Official vs Exercise Simulation Tag */}
        <div className="flex items-center gap-2 bg-slate-950 p-2 rounded-lg border border-slate-800 text-xs">
          <input
            type="checkbox"
            id="official-check"
            checked={isOfficial}
            onChange={(e) => setIsOfficial(e.target.checked)}
            className="rounded border-slate-700 text-red-600 focus:ring-red-500"
          />
          <label htmlFor="official-check" className="cursor-pointer text-slate-300 font-semibold">
            {isOfficial ? "🔴 Official Govt Warning" : "🟡 Simulated Platform Exercise"}
          </label>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/60 border border-red-800 p-3 rounded-lg text-xs text-red-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMessage && (
        <div className="bg-emerald-950 border border-emerald-800 p-3 rounded-lg text-xs text-emerald-300 flex items-center gap-2 font-semibold">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form Inputs (2 Cols) */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          {/* Title */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              Alert Title *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Flash Flood Warning: Rapid Inundation in Low-Lying Wards"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-orange-500 font-medium"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Hazard Type */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Hazard Category *
              </label>
              <select
                aria-label="Hazard Category"
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white"
              >
                <option value="flood">Flood / Inundation</option>
                <option value="cyclone">Cyclone / Gale Wind</option>
                <option value="fire">Wildfire / Structural Fire</option>
                <option value="earthquake">Earthquake Tremor</option>
                <option value="landslide">Landslide / Rockfall</option>
              </select>
            </div>

            {/* Severity Level */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Severity Level *
              </label>
              <select
                aria-label="Severity Level"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white font-bold"
              >
                <option value="critical">CRITICAL (Red Alert - Immediate Danger)</option>
                <option value="high">HIGH (Orange Alert - Severe Threat)</option>
                <option value="medium">MEDIUM (Yellow Alert - Be Aware)</option>
                <option value="low">LOW (Green / Advisory)</option>
              </select>
            </div>
          </div>

          {/* Issuer Agency */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              Issuing Agency / Control Room *
            </label>
            <input
              type="text"
              required
              value={issuer}
              onChange={(e) => setIssuer(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white font-medium"
            />
          </div>

          {/* Geographic Targeting (District) */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              Targeted District Jurisdiction *
            </label>
            <select
              aria-label="Targeted District Jurisdiction"
              value={selectedDistrictId}
              onChange={(e) => setSelectedDistrictId(parseInt(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white font-bold"
            >
              {districts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} (District ID #{d.id})
                </option>
              ))}
            </select>
            <span className="text-[11px] text-slate-500 block">
              Backend strictly enforces officer assignment (Attempting to alert outside jurisdiction results in HTTP 403).
            </span>
          </div>

          {/* Validity Times */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Valid From *
              </label>
              <input
                type="datetime-local"
                value={validFrom}
                onChange={(e) => setValidFrom(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Valid Until *
              </label>
              <input
                type="datetime-local"
                value={validTo}
                onChange={(e) => setValidTo(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white"
              />
            </div>
          </div>

          {/* Description & Advisory Instructions */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              Advisory Instructions & Safety Protocol *
            </label>
            <textarea
              rows={4}
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Evacuate ground floor basements. Move to designated high school shelters. Do not enter moving floodwaters."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-orange-500 leading-relaxed"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSubmitAlert(false)}
              className="flex-1 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-bold py-2.5 rounded-lg text-xs transition shadow-md flex items-center justify-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{submitting ? "Publishing..." : "Publish Bulletin Immediately"}</span>
            </button>

            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSubmitAlert(true)}
              className="bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-300 font-semibold px-4 py-2.5 rounded-lg text-xs transition"
            >
              Save as Draft
            </button>
          </div>
        </div>

        {/* Live Citizen Preview Card (1 Col) */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Eye className="w-4 h-4 text-indigo-400" />
            <span>Citizen Preview</span>
          </h3>

          <div className="bg-slate-900 border-2 border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase border ${
                severity === "critical"
                  ? "bg-red-600 text-white border-red-700"
                  : severity === "high"
                  ? "bg-orange-600 text-white border-orange-700"
                  : "bg-yellow-500 text-slate-950 border-yellow-600 font-bold"
              }`}>
                {severity} ALERT
              </span>
              <span className="text-[10px] text-slate-400">
                {isOfficial ? "Govt Warning" : "Platform Exercise"}
              </span>
            </div>

            <h4 className="font-bold text-sm text-white">
              {title || "Untitled Warning Bulletin"}
            </h4>

            <p className="text-xs text-slate-300 leading-relaxed line-clamp-4">
              {description || "No advisory instructions entered yet. The instructions you compose will appear here on citizen mobile screens."}
            </p>

            <div className="bg-slate-950 p-2.5 rounded border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <p>
                <strong>Issuer:</strong> {issuer}
              </p>
              <p>
                <strong>Target District:</strong> {selectedDistObj?.name || `District #${selectedDistrictId}`}
              </p>
              <p>
                <strong>Valid:</strong> {new Date(validFrom).toLocaleTimeString()} - {new Date(validTo).toLocaleTimeString()}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
