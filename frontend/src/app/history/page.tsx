"use client";

import React, { useState, useEffect } from "react";
import Sidebar from "../../components/layout/Sidebar";
import AmbientBackground from "../../components/layout/AmbientBackground";
import { Search, History, Calendar, Clock, BarChart2, Bookmark, CheckCircle2, ChevronRight, Activity, Loader2, AlertCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface HistorySession {
  research_id: number;
  query: string;
  status: string;
  iterations: number;
  coverage_score: number;
  sources_analyzed: number;
  started_at: string;
}

export default function HistoryPage() {
  const [historyList, setHistoryList] = useState<HistorySession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [systemStatus, setSystemStatus] = useState<"healthy" | "degraded" | "offline">("healthy");
  const router = useRouter();

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    fetchHistory();
    checkHealth();
  }, []);

  const fetchHistory = async (filterQuery: string = "") => {
    setLoading(true);
    setError(null);
    try {
      const url = filterQuery 
        ? `${API_BASE_URL}/api/research/history?q=${encodeURIComponent(filterQuery)}`
        : `${API_BASE_URL}/api/research/history`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to retrieve research history list.");
      const data = await res.json();
      setHistoryList(data);
    } catch (e) {
      console.error(e);
      setError("Failed to connect to history database. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (!res.ok) {
        setSystemStatus("degraded");
        return;
      }
      const data = await res.json();
      setSystemStatus(data.status === "healthy" ? "healthy" : "degraded");
    } catch (e) {
      setSystemStatus("offline");
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchHistory(searchQuery);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
      case "success":
        return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400 border-emerald-100 dark:border-emerald-900/30";
      case "running":
        return "bg-violet-50 text-violet-700 dark:bg-violet-950/30 dark:text-violet-400 border-violet-100 dark:border-violet-900/30 animate-pulse";
      default:
        return "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400 border-rose-100 dark:border-rose-900/30";
    }
  };

  return (
    <div className="flex w-full h-screen overflow-hidden bg-[#faf9f6] dark:bg-[#090d16] font-sans text-zinc-900 dark:text-zinc-50">
      <Sidebar onNewSearch={() => {}} />

      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="p-6 border-b border-zinc-200/90 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight">Research History</h1>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">Reopen and audit past multi-step autonomous searches</p>
            </div>
          </div>

          {/* System Status Indicators */}
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">System Status:</span>
            <div className={`flex items-center gap-1.5 py-1 px-3 rounded-full text-xs font-bold ${
              systemStatus === "healthy" 
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-900/30"
                : systemStatus === "degraded"
                ? "bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-900/30"
                : "bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/30 dark:text-rose-400 dark:border-rose-900/30"
            }`}>
              <Activity className="w-3.5 h-3.5" />
              <span className="capitalize">{systemStatus === "healthy" ? "Operational" : systemStatus === "degraded" ? "Degraded" : "Offline"}</span>
            </div>
          </div>
        </header>

        <div className="p-6 max-w-4xl mx-auto w-full space-y-6">
          {/* History Search Filter */}
          <form onSubmit={handleSearchSubmit} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-sky-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search previous research..."
                className="w-full pl-10 pr-4 py-2.5 glass-input-container rounded-2xl text-sm focus:outline-none text-zinc-900 dark:text-zinc-50"
              />
            </div>
            <button
              type="submit"
              className="px-5 py-2.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white rounded-2xl text-sm font-bold transition-all shadow-md shadow-sky-500/25"
            >
              Filter
            </button>
          </form>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
              <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Loading research records...</p>
            </div>
          ) : error ? (
            <div className="p-6 glass-panel border border-rose-200/80 dark:border-rose-900/50 rounded-3xl text-center">
              <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
              <p className="text-sm text-zinc-700 dark:text-rose-400 font-bold">{error}</p>
            </div>
          ) : historyList.length === 0 ? (
            <div className="text-center py-16 glass-panel rounded-3xl">
              <History className="w-8 h-8 text-sky-300 dark:text-sky-700 mx-auto mb-2" />
              <p className="text-sm font-semibold text-zinc-600 dark:text-zinc-400">No matching search history found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {historyList.map((session) => (
                <div
                  key={session.research_id}
                  onClick={() => {
                    const params = new URLSearchParams({
                      q: session.query.trim(),
                      mode: "research",
                      session_id: session.research_id.toString(),
                    });
                    router.push(`/search?${params.toString()}`);
                  }}
                  className="peec-card peec-card-hover p-4 rounded-xl cursor-pointer transition-all flex items-center justify-between gap-4 group bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800"
                >
                  <div className="flex-1 min-w-0 space-y-1.5">
                    <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-50 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors leading-snug">
                      {session.query}
                    </h3>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-400 dark:text-zinc-500">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5" />
                        {new Date(session.started_at).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        {new Date(session.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Bookmark className="w-3.5 h-3.5" />
                        {session.sources_analyzed} sources
                      </span>
                      <span className="flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {Math.round(session.coverage_score * 100)}% coverage
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider border rounded-lg ${getStatusColor(session.status)}`}>
                      {session.status}
                    </span>
                    <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
