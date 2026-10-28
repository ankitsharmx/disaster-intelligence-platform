"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Filter,
  Calendar,
  Building2,
  ArrowRight,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";
import { Alert } from "@/types";

export default function AlertsPage() {
  const { selectedDistrict, language } = useApp();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [_error, setError] = useState<string | null>(null);

  // Filters
  const [selectedHazard, setSelectedHazard] = useState<string>("all");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [activeAlertModal, setActiveAlertModal] = useState<Alert | null>(null);

  useEffect(() => {
    async function fetchAlerts() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getActiveAlerts(selectedDistrict?.id);
        setAlerts(data);
      } catch (err: any) {
        setError(err.message || "Failed to load active disaster alerts.");
      } finally {
        setLoading(false);
      }
    }
    fetchAlerts();
  }, [selectedDistrict]);

  const filteredAlerts = alerts.filter((alert) => {
    const matchHazard =
      selectedHazard === "all" ||
      alert.type.toLowerCase().includes(selectedHazard.toLowerCase());
    const matchSeverity =
      selectedSeverity === "all" ||
      alert.severity.toLowerCase() === selectedSeverity.toLowerCase();
    return matchHazard && matchSeverity;
  });

  const getSeverityStyle = (sev: string) => {
    switch (sev.toLowerCase()) {
      case "critical":
        return "bg-red-600 text-white border-red-700";
      case "high":
        return "bg-orange-600 text-white border-orange-700";
      case "medium":
        return "bg-yellow-500 text-slate-950 border-yellow-600 font-bold";
      default:
        return "bg-emerald-600 text-white border-emerald-700";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2.5">
            <AlertTriangle className="w-6 h-6 text-orange-500" />
            <span>{language === "en" ? "Active Disaster Alerts" : "सक्रिय आपदा चेतावनियाँ"}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {language === "en"
              ? "Official sourced bulletins from IMD, NDMA, and verified municipal disaster authorities."
              : "मौसम विभाग (IMD), एनडीएमए और नगर निगम नियंत्रण कक्ष से जारी आधिकारिक चेतावनियाँ।"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-lg text-slate-300">
            {language === "en" ? "District" : "जिला"}:{" "}
            <strong className="text-white">{selectedDistrict ? selectedDistrict.name : "All Districts"}</strong>
          </span>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
            <Filter className="w-4 h-4 text-orange-400" />
            <span>{language === "en" ? "Filter by" : "फ़िल्टर"}:</span>
          </div>

          {/* Hazard Type filter */}
          <select
            aria-label="Filter by Hazard Type"
            value={selectedHazard}
            onChange={(e) => setSelectedHazard(e.target.value)}
            className="bg-slate-950 text-xs text-slate-200 border border-slate-800 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-orange-500"
          >
            <option value="all">{language === "en" ? "All Hazard Types" : "सभी आपदा प्रकार"}</option>
            <option value="flood">{language === "en" ? "Floods & Rain" : "बाढ़ एवं वर्षा"}</option>
            <option value="earthquake">{language === "en" ? "Earthquake" : "भूकंप"}</option>
            <option value="fire">{language === "en" ? "Wildfire / Fire" : "आग / जंगल की आग"}</option>
            <option value="cyclone">{language === "en" ? "Cyclone / Storm" : "चक्रवात / आंधी"}</option>
          </select>

          {/* Severity filter */}
          <select
            aria-label="Filter by Severity"
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-slate-950 text-xs text-slate-200 border border-slate-800 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-orange-500"
          >
            <option value="all">{language === "en" ? "All Severities" : "सभी गंभीरता स्तर"}</option>
            <option value="critical">{language === "en" ? "Critical (Red Alert)" : "अति गंभीर (रेड अलर्ट)"}</option>
            <option value="high">{language === "en" ? "High (Orange Alert)" : "उच्च (ऑरेंज अलर्ट)"}</option>
            <option value="medium">{language === "en" ? "Medium (Yellow Alert)" : "मध्यम (येलो अलर्ट)"}</option>
            <option value="low">{language === "en" ? "Low (Advisory)" : "सामान्य (सलाह)"}</option>
          </select>
        </div>

        <div className="text-xs text-slate-400">
          <span>{filteredAlerts.length} {language === "en" ? "Active alerts listed" : "चेतावनियाँ उपलब्ध"}</span>
        </div>
      </div>

      {/* Alert Feed List */}
      {loading ? (
        <div className="text-center py-16 space-y-2">
          <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-400">{language === "en" ? "Retrieving active bulletins..." : "चेतावनियाँ लोड हो रही हैं..."}</p>
        </div>
      ) : filteredAlerts.length > 0 ? (
        <div className="space-y-4">
          {filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`bg-slate-900 border rounded-xl p-5 shadow-md hover:border-slate-700 transition ${
                alert.severity.toLowerCase() === "critical"
                  ? "border-red-600/60 bg-gradient-to-r from-red-950/40 to-slate-900"
                  : alert.severity.toLowerCase() === "high"
                  ? "border-orange-600/50"
                  : "border-slate-800"
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-2 max-w-3xl">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded uppercase tracking-wider border ${getSeverityStyle(alert.severity)}`}>
                      {alert.severity}
                    </span>
                    <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700 uppercase">
                      {alert.type}
                    </span>
                    <span className="text-xs text-slate-400 flex items-center gap-1">
                      <Building2 className="w-3.5 h-3.5" />
                      <span>{alert.issuer}</span>
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-white tracking-tight">
                    {alert.title}
                  </h3>

                  <p className="text-sm text-slate-300 leading-relaxed line-clamp-2">
                    {alert.description}
                  </p>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      <span>{language === "en" ? "Valid" : "मान्य"}: {new Date(alert.valid_from).toLocaleDateString()} &mdash; {new Date(alert.valid_to).toLocaleDateString()}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>{language === "en" ? "Expires at" : "समाप्ति"}: {new Date(alert.valid_to).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row md:flex-col gap-2 shrink-0">
                  <button
                    onClick={() => setActiveAlertModal(alert)}
                    className="bg-orange-600 hover:bg-orange-500 text-white font-bold px-4 py-2 rounded-lg text-xs transition"
                  >
                    {language === "en" ? "View Full Instructions" : "पूर्ण निर्देश देखें"}
                  </button>
                  <Link
                    href={`/map?district_id=${selectedDistrict?.id}`}
                    className="bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 px-4 py-2 rounded-lg text-xs font-semibold text-center transition flex items-center justify-center gap-1"
                  >
                    <span>{language === "en" ? "Map Zone" : "मानचित्र पर देखें"}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center space-y-3">
          <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
          <h3 className="font-bold text-base text-white">
            {language === "en" ? "No Active Alerts Matching Criteria" : "कोई सक्रिय चेतावनी नहीं मिली"}
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            {language === "en"
              ? "All baseline monitored parameters are within safe operational limits. You can reset filters to view all bulletins."
              : "वर्तमान में सभी मानक सुरक्षित सीमा के भीतर हैं। आप फ़िल्टर बदलकर अन्य सूचनाएं देख सकते हैं।"}
          </p>
          <button
            onClick={() => {
              setSelectedHazard("all");
              setSelectedSeverity("all");
            }}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 font-semibold"
          >
            {language === "en" ? "Clear Filters" : "फ़िल्टर हटाएं"}
          </button>
        </div>
      )}

      {/* Alert Full Detail Modal */}
      {activeAlertModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className={`text-xs font-bold px-2.5 py-0.5 rounded uppercase tracking-wider border ${getSeverityStyle(activeAlertModal.severity)}`}>
                {activeAlertModal.severity} ALERT
              </span>
              <button
                onClick={() => setActiveAlertModal(null)}
                className="text-slate-400 hover:text-white font-bold text-sm"
              >
                ✕ Close
              </button>
            </div>

            <h3 className="text-xl font-bold text-white">
              {activeAlertModal.title}
            </h3>

            <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs space-y-1.5 text-slate-300">
              <p><strong>Issuing Authority:</strong> {activeAlertModal.issuer}</p>
              <p><strong>Hazard Category:</strong> {activeAlertModal.type.toUpperCase()}</p>
              <p><strong>Issued At:</strong> {new Date(activeAlertModal.created_at).toLocaleString()}</p>
              <p><strong>Validity Window:</strong> {new Date(activeAlertModal.valid_from).toLocaleString()} to {new Date(activeAlertModal.valid_to).toLocaleString()}</p>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-orange-400">
                Official Instructions & Advisory:
              </h4>
              <p className="text-sm text-slate-200 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                {activeAlertModal.description}
              </p>
            </div>

            <div className="flex gap-2 pt-2">
              <Link
                href={`/map?district_id=${selectedDistrict?.id}`}
                onClick={() => setActiveAlertModal(null)}
                className="flex-1 bg-orange-600 hover:bg-orange-500 text-white font-bold py-2 rounded-lg text-sm text-center"
              >
                Inspect Hazard Zone on Map
              </Link>
              <button
                onClick={() => setActiveAlertModal(null)}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold px-4 py-2 rounded-lg text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
