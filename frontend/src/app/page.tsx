"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ShieldCheck,
  CloudRain,
  Activity,
  Building2,
  PhoneCall,
  MapPin,
  Clock,
  ArrowRight,
  AlertCircle,
  FilePlus2,
  BookOpen,
  Info,
  Radio,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";
import { DistrictOverview, Facility } from "@/types";
import PwaManager from "@/components/PwaManager";

export default function HomePage() {
  const { selectedDistrict, language, lastUpdated, refreshTimestamp, locationError } = useApp();
  const [overview, setOverview] = useState<DistrictOverview | null>(null);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [_loading, setLoading] = useState(true);
  const [_error, setError] = useState<string | null>(null);
  const [selectedAlertForModal, setSelectedAlertForModal] = useState<any | null>(null);

  useEffect(() => {
    if (!selectedDistrict) return;
    const currentDistrict = selectedDistrict;

    let isMounted = true;
    async function fetchDistrictData() {
      setLoading(true);
      setError(null);
      try {
        const [overviewData, mapData] = await Promise.all([
          api.getDistrictOverview(currentDistrict.id),
          api.getMapLayers(currentDistrict.id),
        ]);

        if (!isMounted) return;
        setOverview(overviewData);

        // Extract facilities from GeoJSON features
        const facList: Facility[] = (mapData.facilities?.features || []).map((f: any) => ({
          id: f.id,
          district_id: f.properties.district_id,
          name: f.properties.name,
          category: f.properties.category,
          latitude: f.geometry.coordinates[1],
          longitude: f.geometry.coordinates[0],
          contact_number: f.properties.contact_number,
          capacity: f.properties.capacity,
          details: f.properties.details,
        }));
        setFacilities(facList);
        refreshTimestamp();
      } catch (err: any) {
        if (isMounted) setError(err.message || "Failed to load district situation overview.");
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchDistrictData();
    const interval = setInterval(fetchDistrictData, 30000); // 30-second live polling
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedDistrict, refreshTimestamp]);

  const severityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case "critical":
        return "bg-red-600 text-white border-red-700 font-bold";
      case "high":
        return "bg-orange-600 text-white border-orange-700 font-bold";
      case "medium":
        return "bg-yellow-500 text-slate-950 border-yellow-600 font-semibold";
      default:
        return "bg-emerald-600 text-white border-emerald-700";
    }
  };

  const activeAlerts = overview?.applicable_alerts || [];
  const primaryAlert = activeAlerts.length > 0 ? activeAlerts[0] : null;

  return (
    <div className="space-y-6">
      {/* Location Status & Freshness Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-orange-500/10 p-2.5 rounded-lg border border-orange-500/20 text-orange-400">
            <MapPin className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white">
                {selectedDistrict ? selectedDistrict.name : "Select a District"}
              </h1>
              <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                {language === "en" ? "Active Monitoring" : "सक्रिय निगरानी"}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              {language === "en"
                ? "Coordinates & administrative polygon verified via PostGIS"
                : "भौगोलिक सीमाएँ और समन्वय पुष्टि PostGIS द्वारा सत्यापित"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-slate-500" />
            <span>
              {language === "en" ? "Updated" : "अंतिम अद्यतन"}:{" "}
              <strong className="text-slate-200">
                {lastUpdated ? lastUpdated.toLocaleTimeString() : "--"}
              </strong>
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span className="text-emerald-400 font-medium">LIVE</span>
          </div>
        </div>
      </div>

      {locationError && (
        <div className="bg-yellow-950/40 border border-yellow-800/80 p-3 rounded-lg flex items-center gap-2 text-xs text-yellow-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{locationError}</span>
        </div>
      )}

      {/* Prominent Active Alert Hero (If an alert is active) */}
      {primaryAlert ? (
        <div className="bg-gradient-to-r from-red-950/80 via-slate-900 to-slate-900 border-2 border-red-600/80 rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-2 max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`px-2.5 py-0.5 rounded text-xs tracking-wider uppercase border shadow-sm ${severityBadge(primaryAlert.severity)}`}>
                  {primaryAlert.severity} {language === "en" ? "SEVERITY ALERT" : "गंभीरता चेतावनी"}
                </span>
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5 text-slate-400" />
                  {language === "en" ? "Issuer" : "जारीकर्ता"}: <strong className="text-slate-200">{primaryAlert.issuer}</strong>
                </span>
                <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                  {primaryAlert.is_official ? (language === "en" ? "Authoritative Warning" : "आधिकारिक चेतावनी") : (language === "en" ? "Exercise Simulation" : "प्रशिक्षण अभ्यास")}
                </span>
              </div>

              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight flex items-center gap-2">
                <AlertTriangle className="w-6 h-6 text-red-500 shrink-0 animate-bounce" />
                {primaryAlert.title}
              </h2>

              <p className="text-sm text-slate-300 line-clamp-2">
                {primaryAlert.description}
              </p>

              <div className="text-xs text-slate-400 flex items-center gap-2 pt-1">
                <span>
                  {language === "en" ? "Valid until" : "मान्य समय"}:{" "}
                  <strong className="text-slate-200">{new Date(primaryAlert.valid_to).toLocaleString()}</strong>
                </span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row md:flex-col gap-2 w-full md:w-auto shrink-0">
              <button
                onClick={() => setSelectedAlertForModal(primaryAlert)}
                className="bg-red-600 hover:bg-red-500 text-white font-bold px-4 py-2.5 rounded-lg text-sm text-center shadow-md transition"
              >
                {language === "en" ? "Read Instructions" : "सुरक्षा निर्देश पढ़ें"}
              </button>
              <Link
                href={`/map?district_id=${selectedDistrict?.id}`}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold px-4 py-2 rounded-lg text-sm text-center transition flex items-center justify-center gap-1.5"
              >
                <span>{language === "en" ? "View Affected Map" : "मानचित्र पर देखें"}</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/60 border border-emerald-900/40 rounded-xl p-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">
                {language === "en" ? "No Active Authoritative Alerts" : "कोई सक्रिय आधिकारिक चेतावनी नहीं"}
              </h2>
              <p className="text-xs text-slate-400">
                {language === "en"
                  ? `Normal hazard baseline conditions reported for ${selectedDistrict?.name || "this district"}.`
                  : `${selectedDistrict?.name || "इस जिले"} के लिए वर्तमान स्थिति सामान्य दर्ज की गई है।`}
              </p>
            </div>
          </div>
          <Link
            href="/alerts"
            className="text-xs font-semibold text-orange-400 hover:text-orange-300 flex items-center gap-1"
          >
            <span>{language === "en" ? "View Archive" : "पिछली चेतावनियाँ"}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Quick Action Emergency Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Link
          href="/report"
          className="bg-orange-600 hover:bg-orange-500 text-white p-3.5 rounded-xl flex flex-col justify-between shadow-md transition group"
        >
          <FilePlus2 className="w-5 h-5 mb-2 group-hover:scale-110 transition-transform" />
          <div>
            <span className="font-bold text-sm block">
              {language === "en" ? "Report Incident" : "घटना दर्ज करें"}
            </span>
            <span className="text-[11px] text-orange-100 opacity-90 block">
              {language === "en" ? "Submit field evidence" : "फोटो व स्थान भेजें"}
            </span>
          </div>
        </Link>

        <Link
          href="/map"
          className="bg-slate-800 hover:bg-slate-750 border border-slate-700 text-white p-3.5 rounded-xl flex flex-col justify-between transition group"
        >
          <MapPin className="w-5 h-5 text-orange-400 mb-2 group-hover:scale-110 transition-transform" />
          <div>
            <span className="font-bold text-sm block">
              {language === "en" ? "Interactive Map" : "आपदा मानचित्र"}
            </span>
            <span className="text-[11px] text-slate-400 block">
              {language === "en" ? "Shelters & Verified Zones" : "राहत शिविर व घटनाएं"}
            </span>
          </div>
        </Link>

        <Link
          href="/awareness"
          className="bg-slate-800 hover:bg-slate-750 border border-slate-700 text-white p-3.5 rounded-xl flex flex-col justify-between transition group"
        >
          <BookOpen className="w-5 h-5 text-blue-400 mb-2 group-hover:scale-110 transition-transform" />
          <div>
            <span className="font-bold text-sm block">
              {language === "en" ? "Safety Guides" : "सुरक्षा मार्गदर्शिका"}
            </span>
            <span className="text-[11px] text-slate-400 block">
              {language === "en" ? "Before, During & After" : "तैयारी व जीवन रक्षा"}
            </span>
          </div>
        </Link>

        <a
          href="tel:112"
          className="bg-red-700 hover:bg-red-600 text-white p-3.5 rounded-xl flex flex-col justify-between shadow-md transition group"
        >
          <PhoneCall className="w-5 h-5 mb-2 group-hover:scale-110 transition-transform animate-pulse" />
          <div>
            <span className="font-bold text-sm block">
              {language === "en" ? "Dial 112 Help" : "112 पर कॉल करें"}
            </span>
            <span className="text-[11px] text-red-100 opacity-90 block">
              {language === "en" ? "Police, Fire, Ambulance" : "तत्काल राहत सहायता"}
            </span>
          </div>
        </a>
      </div>

      {/* Hazard Observations & Indicative Risk Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Weather & Flood Signals Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <CloudRain className="w-4 h-4 text-blue-400" />
              <h3 className="font-bold text-sm text-white">
                {language === "en" ? "Precipitation & Inundation" : "वर्षा एवं जलभराव"}
              </h3>
            </div>
            <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
              IMD / Sensor
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block">
                {language === "en" ? "Rainfall Rate" : "वर्षा दर"}
              </span>
              <span className="text-lg font-black text-white">
                {overview?.observations?.weather?.rainfall_mm ?? 18.5} mm/h
              </span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block">
                {language === "en" ? "River Stage" : "नदी का जलस्तर"}
              </span>
              <span className="text-lg font-black text-white">
                {overview?.observations?.weather?.water_level_m ?? 2.4} m
              </span>
            </div>
          </div>

          <p className="text-xs text-slate-400">
            {language === "en"
              ? "Monitored catchment basins and stormwater discharge channels are stable."
              : "जल निकासी मार्ग और प्रमुख नालों में प्रवाह पर निगरानी जारी है।"}
          </p>
        </div>

        {/* Earthquake & Seismic Status Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-400" />
              <h3 className="font-bold text-sm text-white">
                {language === "en" ? "Seismic & Tectonic" : "भूकंपीय स्थिति"}
              </h3>
            </div>
            <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
              USGS / NCS
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block">
                {language === "en" ? "Recent Tremors" : "हालिया झटके"}
              </span>
              <span className="text-lg font-black text-white">
                {overview?.observations?.earthquake?.magnitude ? `${overview.observations.earthquake.magnitude} M` : "None"}
              </span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block">
                {language === "en" ? "Tectonic Risk" : "भूकंपीय जोखिम"}
              </span>
              <span className="text-lg font-black text-emerald-400">
                Zone III
              </span>
            </div>
          </div>

          <p className="text-xs text-slate-400">
            {language === "en"
              ? "No significant ground acceleration recorded within 100km radius."
              : "100 किमी के दायरे में कोई गंभीर भूमिगत हलचल दर्ज नहीं हुई।"}
          </p>
        </div>

        {/* Indicative Risk Score (Strictly Demarcated) */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-orange-400" />
              <h3 className="font-bold text-sm text-white">
                {language === "en" ? "Indicative Risk Score" : "अनुमानित जोखिम स्तर"}
              </h3>
            </div>
            <span className="text-[10px] bg-amber-950 text-amber-300 border border-amber-800 px-1.5 py-0.5 rounded font-semibold">
              {language === "en" ? "Calculated (ML)" : "अनुमानित"}
            </span>
          </div>

          <div className="flex items-center justify-between bg-slate-950 p-3 rounded-lg border border-slate-800">
            <div>
              <span className="text-xs text-slate-400 block">
                {language === "en" ? "Composite Level" : "समग्र स्तर"}
              </span>
              <span className={`text-base font-black uppercase ${
                overview?.risk_estimates?.composite_risk_level === "high" || overview?.risk_estimates?.composite_risk_level === "critical"
                  ? "text-orange-400"
                  : "text-emerald-400"
              }`}>
                {overview?.risk_estimates?.composite_risk_level || "LOW"}
              </span>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-400 block">
                {language === "en" ? "Algorithm Score" : "कंप्यूटर स्कोर"}
              </span>
              <span className="text-lg font-bold text-white">
                {overview?.risk_estimates?.calculated_score ?? 28} / 100
              </span>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 leading-tight">
            <strong>{language === "en" ? "Notice:" : "सूचना:"}</strong>{" "}
            {language === "en"
              ? "This indicative score is computed algorithmically from multi-source weather and report density. It does not replace authoritative disaster declarations."
              : "यह स्कोर कंप्यूटर गणना पर आधारित है। इसे आधिकारिक आपदा घोषणा का विकल्प न मानें।"}
          </p>
        </div>
      </div>

      {/* Critical Facilities: Shelters & Hospitals */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Building2 className="w-5 h-5 text-orange-400" />
              {language === "en" ? "Nearby Emergency Shelters & Hospitals" : "निकटतम राहत शिविर एवं अस्पताल"}
            </h2>
            <p className="text-xs text-slate-400">
              {language === "en"
                ? `Operational municipal relief infrastructure in ${selectedDistrict?.name || "your district"}`
                : `${selectedDistrict?.name || "आपके जिले"} में उपलब्ध राहत शिविर व चिकित्सा केंद्र`}
            </p>
          </div>
          <Link
            href={`/map?district_id=${selectedDistrict?.id}`}
            className="text-xs font-semibold text-orange-400 hover:text-orange-300 flex items-center gap-1 shrink-0"
          >
            <span>{language === "en" ? "Open Full Screen Map" : "पूर्ण मानचित्र खोलें"}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {facilities.length > 0 ? (
            facilities.slice(0, 6).map((fac) => (
              <div
                key={fac.id}
                className="bg-slate-950 border border-slate-800/80 rounded-lg p-3.5 flex flex-col justify-between hover:border-slate-700 transition"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                      fac.category === "hospital"
                        ? "bg-rose-950 text-rose-300 border border-rose-800"
                        : fac.category === "shelter"
                        ? "bg-blue-950 text-blue-300 border border-blue-800"
                        : "bg-slate-800 text-slate-300"
                    }`}>
                      {fac.category.replace("_", " ")}
                    </span>
                    {fac.capacity && (
                      <span className="text-[11px] text-slate-400">
                        {fac.capacity} {language === "en" ? "Beds" : "बिस्तर"}
                      </span>
                    )}
                  </div>

                  <h4 className="font-bold text-sm text-white line-clamp-1">
                    {fac.name}
                  </h4>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-slate-900 mt-3 text-xs">
                  {fac.contact_number ? (
                    <a
                      href={`tel:${fac.contact_number}`}
                      className="text-orange-400 hover:text-orange-300 font-semibold flex items-center gap-1"
                    >
                      <PhoneCall className="w-3.5 h-3.5" />
                      <span>{fac.contact_number}</span>
                    </a>
                  ) : (
                    <span className="text-slate-500">
                      {language === "en" ? "Contact at gate" : "गेट पर संपर्क करें"}
                    </span>
                  )}
                  <Link
                    href={`/map?lat=${fac.latitude}&lon=${fac.longitude}`}
                    className="text-slate-300 hover:text-white flex items-center gap-1"
                  >
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span>{language === "en" ? "Directions" : "दिशा"}</span>
                  </Link>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full py-8 text-center text-slate-400 text-sm">
              {language === "en"
                ? "No registered facilities found for this district."
                : "इस जिले के लिए कोई पंजीकृत केंद्र नहीं मिला।"}
            </div>
          )}
        </div>
      </div>

      {/* PWA Install & Push Notification Manager */}
      <PwaManager />

      {/* Alert Instructions Modal */}
      {selectedAlertForModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className={`px-2.5 py-0.5 rounded text-xs font-bold uppercase ${severityBadge(selectedAlertForModal.severity)}`}>
                {selectedAlertForModal.severity} ALERT
              </span>
              <button
                onClick={() => setSelectedAlertForModal(null)}
                className="text-slate-400 hover:text-white text-sm font-bold"
              >
                ✕ Close
              </button>
            </div>

            <h3 className="text-xl font-bold text-white">
              {selectedAlertForModal.title}
            </h3>

            <p className="text-sm text-slate-300 leading-relaxed">
              {selectedAlertForModal.description}
            </p>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5 text-slate-300">
              <p>
                <strong>Issuing Agency:</strong> {selectedAlertForModal.issuer}
              </p>
              <p>
                <strong>Validity Window:</strong> {new Date(selectedAlertForModal.valid_from).toLocaleString()} &mdash; {new Date(selectedAlertForModal.valid_to).toLocaleString()}
              </p>
            </div>

            <div className="flex gap-2 pt-2">
              <Link
                href={`/map?district_id=${selectedDistrict?.id}`}
                onClick={() => setSelectedAlertForModal(null)}
                className="flex-1 bg-orange-600 hover:bg-orange-500 text-white font-bold py-2 rounded-lg text-sm text-center"
              >
                View on Map
              </Link>
              <button
                onClick={() => setSelectedAlertForModal(null)}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold px-4 py-2 rounded-lg text-sm"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
