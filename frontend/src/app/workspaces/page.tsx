"use client";

import React, { useState, useEffect } from "react";
import Sidebar from "../../components/layout/Sidebar";
import SearchBar from "../../components/search/SearchBar";
import AmbientBackground from "../../components/layout/AmbientBackground";
import AnswerView from "../../components/answer/AnswerView";
import { Folder, Search, Loader2, Sparkles, Plus, Trash2, ArrowRight } from "lucide-react";

interface Workspace {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

interface Project {
  research_id: number;
  query: string;
  status: string;
  coverage_score: number;
  started_at: string;
}

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [creationName, setCreationName] = useState("");
  const [creationDesc, setCreationDesc] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  // Cross-RAG workspace search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResult, setSearchResult] = useState<any | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState("");

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/workspaces`);
      const data = await res.json();
      setWorkspaces(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectWorkspace = async (ws: Workspace) => {
    setActiveWorkspace(ws);
    setSearchResult(null);
    setSearchQuery("");
    try {
      const res = await fetch(`${apiBase}/api/workspaces/${ws.id}`);
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!creationName.trim()) return;

    try {
      const res = await fetch(`${apiBase}/api/workspaces`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: creationName, description: creationDesc })
      });
      if (res.ok) {
        const newWs = await res.json();
        setWorkspaces((prev) => [newWs, ...prev]);
        setCreationName("");
        setCreationDesc("");
        setShowCreate(false);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleWorkspaceSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !searchQuery.trim()) return;

    setSearchLoading(true);
    setSearchResult(null);
    setStreamingAnswer("");

    try {
      const res = await fetch(`${apiBase}/api/workspaces/${activeWorkspace.id}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery })
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResult(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div className="flex w-full h-screen overflow-hidden bg-[#faf9f6] dark:bg-[#090d16] font-sans text-zinc-900 dark:text-zinc-50">
      <Sidebar onNewSearch={() => {}} />

      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="p-6 border-b border-zinc-200/90 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight flex items-center gap-2">
              <Folder className="w-5 h-5 text-zinc-900 dark:text-zinc-100" />
              Saved Workspaces
            </h1>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">Group your research sessions into folders and run semantic search over accumulated workspace evidence.</p>
          </div>

          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1.5 py-2.5 px-4 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 rounded-xl text-xs font-bold shadow-xs transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Workspace</span>
          </button>
        </header>

        <div className="p-6 flex flex-col md:flex-row gap-6 h-[calc(100vh-100px)] overflow-hidden">
          {/* Left Panel: Folders lists */}
          <div className="w-full md:w-64 shrink-0 flex flex-col gap-4 overflow-y-auto">
            {showCreate && (
              <form onSubmit={handleCreateWorkspace} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-4 rounded-2xl flex flex-col gap-3">
                <input
                  type="text"
                  placeholder="Workspace Name..."
                  value={creationName}
                  onChange={(e) => setCreationName(e.target.value)}
                  className="w-full text-xs p-2.5 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:border-violet-500"
                />
                <input
                  type="text"
                  placeholder="Optional description..."
                  value={creationDesc}
                  onChange={(e) => setCreationDesc(e.target.value)}
                  className="w-full text-xs p-2.5 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:border-violet-500"
                />
                <button
                  type="submit"
                  className="py-2 bg-violet-600 text-white rounded-xl text-xs font-bold"
                >
                  Create
                </button>
              </form>
            )}

            <div className="space-y-1">
              {workspaces.map((ws) => {
                const isActive = activeWorkspace?.id === ws.id;
                return (
                  <button
                    key={ws.id}
                    onClick={() => handleSelectWorkspace(ws)}
                    className={`w-full flex items-center justify-between p-3 rounded-xl border text-left text-xs transition-all ${
                      isActive
                        ? "bg-violet-50 border-violet-200 text-violet-700 dark:bg-violet-950/20 dark:border-violet-900 dark:text-violet-400 font-bold"
                        : "bg-white border-zinc-200 hover:bg-zinc-50 dark:bg-zinc-900 dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-850"
                    }`}
                  >
                    <span className="truncate">{ws.name}</span>
                    <Folder className="w-4 h-4 opacity-60" />
                  </button>
                );
              })}
              {workspaces.length === 0 && !loading && (
                <div className="text-center text-xs text-zinc-400 py-8">No workspaces created yet.</div>
              )}
            </div>
          </div>

          {/* Right Panel: Workspace details & Search */}
          <div className="flex-1 bg-white dark:bg-zinc-950 rounded-2xl border border-zinc-200 dark:border-zinc-800 overflow-y-auto flex flex-col">
            {activeWorkspace ? (
              <div className="flex flex-col h-full">
                {/* Header info */}
                <div className="p-6 border-b border-zinc-100 dark:border-zinc-900">
                  <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-50">{activeWorkspace.name}</h2>
                  <p className="text-xs text-zinc-500 mt-1">{activeWorkspace.description || "No description provided."}</p>
                </div>

                {/* Workspace Search box */}
                <div className="p-6 border-b border-zinc-100 dark:border-zinc-900 bg-zinc-50 dark:bg-zinc-900/30">
                  <h3 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-3">Semantic folder search (Cross-RAG)</h3>
                  <form onSubmit={handleWorkspaceSearch} className="flex gap-2">
                    <input
                      type="text"
                      placeholder={`Query all evidence saved in ${activeWorkspace.name}...`}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="flex-1 text-xs p-3 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:border-violet-500"
                    />
                    <button
                      type="submit"
                      disabled={searchLoading}
                      className="py-2.5 px-4 bg-violet-600 hover:bg-violet-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                    >
                      {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                      <span>Ask Workspace</span>
                    </button>
                  </form>
                </div>

                {/* Main Results / Projects list */}
                <div className="flex-1 p-6 overflow-y-auto">
                  {searchLoading && (
                    <div className="flex flex-col items-center justify-center py-12 gap-2 text-zinc-500 text-xs">
                      <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
                      <span>Searching Qdrant collection...</span>
                    </div>
                  )}

                  {searchResult && (
                    <div className="mb-6">
                      <AnswerView
                        result={{
                          query: searchQuery,
                          mode: "research",
                          answer: searchResult.answer,
                          sources: searchResult.sources || [],
                          citations: searchResult.citations || [],
                          evidences: searchResult.evidences || []
                        }}
                        onCitationClick={() => {}}
                        onSourceClick={() => {}}
                      />
                    </div>
                  )}

                  {!searchResult && !searchLoading && (
                    <div>
                      <h3 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-3">Linked Research Projects</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {projects.map((p) => (
                          <div key={p.research_id} className="p-4 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200/50 dark:border-zinc-800/80 rounded-xl flex items-center justify-between text-xs">
                            <div className="truncate max-w-[80%]">
                              <div className="font-bold text-zinc-900 dark:text-zinc-100 truncate">{p.query}</div>
                              <div className="text-[10px] text-zinc-400 mt-1">Coverage: {Math.round(p.coverage_score * 100)}%</div>
                            </div>
                            <ArrowRight className="w-4 h-4 text-zinc-400 shrink-0" />
                          </div>
                        ))}
                        {projects.length === 0 && (
                          <div className="text-xs text-zinc-400 py-6 text-center col-span-2">
                            No research sessions linked to this workspace folder. Bookmark or save sessions to add them here.
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-24 text-center text-zinc-400 gap-3">
                <Folder className="w-12 h-12 opacity-30" />
                <div className="text-sm font-semibold">Select a workspace folder to begin</div>
                <div className="text-xs max-w-xs leading-relaxed">Choose a workspace from the left panel to run cross-RAG questions or organize your collection.</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
