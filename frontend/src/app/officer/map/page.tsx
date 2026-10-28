"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  Map as MapIcon,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
  Building2,
  PhoneCall,
  X,
  Layers,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";

const LeafletMap = dynamic(() => import("@/components/Map/LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[550px] bg-slate-900 flex items-center justify-center rounded-xl border border-slate-800">
      <div className="text-center space-y-2">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-indigo-400" />
        <p className="text-xs text-slate-400">Loading Operational Layers...</p>
      </div>
    </div>
  ),
});

export default function OfficerOperationalMapPage() {
  const [layersData, setLayersData] = useState<any>({});
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [selectedFeature, setSelectedFeature] = useState<any | null>(null);

  const [visibleLayers, setVisibleLayers] = useState({
    boundaries: true,
    facilities: true,
    incidents: true,
    alerts: true,
    riskZones: true,
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [mapLayers, operationalIncidents, activeAlerts] = await Promise.all([
        api.getMapLayers(),
        api.getOperationalIncidents(statusFilter),
        api.getActiveAlerts(),
      ]);

      setLayersData({
        boundaries: mapLayers.boundaries,
        facilities: mapLayers.facilities,
        incidents: operationalIncidents, // Officer sees ALL incident statuses!
        alerts: activeAlerts,
      });
    } catch (err) {
      console.error("Failed to load officer map data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    const handleWsEvent = (_e: any) => {
      loadData();
    };
    window.addEventListener("officer_ws_message", handleWsEvent);
    return () => window.removeEventListener("officer_ws_message", handleWsEvent);
  }, [statusFilter]);

  const toggleLayer = (key: keyof typeof visibleLayers) => {
    setVisibleLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-4">
      {/* Control Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <MapIcon className="w-5 h-5 text-indigo-400" />
            <span>Officer Operational GIS Command</span>
          </h2>
          <p className="text-xs text-slate-400">
            Internal full-fidelity map displaying all triage stages, restricted reporter IDs, and facilities
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status Filter */}
          <select
            aria-label="Filter Map Incidents by Status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 text-xs text-slate-200 border border-slate-800 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-semibold"
          >
            <option value="all">All Incidents (Full Pipeline)</option>
            <option value="submitted">Submitted Only (Unverified)</option>
            <option value="under_review">Under Review</option>
            <option value="verified">Verified Only (Public Map)</option>
            <option value="rejected">Rejected Only</option>
          </select>

          <button
            onClick={loadData}
            className="text-xs bg-slate-950 hover:bg-slate-850 text-slate-300 border border-slate-800 px-3 py-1.5 rounded-lg flex items-center gap-1 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Sync</span>
          </button>
        </div>
      </div>

      {/* Map + Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Map */}
        <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden relative shadow-md h-[620px]">
          <LeafletMap
            center={[19.076, 72.877]}
            zoom={11}
            layersData={layersData}
            visibleLayers={visibleLayers}
            onSelectFeature={(feat) => setSelectedFeature(feat)}
          />

          {/* Officer Layer Controls Pill */}
          <div className="absolute top-4 right-4 bg-slate-900/90 backdrop-blur-sm border border-slate-800 p-2 rounded-lg text-[11px] flex items-center gap-1.5 z-[400] shadow-lg">
            <button
              onClick={() => toggleLayer("facilities")}
              className={`px-2 py-1 rounded font-semibold transition ${
                visibleLayers.facilities ? "bg-blue-900/80 text-blue-300" : "text-slate-400"
              }`}
            >
              Facilities
            </button>
            <button
              onClick={() => toggleLayer("incidents")}
              className={`px-2 py-1 rounded font-semibold transition ${
                visibleLayers.incidents ? "bg-amber-900/80 text-amber-300" : "text-slate-400"
              }`}
            >
              Incidents
            </button>
            <button
              onClick={() => toggleLayer("alerts")}
              className={`px-2 py-1 rounded font-semibold transition ${
                visibleLayers.alerts ? "bg-red-900/80 text-red-300" : "text-slate-400"
              }`}
            >
              Alerts
            </button>
          </div>
        </div>

        {/* Selected Incident / Facility Inspector */}
        <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-md">
          {selectedFeature ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-400">
                  {selectedFeature.type === "facility"
                    ? `${selectedFeature.properties.category} Command Data`
                    : "Incident Details"}
                </span>
                <button
                  onClick={() => setSelectedFeature(null)}
                  className="text-slate-400 hover:text-white text-xs"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {selectedFeature.type === "facility" && (
                <div className="space-y-3">
                  <h4 className="font-bold text-base text-white">
                    {selectedFeature.properties.name}
                  </h4>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5 text-slate-300">
                    <p><strong>Category:</strong> {selectedFeature.properties.category.toUpperCase()}</p>
                    {selectedFeature.properties.capacity && (
                      <p><strong>Bed Capacity:</strong> {selectedFeature.properties.capacity}</p>
                    )}
                    {selectedFeature.coordinates && (
                      <p><strong>GPS:</strong> {selectedFeature.coordinates[0].toFixed(5)}, {selectedFeature.coordinates[1].toFixed(5)}</p>
                    )}
                  </div>
                  {selectedFeature.properties.contact_number && (
                    <a
                      href={`tel:${selectedFeature.properties.contact_number}`}
                      className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 rounded text-xs flex items-center justify-center gap-1.5"
                    >
                      <PhoneCall className="w-3.5 h-3.5" />
                      <span>Direct Contact: {selectedFeature.properties.contact_number}</span>
                    </a>
                  )}
                </div>
              )}

              {selectedFeature.type === "incident" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-white">
                      Report #{selectedFeature.properties.id}
                    </span>
                    <span className="text-[10px] bg-slate-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded uppercase font-bold">
                      {selectedFeature.properties.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 bg-slate-950 p-3 rounded-lg border border-slate-800 leading-relaxed">
                    {selectedFeature.properties.description}
                  </p>

                  <div className="text-[11px] text-slate-400 bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1">
                    <p><strong>Hazard Type:</strong> {selectedFeature.properties.type.toUpperCase()}</p>
                    <p><strong>AI Confidence Score:</strong> {selectedFeature.properties.confidence_score ? (selectedFeature.properties.confidence_score * 100).toFixed(0) + "%" : "Pending"}</p>
                    <p><strong>Assigned Officer:</strong> {selectedFeature.properties.assigned_officer_id ? `ID #${selectedFeature.properties.assigned_officer_id}` : "Unassigned"}</p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-20 text-center space-y-2">
              <Layers className="w-8 h-8 text-slate-600 mx-auto" />
              <h4 className="font-bold text-xs text-slate-300">Operational Feature Inspector</h4>
              <p className="text-[11px] text-slate-500 max-w-[200px] mx-auto">
                Select any incident or emergency facility on the map to inspect restricted triage data.
              </p>
            </div>
          )}

          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-[11px] text-slate-500">
            <strong>Restricted Access:</strong> All field data displayed here is strictly privileged and audited for command operations.
          </div>
        </div>
      </div>
    </div>
  );
}
