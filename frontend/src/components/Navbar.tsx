"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldAlert,
  PhoneCall,
  MapPin,
  Compass,
  AlertTriangle,
  FilePlus2,
  BookOpen,
  ClipboardList,
  Menu,
  X,
  Globe2,
} from "lucide-react";
import { useApp } from "@/context/AppContext";

export default function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const {
    states,
    districts,
    selectedStateId,
    selectedDistrict,
    language,
    isLocating,
    setSelectedStateId,
    setSelectedDistrict,
    setLanguage,
    detectLocation,
  } = useApp();

  const filteredDistricts = selectedStateId
    ? districts.filter((d) => d.state_id === selectedStateId)
    : districts;

  const navLinks = [
    { href: "/", label: language === "en" ? "Home & Status" : "मुख्य पृष्ठ", icon: Compass },
    { href: "/map", label: language === "en" ? "Live Map" : "मानचित्र", icon: MapPin },
    { href: "/alerts", label: language === "en" ? "Alerts" : "चेतावनियाँ", icon: AlertTriangle },
    { href: "/report", label: language === "en" ? "Report Incident" : "घटना दर्ज करें", icon: FilePlus2, highlight: true },
    { href: "/reports/my", label: language === "en" ? "My Reports" : "मेरी रिपोर्ट", icon: ClipboardList },
    { href: "/awareness", label: language === "en" ? "Safety Guides" : "सुरक्षा मार्गदर्शिका", icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-900 border-b border-slate-800 text-white shadow-md">
      {/* Emergency Hotline Top Banner */}
      <div className="bg-red-600 text-white px-4 py-1.5 text-xs sm:text-sm font-semibold flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PhoneCall className="w-4 h-4 animate-pulse" />
          <span>
            {language === "en"
              ? "Emergency Services Hotline: Dial 112 immediately for life-threatening situations."
              : "आपातकालीन सेवा: जीवन रक्षक सहायता के लिए तुरंत 112 डायल करें।"}
          </span>
        </div>
        <a
          href="tel:112"
          className="bg-white text-red-700 px-3 py-0.5 rounded font-bold hover:bg-red-50 transition shadow-sm"
        >
          {language === "en" ? "Call 112" : "112 कॉल करें"}
        </a>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Portal Identity */}
          <Link href="/" className="flex items-center gap-2.5">
            <div className="bg-orange-600 p-2 rounded-lg text-white shadow-sm">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight block leading-tight text-white">
                APAT-RAKSHAK
              </span>
              <span className="text-[11px] text-slate-400 font-medium block">
                {language === "en" ? "Unified Citizen Disaster Portal" : "नागरिक आपदा प्रबंधन पोर्टल"}
              </span>
            </div>
          </Link>

          {/* Location & Language Controls (Desktop) */}
          <div className="hidden lg:flex items-center gap-3 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
            {/* State selector */}
            <select
              aria-label="Select State"
              value={selectedStateId || ""}
              onChange={(e) => {
                const sId = parseInt(e.target.value);
                setSelectedStateId(sId);
                const matching = districts.filter((d) => d.state_id === sId);
                if (matching.length > 0) setSelectedDistrict(matching[0]);
              }}
              className="bg-slate-900 text-xs text-slate-200 border border-slate-700 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-orange-500"
            >
              {states.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>

            {/* District selector */}
            <div className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-orange-400" />
              <select
                aria-label="Select District"
                value={selectedDistrict?.id || ""}
                onChange={(e) => {
                  const d = districts.find((dist) => dist.id === parseInt(e.target.value));
                  if (d) setSelectedDistrict(d);
                }}
                className="bg-slate-900 text-xs font-semibold text-white border border-slate-700 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-orange-500"
              >
                {filteredDistricts.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            {/* GPS Locate Me Button */}
            <button
              onClick={detectLocation}
              disabled={isLocating}
              title={language === "en" ? "Detect my current location" : "मेरी स्थिति का पता लगाएं"}
              className="bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 px-2.5 py-1 rounded text-xs flex items-center gap-1 font-medium transition"
            >
              <Compass className={`w-3.5 h-3.5 text-orange-400 ${isLocating ? "animate-spin" : ""}`} />
              <span>{isLocating ? (language === "en" ? "Locating..." : "खोज रहे हैं...") : (language === "en" ? "GPS" : "जीपीएस")}</span>
            </button>

            {/* Language Switcher */}
            <div className="flex items-center gap-1 border-l border-slate-700 pl-3">
              <Globe2 className="w-3.5 h-3.5 text-slate-400" />
              <button
                onClick={() => setLanguage(language === "en" ? "hi" : "en")}
                className="text-xs font-semibold px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-orange-300 transition"
              >
                {language === "en" ? "हिन्दी" : "English"}
              </button>
            </div>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium transition ${
                    link.highlight
                      ? "bg-orange-600 hover:bg-orange-500 text-white font-bold ml-1 shadow-sm"
                      : isActive
                      ? "bg-slate-800 text-orange-400 border border-slate-700"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={() => setLanguage(language === "en" ? "hi" : "en")}
              className="text-xs font-semibold px-2 py-1 rounded bg-slate-800 border border-slate-700 text-orange-400"
            >
              {language === "en" ? "हिन्दी" : "English"}
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-900 border-b border-slate-800 px-4 pt-2 pb-4 space-y-3">
          {/* Mobile District Selector */}
          <div className="bg-slate-800 p-3 rounded-lg border border-slate-700 space-y-2">
            <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span>{language === "en" ? "Current District" : "वर्तमान जिला"}:</span>
              <button
                onClick={detectLocation}
                disabled={isLocating}
                className="text-xs text-orange-400 font-bold flex items-center gap-1"
              >
                <Compass className={`w-3.5 h-3.5 ${isLocating ? "animate-spin" : ""}`} />
                <span>{language === "en" ? "Auto-Detect GPS" : "जीपीएस से खोजें"}</span>
              </button>
            </div>
            <select
              aria-label="Select District"
              value={selectedDistrict?.id || ""}
              onChange={(e) => {
                const d = districts.find((dist) => dist.id === parseInt(e.target.value));
                if (d) setSelectedDistrict(d);
              }}
              className="w-full bg-slate-900 text-sm font-semibold text-white border border-slate-700 rounded px-2.5 py-1.5"
            >
              {districts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          {/* Mobile Links */}
          <div className="space-y-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
                    link.highlight
                      ? "bg-orange-600 text-white font-bold"
                      : isActive
                      ? "bg-slate-800 text-orange-400"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
}
