"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FilePlus2,
  AlertTriangle,
  PhoneCall,
  CheckCircle2,
  Compass,
  Upload,
  AlertCircle,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";

const INCIDENT_TYPES = [
  { id: "flood", label: "Flood / Severe Waterlogging", labelHi: "बाढ़ / गंभीर जलभराव", icon: "🌊" },
  { id: "fire", label: "Fire / Smoke Outbreak", labelHi: "आग / धुआं का प्रकोप", icon: "🔥" },
  { id: "landslide", label: "Landslide / Rockfall", labelHi: "भूस्खलन / चट्टान खिसकना", icon: "⛰️" },
  { id: "blocked_road", label: "Blocked Road / Fallen Tree", labelHi: "सड़क अवरोध / गिरा हुआ पेड़", icon: "🚧" },
  { id: "infrastructure", label: "Damaged Bridge / Building", labelHi: "पुल या इमारत की क्षति", icon: "🏚️" },
  { id: "other", label: "Other Hazard / Emergency", labelHi: "अन्य आपातकालीन स्थिति", icon: "⚠️" },
];

export default function ReportPage() {
  const { selectedDistrict, language } = useApp();

  const [type, setType] = useState<string>("flood");
  const [description, setDescription] = useState<string>("");
  const [latitude, setLatitude] = useState<number>(selectedDistrict ? selectedDistrict.center_lat : 18.96);
  const [longitude, setLongitude] = useState<number>(selectedDistrict ? selectedDistrict.center_lon : 72.83);
  const [locationMethod, setLocationMethod] = useState<"gps" | "manual">("manual");
  const [file, setFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [submissionSuccess, setSubmissionSuccess] = useState<boolean>(false);
  const [_createdReportId, setCreatedReportId] = useState<number | null>(null);

  // Capture Browser Geolocation
  const handleCaptureGPS = () => {
    if (!navigator.geolocation) {
      setFormError("Geolocation is not supported by your browser. Please enter coordinates manually.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(parseFloat(pos.coords.latitude.toFixed(5)));
        setLongitude(parseFloat(pos.coords.longitude.toFixed(5)));
        setLocationMethod("gps");
        setFormError(null);
      },
      (_err) => {
        setFormError("Could not retrieve GPS location. You can enter coordinates manually or use the district center.");
        setLocationMethod("manual");
      },
      { timeout: 8000 }
    );
  };

  // Handle Media File Selection with Validation
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    // Validate size (max 10MB)
    if (selected.size > 10 * 1024 * 1024) {
      setFormError("Uploaded file exceeds 10MB limit. Please upload a smaller photo or document.");
      return;
    }

    // Validate type
    const validMimes = ["image/jpeg", "image/png", "image/webp", "video/mp4", "application/pdf"];
    if (!validMimes.includes(selected.type)) {
      setFormError("Unsupported file format. Please upload JPEG, PNG, WEBP, MP4, or PDF.");
      return;
    }

    setFile(selected);
    setFormError(null);

    if (selected.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = () => setFilePreview(reader.result as string);
      reader.readAsDataURL(selected);
    } else {
      setFilePreview(null);
    }
  };

  // Handle Form Submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim() || description.length < 5) {
      setFormError("Please provide a clear factual description (at least 5 characters).");
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      // 1. Submit report
      const report = await api.submitReport({
        type,
        description,
        latitude,
        longitude,
      });

      setCreatedReportId(report.id);

      // 2. Upload media if attached
      if (file) {
        try {
          await api.uploadReportMedia(report.id, file);
        } catch (mediaErr: any) {
          console.warn("Report saved but media upload had an issue:", mediaErr.message);
        }
      }

      setSubmissionSuccess(true);
    } catch (err: any) {
      setFormError(err.message || "Failed to submit report. Please check your connection.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Critical Emergency Advisory Banner */}
      <div className="bg-red-950/80 border-2 border-red-600 rounded-xl p-4 flex items-start gap-3 shadow-md">
        <AlertTriangle className="w-6 h-6 text-red-500 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h3 className="font-bold text-sm text-white">
            {language === "en" ? "Emergency Notice (Life Safety First)" : "आपातकालीन चेतावनी (जीवन सुरक्षा सर्वोपरि)"}
          </h3>
          <p className="text-xs text-red-200 leading-relaxed">
            {language === "en"
              ? "Submitting a citizen report is an administrative recording process. If you or someone else is in immediate physical danger, dial 112 immediately."
              : "नागरिक रिपोर्ट दर्ज करना प्रशासनिक प्रक्रिया है। यदि जान का खतरा है, तो रिपोर्ट की प्रतीक्षा न करें, तुरंत 112 डायल करें।"}
          </p>
          <a
            href="tel:112"
            className="inline-flex items-center gap-1.5 bg-red-600 hover:bg-red-500 text-white font-bold px-3 py-1 rounded text-xs mt-2 transition"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>{language === "en" ? "Call 112 Emergency" : "112 डायल करें"}</span>
          </a>
        </div>
      </div>

      {/* Main Report Form Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-md space-y-6">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FilePlus2 className="w-5 h-5 text-orange-500" />
            <span>{language === "en" ? "Submit Field Incident Report" : "आपदा घटना की रिपोर्ट दर्ज करें"}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {language === "en"
              ? "Your report will be sent to district disaster officers for ground verification before publication."
              : "आपकी रिपोर्ट सत्यापन के लिए जिला आपदा नियंत्रण कक्ष को भेजी जाएगी।"}
          </p>
        </div>

        {formError && (
          <div className="bg-red-950/50 border border-red-800 p-3 rounded-lg flex items-center gap-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Step 1: Hazard Category */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              1. {language === "en" ? "Select Incident Type" : "आपदा का प्रकार चुनें"} *
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {INCIDENT_TYPES.map((inc) => (
                <button
                  type="button"
                  key={inc.id}
                  onClick={() => setType(inc.id)}
                  className={`p-3 rounded-lg border text-left flex flex-col justify-between transition ${
                    type === inc.id
                      ? "bg-orange-600 border-orange-500 text-white shadow-md font-bold"
                      : "bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700"
                  }`}
                >
                  <span className="text-xl mb-1">{inc.icon}</span>
                  <span className="text-xs leading-tight">
                    {language === "en" ? inc.label : inc.labelHi}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Step 2: Description */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              2. {language === "en" ? "Describe What Happened" : "घटना का विवरण दें"} *
            </label>
            <textarea
              required
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={
                language === "en"
                  ? "e.g., Road underpass submerged in 3 feet water, 2 vehicles stranded near railway station."
                  : "उदा. रेलवे स्टेशन के पास अंडरपास में 3 फीट पानी भर गया है, दो वाहन फंसे हैं।"
              }
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-orange-500"
            />
          </div>

          {/* Step 3: Location Coordinates */}
          <div className="space-y-2 bg-slate-950 p-4 rounded-lg border border-slate-800">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                3. {language === "en" ? "Location Coordinates" : "घटना स्थल निर्देशांक"} *
              </label>
              <button
                type="button"
                onClick={handleCaptureGPS}
                className="text-xs text-orange-400 font-bold flex items-center gap-1 hover:text-orange-300 transition"
              >
                <Compass className="w-3.5 h-3.5" />
                <span>{language === "en" ? "Auto-Detect GPS" : "जीपीएस से भरें"}</span>
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <span className="text-[11px] text-slate-500 block">Latitude (अक्षांश)</span>
                <input
                  type="number"
                  step="0.00001"
                  required
                  value={latitude}
                  onChange={(e) => setLatitude(parseFloat(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white"
                />
              </div>
              <div>
                <span className="text-[11px] text-slate-500 block">Longitude (देशांतर)</span>
                <input
                  type="number"
                  step="0.00001"
                  required
                  value={longitude}
                  onChange={(e) => setLongitude(parseFloat(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white"
                />
              </div>
            </div>
            <p className="text-[11px] text-slate-500">
              {locationMethod === "gps"
                ? "📍 Location captured via browser GPS sensor."
                : "📍 Coordinates set manually or from district center."}
            </p>
          </div>

          {/* Step 4: Evidence File Upload */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              4. {language === "en" ? "Attach Photo / Document (Optional)" : "तस्वीर या दस्तावेज संलग्न करें (वैकल्पिक)"}
            </label>
            <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-lg p-4 text-center cursor-pointer transition">
              <input
                type="file"
                id="file-upload"
                onChange={handleFileChange}
                accept="image/*,video/mp4,application/pdf"
                className="hidden"
              />
              <label htmlFor="file-upload" className="cursor-pointer space-y-1 block">
                <Upload className="w-6 h-6 text-orange-400 mx-auto mb-1" />
                <span className="text-xs font-semibold text-slate-300 block">
                  {file ? file.name : (language === "en" ? "Click to upload evidence photo" : "फोटो अपलोड करने के लिए क्लिक करें")}
                </span>
                <span className="text-[11px] text-slate-500 block">
                  Max file size: 10MB (JPEG, PNG, MP4, PDF)
                </span>
              </label>
            </div>

            {filePreview && (
              <div className="relative w-32 h-32 rounded-lg overflow-hidden border border-slate-700 mt-2">
                <img src={filePreview} alt="Preview" className="w-full h-full object-cover" />
              </div>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white font-bold py-3 rounded-lg text-sm transition shadow-md flex items-center justify-center gap-2"
          >
            <FilePlus2 className="w-4 h-4" />
            <span>
              {submitting
                ? (language === "en" ? "Submitting Report..." : "रिपोर्ट दर्ज हो रही है...")
                : (language === "en" ? "Submit Incident Report" : "रिपोर्ट जमा करें")}
            </span>
          </button>
        </form>
      </div>

      {/* Post-Submission Confirmation Modal */}
      {submissionSuccess && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 text-center space-y-4 shadow-2xl">
            <div className="w-12 h-12 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-7 h-7" />
            </div>

            <h3 className="text-lg font-bold text-white">
              {language === "en" ? "Report Submitted Successfully" : "रिपोर्ट सफलतापूर्वक दर्ज की गई"}
            </h3>

            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-xs text-slate-300 space-y-2 text-left">
              <p className="font-semibold text-orange-400">
                {language === "en"
                  ? "Report submitted. It is awaiting verification and has not yet been confirmed."
                  : "रिपोर्ट दर्ज कर ली गई है। यह वर्तमान में सत्यापन की प्रतीक्षा में है और सार्वजनिक मानचित्र पर अभी प्रकाशित नहीं हुई है।"}
              </p>
              <p className="text-slate-400">
                {language === "en"
                  ? "District disaster response officers will verify this submission. Once verified, it will appear on the public map."
                  : "जिला नियंत्रण कक्ष के अधिकारी इसकी समीक्षा करेंगे। पुष्टि होने के बाद ही यह सार्वजनिक मानचित्र पर दिखाई देगी।"}
              </p>
            </div>

            <div className="flex gap-2 pt-2">
              <Link
                href="/reports/my"
                className="flex-1 bg-orange-600 hover:bg-orange-500 text-white font-bold py-2.5 rounded-lg text-xs"
              >
                {language === "en" ? "View My Reports" : "मेरी रिपोर्ट देखें"}
              </Link>
              <button
                onClick={() => {
                  setSubmissionSuccess(false);
                  setDescription("");
                  setFile(null);
                  setFilePreview(null);
                }}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold px-4 py-2.5 rounded-lg text-xs"
              >
                {language === "en" ? "Submit Another" : "नई रिपोर्ट"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
