"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  Layers,
  MapPin,
  CheckCircle2,
  PhoneCall,
  X,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";

// Dynamically import LeafletMap with SSR disabled to prevent window is not defined errors
const LeafletMap = dynamic(() => import("@/components/Map/LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[550px] bg-slate-900 flex items-center justify-center rounded-xl border border-slate-800">
      <div className="text-center space-y-2">
        <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs text-slate-400">Loading Geospatial Layers & Tiles...</p>
      </div>
    </div>
  ),
});

export default function MapPage() {
  const { selectedDistrict, language } = useApp();
  const [layersData, setLayersData] = useState<{
    boundaries?: any;
    facilities?: any;
    incidents?: any;
    alerts?: any[];
  }>({});
  const [_loading, setLoading] = useState(true);
  const [selectedFeature, setSelectedFeature] = useState<any | null>(null);

  // Independent Layer Toggles
  const [visibleLayers, setVisibleLayers] = useState({
    boundaries: true,
    facilities: true,
    incidents: true,
    alerts: true,
    riskZones: true,
  });

  useEffect(() => {
    if (!selectedDistrict) return;
    const currentDistrict = selectedDistrict;

    let isMounted = true;
    async function loadMapData() {
      setLoading(true);
      try {
        const [mapLayers, activeAlerts] = await Promise.all([
          api.getMapLayers(currentDistrict.id),
          api.getActiveAlerts(currentDistrict.id),
        ]);

        if (!isMounted) return;
        setLayersData({
          boundaries: mapLayers.boundaries,
          facilities: mapLayers.facilities,
          incidents: mapLayers.incidents,
          alerts: activeAlerts,
        });
      } catch (err) {
        console.error("Failed to load map geospatial layers:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadMapData();
    return () => {
      isMounted = false;
    };
  }, [selectedDistrict]);

  const mapCenter: [number, number] = selectedDistrict
    ? [selectedDistrict.center_lat, selectedDistrict.center_lon]
    : [18.96, 72.83];

  const toggleLayer = (layerKey: keyof typeof visibleLayers) => {
    setVisibleLayers((prev) => ({
      ...prev,
      [layerKey]: !prev[layerKey],
    }));
  };

  return (
    <div className="space-y-4">
      {/* Map Control Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-orange-500" />
            <span>{language === "en" ? "Interactive Disaster Map" : "आपदा स्थानिक मानचित्र"}</span>
          </h1>
          <p className="text-xs text-slate-400">
            {language === "en"
              ? `Displaying verified emergency layers for ${selectedDistrict?.name || "selected area"}`
              : `${selectedDistrict?.name || "चुने हुए क्षेत्र"} के लिए सत्यापित आपदा परतें`}
          </p>
        </div>

        {/* Independent Layer Toggle Checkboxes */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => toggleLayer("boundaries")}
            className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition ${
              visibleLayers.boundaries
                ? "bg-orange-950/80 border-orange-700 text-orange-300"
                : "bg-slate-950 border-slate-800 text-slate-400 opacity-60"
            }`}
          >
            {language === "en" ? "District Boundary" : "जिला सीमा"}
          </button>

          <button
            onClick={() => toggleLayer("facilities")}
            className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition ${
              visibleLayers.facilities
                ? "bg-blue-950/80 border-blue-700 text-blue-300"
                : "bg-slate-950 border-slate-800 text-slate-400 opacity-60"
            }`}
          >
            {language === "en" ? "Shelters & Hospitals" : "शिविर व अस्पताल"}
          </button>

          <button
            onClick={() => toggleLayer("incidents")}
            className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition ${
              visibleLayers.incidents
                ? "bg-amber-950/80 border-amber-700 text-amber-300"
                : "bg-slate-950 border-slate-800 text-slate-400 opacity-60"
            }`}
          >
            {language === "en" ? "Verified Incidents" : "सत्यापित घटनाएं"}
          </button>

          <button
            onClick={() => toggleLayer("alerts")}
            className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition ${
              visibleLayers.alerts
                ? "bg-red-950/80 border-red-700 text-red-300"
                : "bg-slate-950 border-slate-800 text-slate-400 opacity-60"
            }`}
          >
            {language === "en" ? "Official Alerts" : "आधिकारिक अलर्ट"}
          </button>

          <button
            onClick={() => toggleLayer("riskZones")}
            className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition ${
              visibleLayers.riskZones
                ? "bg-sky-950/80 border-sky-700 text-sky-300"
                : "bg-slate-950 border-slate-800 text-slate-400 opacity-60"
            }`}
          >
            {language === "en" ? "Indicative Risk Zones" : "अनुमानित जलभराव"}
          </button>
        </div>
      </div>

      {/* Map + Detail Panel Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Main Leaflet Map Container */}
        <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden relative shadow-md h-[600px]">
          <LeafletMap
            center={mapCenter}
            zoom={12}
            layersData={layersData}
            visibleLayers={visibleLayers}
            onSelectFeature={(feat) => setSelectedFeature(feat)}
          />

          {/* Map Legend (Floating Overlay) */}
          <div className="absolute bottom-6 left-4 bg-slate-900/90 backdrop-blur-sm border border-slate-800 p-3 rounded-lg text-[11px] space-y-1.5 shadow-lg z-[400]">
            <span className="font-bold text-slate-300 block border-b border-slate-800 pb-1">
              {language === "en" ? "Map Legend" : "मानचित्र संकेत"}
            </span>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-600 border border-white inline-block" />
              <span className="text-slate-300">{language === "en" ? "Hospital (H)" : "अस्पताल"}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-blue-600 border border-white inline-block" />
              <span className="text-slate-300">{language === "en" ? "Relief Shelter (S)" : "राहत शिविर"}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-amber-500 border border-white inline-block text-[8px] text-center text-white">⚠️</span>
              <span className="text-slate-300">{language === "en" ? "Verified Citizen Report" : "सत्यापित घटना"}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-600/30 border border-red-500 inline-block" />
              <span className="text-slate-300">{language === "en" ? "Active Warning Zone" : "चेतावनी क्षेत्र"}</span>
            </div>
          </div>
        </div>

        {/* Selected Feature Detail Panel */}
        <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-md">
          {selectedFeature ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-orange-400">
                  {selectedFeature.type === "facility"
                    ? `${selectedFeature.properties.category} Details`
                    : selectedFeature.type === "incident"
                    ? "Verified Field Incident"
                    : "Feature Details"}
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
                  <h3 className="font-bold text-base text-white">
                    {selectedFeature.properties.name}
                  </h3>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5 text-slate-300">
                    <p>
                      <strong>Category:</strong> {selectedFeature.properties.category.toUpperCase()}
                    </p>
                    {selectedFeature.properties.capacity && (
                      <p>
                        <strong>Bed Capacity:</strong> {selectedFeature.properties.capacity}
                      </p>
                    )}
                    {selectedFeature.coordinates && (
                      <p>
                        <strong>GPS Coordinates:</strong> {selectedFeature.coordinates[0].toFixed(4)}, {selectedFeature.coordinates[1].toFixed(4)}
                      </p>
                    )}
                  </div>

                  {selectedFeature.properties.contact_number && (
                    <a
                      href={`tel:${selectedFeature.properties.contact_number}`}
                      className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 rounded-lg text-xs flex items-center justify-center gap-2 transition"
                    >
                      <PhoneCall className="w-3.5 h-3.5" />
                      <span>Call {selectedFeature.properties.contact_number}</span>
                    </a>
                  )}
                </div>
              )}

              {selectedFeature.type === "incident" && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs bg-amber-500/20 text-amber-300 border border-amber-600 px-2 py-0.5 rounded font-bold uppercase">
                      {selectedFeature.properties.type}
                    </span>
                    <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Verified
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
                    {selectedFeature.properties.description}
                  </p>

                  <div className="text-[11px] text-slate-400 space-y-1">
                    <p>
                      <strong>Confidence Score:</strong>{" "}
                      {selectedFeature.properties.confidence_score
                        ? (selectedFeature.properties.confidence_score * 100).toFixed(0) + "%"
                        : "High"}
                    </p>
                    <p>
                      <strong>Verified On:</strong>{" "}
                      {selectedFeature.properties.created_at
                        ? new Date(selectedFeature.properties.created_at).toLocaleString()
                        : "Recent"}
                    </p>
                  </div>
                </div>
              )}

              {selectedFeature.type === "alert" && (
                <div className="space-y-3">
                  <h3 className="font-bold text-base text-white">
                    {selectedFeature.properties.title}
                  </h3>
                  <p className="text-xs text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-800">
                    {selectedFeature.properties.description}
                  </p>
                  <p className="text-xs text-slate-400">
                    <strong>Authority:</strong> {selectedFeature.properties.issuer}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="py-16 text-center space-y-2">
              <MapPin className="w-8 h-8 text-slate-600 mx-auto" />
              <h4 className="font-bold text-xs text-slate-300">
                {language === "en" ? "Select a Marker on Map" : "मानचित्र पर कोई स्थान चुनें"}
              </h4>
              <p className="text-[11px] text-slate-500 max-w-[200px] mx-auto">
                {language === "en"
                  ? "Click on any hospital, relief shelter, or verified incident to view emergency contact details."
                  : "अस्पताल, राहत शिविर या घटना की जानकारी और संपर्क नंबर देखने के लिए मार्कर पर क्लिक करें।"}
              </p>
            </div>
          )}

          <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <p className="font-semibold text-slate-300">
              {language === "en" ? "Public Safety Policy:" : "सार्वजनिक सुरक्षा नीति:"}
            </p>
            <p>
              {language === "en"
                ? "Only verified reports are mapped to prevent panic and disinformation."
                : "अफवाहों और गलत जानकारी को रोकने के लिए केवल सत्यापित घटनाएं ही प्रदर्शित की जाती हैं।"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
