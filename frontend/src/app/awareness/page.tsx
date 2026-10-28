"use client";

import React, { useEffect, useState } from "react";
import {
  BookOpen,
  Waves,
  Activity,
  Flame,
  Wind,
  ShieldCheck,
  Building2,
  HelpCircle,
  Globe2,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";
import { AwarenessItem } from "@/types";

const HAZARD_TABS = [
  { id: "flood", label: "Floods & Rain", labelHi: "बाढ़ एवं वर्षा", icon: Waves, color: "text-blue-400" },
  { id: "earthquake", label: "Earthquake", labelHi: "भूकंप", icon: Activity, color: "text-purple-400" },
  { id: "cyclone", label: "Cyclone & Storm", labelHi: "चक्रवात व आंधी", icon: Wind, color: "text-teal-400" },
  { id: "fire", label: "Fire Emergencies", labelHi: "आग एवं धुआं", icon: Flame, color: "text-orange-400" },
];

export default function AwarenessPage() {
  const { language, setLanguage } = useApp();
  const [selectedHazard, setSelectedHazard] = useState<string>("flood");
  const [selectedStage, setSelectedStage] = useState<"before" | "during" | "after">("during");
  const [content, setContent] = useState<AwarenessItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAwareness() {
      setLoading(true);
      try {
        const items = await api.getAwareness(selectedHazard, selectedStage, language);
        setContent(items);
      } catch (err) {
        console.error("Failed to load awareness content", err);
      } finally {
        setLoading(false);
      }
    }
    loadAwareness();
  }, [selectedHazard, selectedStage, language]);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2.5">
            <BookOpen className="w-6 h-6 text-orange-500" />
            <span>{language === "en" ? "Disaster Safety & Survival Guides" : "आपदा सुरक्षा एवं जीवन रक्षा मार्गदर्शिका"}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {language === "en"
              ? "Authoritative safety protocols curated from National Disaster Management Authority (NDMA) guidelines."
              : "राष्ट्रीय आपदा प्रबंधन प्राधिकरण (NDMA) और मौसम विभाग द्वारा अनुमोदित आधिकारिक सुरक्षा निर्देश।"}
          </p>
        </div>

        {/* Bilingual Switcher */}
        <div className="flex items-center gap-2 bg-slate-950 p-1.5 rounded-lg border border-slate-800">
          <Globe2 className="w-4 h-4 text-slate-400 ml-1" />
          <button
            onClick={() => setLanguage("en")}
            className={`text-xs px-2.5 py-1 rounded font-semibold transition ${
              language === "en" ? "bg-orange-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            English
          </button>
          <button
            onClick={() => setLanguage("hi")}
            className={`text-xs px-2.5 py-1 rounded font-semibold transition ${
              language === "hi" ? "bg-orange-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            हिन्दी
          </button>
        </div>
      </div>

      {/* Hazard Selector Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {HAZARD_TABS.map((h) => {
          const Icon = h.icon;
          const isSelected = selectedHazard === h.id;
          return (
            <button
              key={h.id}
              onClick={() => setSelectedHazard(h.id)}
              className={`p-3 rounded-xl border text-left flex items-center gap-2.5 transition ${
                isSelected
                  ? "bg-slate-900 border-orange-500 text-white shadow-md"
                  : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
              }`}
            >
              <Icon className={`w-5 h-5 shrink-0 ${isSelected ? "text-orange-400" : h.color}`} />
              <span className="font-bold text-xs">
                {language === "en" ? h.label : h.labelHi}
              </span>
            </button>
          );
        })}
      </div>

      {/* 3 Chronological Stages: Before, During, After */}
      <div className="bg-slate-900 border border-slate-800 p-1.5 rounded-xl flex items-center gap-1">
        <button
          onClick={() => setSelectedStage("before")}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
            selectedStage === "before"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>1. {language === "en" ? "BEFORE (Preparedness)" : "आपदा से पहले (तैयारी)"}</span>
        </button>

        <button
          onClick={() => setSelectedStage("during")}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
            selectedStage === "during"
              ? "bg-red-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>2. {language === "en" ? "DURING (Survival & Action)" : "आपदा के दौरान (जीवन रक्षा)"}</span>
        </button>

        <button
          onClick={() => setSelectedStage("after")}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
            selectedStage === "after"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>3. {language === "en" ? "AFTER (Recovery & Safety)" : "आपदा के बाद (पुनर्प्राप्ति)"}</span>
        </button>
      </div>

      {/* Instructions Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-md space-y-6">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400 space-y-2">
            <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p>{language === "en" ? "Loading guidance..." : "निर्देश लोड हो रहे हैं..."}</p>
          </div>
        ) : content.length > 0 ? (
          content.map((guide) => (
            <div key={guide.id} className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-400" />
                  <span>{guide.title}</span>
                </h2>
                <span className="text-[10px] bg-slate-950 text-slate-400 border border-slate-800 px-2 py-0.5 rounded uppercase font-semibold">
                  NDMA Verified
                </span>
              </div>

              <div className="space-y-3">
                {guide.instructions.map((step, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 flex items-start gap-3 text-slate-200 text-sm leading-relaxed"
                  >
                    <span className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-orange-400 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <p>{step}</p>
                  </div>
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="py-12 text-center space-y-2 text-slate-400">
            <HelpCircle className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs">
              {language === "en"
                ? "No specific instructions loaded for this stage."
                : "इस चरण के लिए कोई विशेष निर्देश उपलब्ध नहीं हैं।"}
            </p>
          </div>
        )}

        {/* Source Attribution Footer */}
        <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-2">
          <div className="flex items-center gap-1.5">
            <Building2 className="w-4 h-4 text-slate-400" />
            <span>
              {language === "en"
                ? "Source Authority: National Disaster Management Authority (NDMA), Govt. of India"
                : "आधिकारिक स्रोत: राष्ट्रीय आपदा प्रबंधन प्राधिकरण (NDMA), भारत सरकार"}
            </span>
          </div>
          <span className="text-slate-500 text-[11px]">
            Reviewed & Updated: 2026
          </span>
        </div>
      </div>
    </div>
  );
}
