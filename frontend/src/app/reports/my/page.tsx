"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ClipboardList,
  FileText,
  RefreshCw,
  Info,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";
import { CitizenReport } from "@/types";

export default function MyReportsPage() {
  const { language } = useApp();
  const [reports, setReports] = useState<CitizenReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [_error, setError] = useState<string | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMyReports();
      setReports(data);
    } catch (err: any) {
      setError(err.message || "Failed to load reports history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "submitted":
        return {
          bg: "bg-blue-950 text-blue-300 border-blue-800",
          label: language === "en" ? "Awaiting Review" : "सत्यापन लंबित",
          desc: language === "en" ? "Received by system. Awaiting officer assignment." : "प्राप्त हुआ, अधिकारी समीक्षा की प्रतीक्षा है।",
        };
      case "under_review":
        return {
          bg: "bg-amber-950 text-amber-300 border-amber-800",
          label: language === "en" ? "Under Field Review" : "समीक्षा जारी",
          desc: language === "en" ? "An emergency officer is actively checking ground evidence." : "अधिकारी द्वारा जमीनी साक्ष्य की जांच की जा रही है।",
        };
      case "verified":
        return {
          bg: "bg-emerald-950 text-emerald-300 border-emerald-800",
          label: language === "en" ? "Verified & Published" : "सत्यापित एवं प्रकाशित",
          desc: language === "en" ? "Confirmed on public map layers for emergency response." : "सत्यापित। यह सार्वजनिक मानचित्र पर दिखाई दे रही है।",
        };
      case "rejected":
        return {
          bg: "bg-red-950 text-red-300 border-red-800",
          label: language === "en" ? "Rejected" : "अस्वीकृत",
          desc: language === "en" ? "Could not be verified or marked as duplicate/false report." : "साक्ष्य अपर्याप्त या गलत सूचना के कारण अस्वीकृत।",
        };
      case "resolved":
        return {
          bg: "bg-slate-800 text-slate-300 border-slate-700",
          label: language === "en" ? "Resolved" : "समाधान पूर्ण",
          desc: language === "en" ? "Incident neutralized by municipal or disaster teams." : "राहत दलों द्वारा स्थिति सामान्य कर दी गई है।",
        };
      case "reopened":
        return {
          bg: "bg-purple-950 text-purple-300 border-purple-800",
          label: language === "en" ? "Reopened" : "पुनः जांच",
          desc: language === "en" ? "Investigation reopened following new field information." : "नई जानकारी के आधार पर पुनः जांच शुरू की गई है।",
        };
      default:
        return {
          bg: "bg-slate-800 text-slate-400 border-slate-700",
          label: status.toUpperCase(),
          desc: "",
        };
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2.5">
            <ClipboardList className="w-6 h-6 text-orange-500" />
            <span>{language === "en" ? "My Submitted Reports" : "मेरी दर्ज की गई रिपोर्ट"}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {language === "en"
              ? "Track the verification and publication lifecycle of your reported incidents."
              : "अपनी दर्ज की गई आपदा घटनाओं की वर्तमान स्थिति और अधिकारी टिप्पणियां देखें।"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchReports}
            className="text-xs bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>{language === "en" ? "Refresh" : "ताजा करें"}</span>
          </button>
          <Link
            href="/report"
            className="text-xs bg-orange-600 hover:bg-orange-500 text-white font-bold px-3 py-1.5 rounded-lg transition"
          >
            + {language === "en" ? "New Report" : "नई रिपोर्ट"}
          </Link>
        </div>
      </div>

      {/* Explanatory Notice */}
      <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex items-start gap-3 text-xs text-slate-400">
        <Info className="w-5 h-5 text-orange-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-slate-300">
            {language === "en" ? "About Report Verification:" : "रिपोर्ट सत्यापन प्रक्रिया:"}
          </p>
          <p>
            {language === "en"
              ? "To prevent rumors and unverified alarm during emergencies, new submissions are marked SUBMITTED and reviewed by authorized district disaster response officers before being published to the live public map."
              : "आपातकाल के समय अफवाहों को रोकने के लिए, सभी रिपोर्टों की समीक्षा अधिकृत जिला अधिकारियों द्वारा की जाती है। सत्यापन के बाद ही रिपोर्ट सार्वजनिक मानचित्र पर दिखाई देती है।"}
          </p>
        </div>
      </div>

      {/* Reports List */}
      {loading ? (
        <div className="text-center py-16 space-y-2">
          <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-400">{language === "en" ? "Loading your reports..." : "रिपोर्ट लोड हो रही हैं..."}</p>
        </div>
      ) : reports.length > 0 ? (
        <div className="space-y-4">
          {reports.map((report) => {
            const badge = getStatusBadge(report.status);
            return (
              <div
                key={report.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-400">#{report.id}</span>
                    <span className="text-xs font-bold uppercase tracking-wider bg-slate-950 text-white px-2 py-0.5 rounded border border-slate-800">
                      {report.type}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(report.created_at).toLocaleString()}
                    </span>
                  </div>

                  <span className={`text-[11px] font-bold px-2.5 py-1 rounded border uppercase tracking-wider ${badge.bg}`}>
                    {badge.label}
                  </span>
                </div>

                <p className="text-sm text-slate-200 leading-relaxed">
                  {report.description}
                </p>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs space-y-1">
                  <p className="text-slate-400">
                    <strong>Status Meaning:</strong> {badge.desc}
                  </p>
                  <p className="text-slate-500">
                    Location: {report.latitude.toFixed(4)}, {report.longitude.toFixed(4)}
                  </p>
                  {report.confidence_score !== undefined && (
                    <p className="text-slate-500">
                      AI Confidence Score: {(report.confidence_score * 100).toFixed(0)}%
                    </p>
                  )}
                </div>

                {/* Officer Review Notes */}
                {report.reviews && report.reviews.length > 0 && (
                  <div className="bg-slate-950/90 border border-slate-800 p-3 rounded-lg space-y-1 text-xs">
                    <span className="font-bold text-orange-400 block">
                      {language === "en" ? "Officer Review Remarks:" : "समीक्षा अधिकारी की टिप्पणी:"}
                    </span>
                    {report.reviews.map((rev) => (
                      <div key={rev.id} className="text-slate-300">
                        <span className="font-semibold uppercase text-slate-400">[{rev.decision}]</span>: {rev.notes || "No notes"}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center space-y-3">
          <FileText className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="font-bold text-base text-white">
            {language === "en" ? "No Incident Reports Submitted Yet" : "अभी तक कोई रिपोर्ट दर्ज नहीं की गई है"}
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {language === "en"
              ? "If you observe rising floodwaters, blocked roads, or fallen powerlines, you can report them to emergency teams."
              : "यदि आप जलभराव, सड़क अवरोध या गिरे हुए बिजली के तार देखते हैं, तो आप तुरंत रिपोर्ट दर्ज कर सकते हैं।"}
          </p>
          <Link
            href="/report"
            className="inline-block bg-orange-600 hover:bg-orange-500 text-white font-bold px-4 py-2 rounded-lg text-xs transition"
          >
            {language === "en" ? "Submit First Report" : "पहली रिपोर्ट दर्ज करें"}
          </Link>
        </div>
      )}
    </div>
  );
}
