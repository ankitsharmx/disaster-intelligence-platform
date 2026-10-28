"use client";

import React, { useEffect, useState } from "react";
import { Bell, Download, CheckCircle2 } from "lucide-react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";

export default function PwaManager() {
  const { selectedDistrict, language } = useApp();
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>("default");
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    // Register Service Worker
    if (typeof window !== "undefined" && "serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js")
        .then(() => console.log("Service Worker registered successfully."))
        .catch((err) => console.warn("Service Worker registration failed:", err));

      if ("Notification" in window) {
        setNotificationPermission(Notification.permission);
      }
    }

    // Capture PWA beforeinstallprompt
    const handleBeforeInstall = (e: any) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    return () => window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
  }, []);

  // Request & Persist Push Subscription
  const handleSubscribe = async () => {
    setStatusMessage(null);

    if (!("Notification" in window)) {
      setStatusMessage("Web Push notifications are not supported by this browser.");
      return;
    }

    try {
      const permission = await Notification.requestPermission();
      setNotificationPermission(permission);

      if (permission === "denied") {
        setStatusMessage(
          language === "en"
            ? "Notification permission was denied in browser settings. You will not receive emergency audio alerts."
            : "ब्राउज़र सेटिंग्स में सूचना अनुमति अस्वीकार कर दी गई है।"
        );
        return;
      }

      if (permission === "granted") {
        // Register or generate simulated push endpoint for browser
        const endpoint = `https://fcm.googleapis.com/fcm/send/device_${Date.now()}`;
        await api.subscribePush({
          endpoint,
          district_id: selectedDistrict?.id,
          p256dh: "mock_p256dh_key",
          auth: "mock_auth_token",
        });

        setIsSubscribed(true);
        setStatusMessage(
          language === "en"
            ? `Subscribed! You will receive emergency alerts targeted to ${selectedDistrict?.name || "your district"}.`
            : `सफलतापूर्वक सदस्यता ली गई! आपको ${selectedDistrict?.name || "जिले"} के लिए आपातकालीन अलर्ट प्राप्त होंगे।`
        );

        // Show immediate confirmation notification
        if ("serviceWorker" in navigator) {
          const reg = await navigator.serviceWorker.ready;
          reg.showNotification("Apat-Rakshak Alert Network", {
            body: `Emergency push notifications activated for ${selectedDistrict?.name || "all districts"}.`,
            icon: "/favicon.ico",
          });
        }
      }
    } catch (err: any) {
      setStatusMessage("Failed to register push subscription: " + err.message);
    }
  };

  const handleInstallApp = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setDeferredPrompt(null);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm text-xs">
      <div className="flex items-center gap-3">
        <div className="bg-orange-500/10 p-2.5 rounded-lg border border-orange-500/20 text-orange-400 shrink-0">
          <Bell className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-white block">
            {language === "en" ? "Emergency Broadcasts & PWA" : "आपातकालीन प्रसारण एवं ऐप"}
          </span>
          <span className="text-slate-400 block text-[11px]">
            {isSubscribed
              ? (language === "en" ? "Active: Notifications will trigger on severe bulletins." : "सक्रिय: गंभीर चेतावनियों पर तुरंत सूचना मिलेगी।")
              : (language === "en" ? "Subscribe for targeted district disaster sirens and install app offline." : "गंभीर चेतावनियों की सूचना पाने के लिए सब्सक्राइब करें।")}
          </span>
          {statusMessage && (
            <span className={`block text-[11px] mt-1 font-semibold ${statusMessage.includes("denied") ? "text-red-400" : "text-emerald-400"}`}>
              {statusMessage}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 w-full sm:w-auto">
        {notificationPermission !== "granted" ? (
          <button
            onClick={handleSubscribe}
            className="flex-1 sm:flex-none bg-orange-600 hover:bg-orange-500 text-white font-bold px-3 py-1.5 rounded-lg transition flex items-center justify-center gap-1.5"
          >
            <Bell className="w-3.5 h-3.5" />
            <span>{language === "en" ? "Enable Alerts" : "सूचनाएं चालू करें"}</span>
          </button>
        ) : (
          <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{language === "en" ? "Alerts Active" : "सक्रिय"}</span>
          </span>
        )}

        {deferredPrompt && (
          <button
            onClick={handleInstallApp}
            className="flex-1 sm:flex-none bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold px-3 py-1.5 rounded-lg transition flex items-center justify-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5 text-orange-400" />
            <span>{language === "en" ? "Install App" : "ऐप इंस्टॉल करें"}</span>
          </button>
        )}
      </div>
    </div>
  );
}
