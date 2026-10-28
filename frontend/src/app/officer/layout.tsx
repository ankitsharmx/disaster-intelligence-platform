"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldAlert,
  LayoutDashboard,
  CheckSquare,
  Send,
  Map,
  History,
  Radio,
  UserCheck,
  LogOut,
  ChevronDown,
  Building2,
  Cpu,
} from "lucide-react";
import { api } from "@/lib/api";

const PRESET_ACCOUNTS = [
  {
    role: "District Officer (Mumbai)",
    email: "officer_mumbai@disastermgmt.gov",
    password: "Officer@123456",
    badge: "District 2 (Mumbai Suburban)",
  },
  {
    role: "District Officer (Pune)",
    email: "officer_pune@disastermgmt.gov",
    password: "Officer@123456",
    badge: "District 4 (Pune)",
  },
  {
    role: "State Administrator",
    email: "state_admin_mh@disastermgmt.gov",
    password: "StateAdmin@123456",
    badge: "State 1 (Maharashtra)",
  },
  {
    role: "System Administrator",
    email: "admin@disastermgmt.gov",
    password: "Admin@123456",
    badge: "Global / All Districts",
  },
];

export default function OfficerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] = useState<any | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [loginEmail, setLoginEmail] = useState("officer_mumbai@disastermgmt.gov");
  const [loginPassword, setLoginPassword] = useState("Officer@123456");
  const [authError, setAuthError] = useState<string | null>(null);

  // Auto-login or verify current token on mount
  useEffect(() => {
    async function initAuth() {
      const token = api.getToken();
      if (!token) {
        // Auto-login with default demo officer (Mumbai) for seamless review
        try {
          const res = await api.login("officer_mumbai@disastermgmt.gov", "Officer@123456");
          setCurrentUser(res);
        } catch {
          // Keep modal available
        }
      } else {
        try {
          const metrics = await api.getOfficerMetrics();
          setCurrentUser({
            role: metrics.jurisdiction.role,
            assigned_district_id: metrics.jurisdiction.assigned_district_id,
            email: "officer_mumbai@disastermgmt.gov",
          });
        } catch {
          // Token might be citizen token or expired, re-login demo officer
          try {
            const res = await api.login("officer_mumbai@disastermgmt.gov", "Officer@123456");
            setCurrentUser(res);
          } catch {
            api.setToken(null);
          }
        }
      }
    }
    initAuth();
  }, []);

  // Connect WebSocket for Real-Time Dashboard Updates
  useEffect(() => {
    let ws: WebSocket | null = null;
    let pingInterval: any = null;

    try {
      const wsUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1")
        .replace("http://", "ws://")
        .replace("https://", "wss://") + "/officer/ws";

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        pingInterval = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        if (event.data === "pong") return;
        try {
          const msg = JSON.parse(event.data);
          // Dispatch custom event to notify current officer views
          window.dispatchEvent(new CustomEvent("officer_ws_message", { detail: msg }));
        } catch {
          // ignore non-json
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (pingInterval) clearInterval(pingInterval);
      };

      ws.onerror = () => {
        setWsConnected(false);
      };
    } catch {
      setWsConnected(false);
    }

    return () => {
      if (pingInterval) clearInterval(pingInterval);
      if (ws) ws.close();
    };
  }, []);

  const handleManualLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    try {
      const res = await api.login(loginEmail, loginPassword);
      setCurrentUser(res);
      setLoginModalOpen(false);
      window.location.reload();
    } catch (err: any) {
      setAuthError(err.message || "Authentication failed.");
    }
  };

  const handleSelectPreset = async (preset: typeof PRESET_ACCOUNTS[0]) => {
    setAuthError(null);
    try {
      const res = await api.login(preset.email, preset.password);
      setCurrentUser(res);
      setLoginModalOpen(false);
      window.location.reload();
    } catch (err: any) {
      setAuthError(err.message || "Failed to switch role.");
    }
  };

  const tabs = [
    { href: "/officer", label: "Dashboard Overview", icon: LayoutDashboard },
    { href: "/officer/queue", label: "Verification Queue", icon: CheckSquare },
    { href: "/officer/alerts/new", label: "Alert Composer", icon: Send },
    { href: "/officer/map", label: "Operational Map", icon: Map },
    { href: "/officer/intelligence", label: "Risk & ML Engine", icon: Cpu },
    { href: "/officer/audit", label: "Audit Trail", icon: History },
  ];

  return (
    <div className="space-y-6">
      {/* Officer Command Center Header Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-md">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 p-2.5 rounded-xl text-white shadow-sm">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-black text-white tracking-tight">
                INCIDENT RESPONSE COMMAND CENTER
              </h1>
              <span className="text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded uppercase font-bold">
                {currentUser?.role ? currentUser.role.replace("_", " ") : "GOVT PORTAL"}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Authorized emergency review, verification decisions & operational geo-targeting
            </p>
          </div>
        </div>

        {/* Status, Jurisdiction & Switch Account */}
        <div className="flex flex-wrap items-center gap-3">
          {/* WebSocket Real-time Indicator */}
          <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800 text-xs">
            <Radio className={`w-3.5 h-3.5 ${wsConnected ? "text-emerald-400 animate-pulse" : "text-slate-500"}`} />
            <span className={wsConnected ? "text-emerald-400 font-semibold" : "text-slate-400"}>
              {wsConnected ? "Live Sync Active" : "Polling Sync"}
            </span>
          </div>

          {/* Current Jurisdiction Tag */}
          <div className="bg-slate-950 px-3 py-1 rounded-lg border border-slate-800 text-xs text-slate-300">
            <span className="text-slate-500 mr-1">Jurisdiction:</span>
            <strong className="text-orange-400">
              {currentUser?.assigned_district_id
                ? `District #${currentUser.assigned_district_id}`
                : currentUser?.assigned_state_id
                ? `State #${currentUser.assigned_state_id}`
                : "Global Command"}
            </strong>
          </div>

          {/* Switch Role Button */}
          <button
            onClick={() => setLoginModalOpen(true)}
            className="bg-indigo-950/80 hover:bg-indigo-900 text-indigo-300 border border-indigo-700 font-semibold px-3 py-1 rounded-lg text-xs flex items-center gap-1.5 transition"
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span>Switch Role / Account</span>
          </button>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="border-b border-slate-800 flex overflow-x-auto gap-2 text-xs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex items-center gap-2 px-4 py-2.5 font-bold whitespace-nowrap border-b-2 transition ${
                isActive
                  ? "border-orange-500 text-orange-400 bg-slate-900/60"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </div>

      {/* Page Content */}
      <div>{children}</div>

      {/* Switch Role / Login Modal */}
      {loginModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-indigo-400" />
                <span>Switch Officer / Administrator Role</span>
              </h3>
              <button
                onClick={() => setLoginModalOpen(false)}
                className="text-slate-400 hover:text-white font-bold text-sm"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Select one of the pre-seeded officer roles to test backend district jurisdiction enforcement:
            </p>

            {authError && (
              <div className="bg-red-950/50 border border-red-800 p-2.5 rounded text-xs text-red-300">
                {authError}
              </div>
            )}

            {/* Presets */}
            <div className="space-y-2">
              {PRESET_ACCOUNTS.map((preset) => (
                <button
                  key={preset.email}
                  onClick={() => handleSelectPreset(preset)}
                  className="w-full text-left bg-slate-950 hover:bg-indigo-950/40 p-3 rounded-lg border border-slate-800 hover:border-indigo-600 transition flex items-center justify-between"
                >
                  <div>
                    <span className="font-bold text-xs text-white block">
                      {preset.role}
                    </span>
                    <span className="text-[11px] text-slate-400 block">
                      {preset.email}
                    </span>
                  </div>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700 font-semibold">
                    {preset.badge}
                  </span>
                </button>
              ))}
            </div>

            {/* Custom Credentials Form */}
            <form onSubmit={handleManualLogin} className="space-y-3 pt-2 border-t border-slate-800">
              <span className="text-[11px] font-bold uppercase text-slate-400 block">
                Or Login with Custom Credentials:
              </span>
              <div className="space-y-2">
                <input
                  type="email"
                  placeholder="Officer Email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>
              <button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 rounded text-xs transition"
              >
                Authenticate & Switch Session
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
