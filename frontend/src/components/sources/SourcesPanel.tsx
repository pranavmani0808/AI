"use client";

import React, { useRef, useEffect, useState } from "react";
import { Source } from "../../types/source";
import SourceCard from "./SourceCard";
import { X, Search, CheckCircle2, Circle, AlertTriangle, FileText, Bookmark, Split } from "lucide-react";

interface SourcesPanelProps {
  sources: Source[];
  selectedSourceId: string | null;
  onSelectSource: (sourceId: string | null) => void;
  onClose: () => void;
  mode?: string;
  plan?: { objective: string; topics: string[] } | null;
  coverage?: { score: number; missing: string[]; covered: string[] } | null;
  evidences?: any[];
  contradictions?: any[];
  performance?: any;
}

export default function SourcesPanel({
  sources,
  selectedSourceId,
  onSelectSource,
  onClose,
  mode = "web",
  plan = null,
  coverage = null,
  evidences = [],
  contradictions = [],
  performance = null
}: SourcesPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<"sources" | "plan" | "evidence" | "contradictions">("sources");

  // Close panel on clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        const target = event.target as HTMLElement;
        if (!target.closest("button") && !target.closest("a")) {
          onClose();
        }
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClose]);

  const isResearch = mode === "research";

  return (
    <div 
      ref={panelRef}
      className="w-full md:w-[450px] bg-white dark:bg-zinc-900 border-l border-zinc-200/90 dark:border-zinc-800 flex flex-col h-screen shadow-xl relative z-25"
    >
      {/* Header */}
      <div className="p-4 border-b border-zinc-200/80 dark:border-zinc-800 flex items-center justify-between bg-white dark:bg-zinc-900">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-zinc-900 dark:text-zinc-100" />
          <h3 className="text-base font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight">
            {isResearch ? "Research Findings" : "Sources Analyzed"}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-zinc-500 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs Selector for Deep Research */}
      {isResearch && (
        <div className="flex border-b border-zinc-200/80 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 px-2 py-1.5 gap-1">
          <button
            onClick={() => setActiveTab("sources")}
            className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === "sources"
                ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-2xs font-bold"
                : "text-zinc-500 hover:bg-zinc-200/60 dark:hover:bg-zinc-800 hover:text-zinc-900"
            }`}
          >
            <Bookmark className="w-3.5 h-3.5" />
            Sources ({sources.length})
          </button>
          <button
            onClick={() => setActiveTab("plan")}
            className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === "plan"
                ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-2xs font-bold"
                : "text-zinc-500 hover:bg-zinc-200/60 dark:hover:bg-zinc-800 hover:text-zinc-900"
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Plan
          </button>
          <button
            onClick={() => setActiveTab("evidence")}
            className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === "evidence"
                ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-2xs font-bold"
                : "text-zinc-500 hover:bg-zinc-200/60 dark:hover:bg-zinc-800 hover:text-zinc-900"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Evidence ({evidences.length})
          </button>
          <button
            onClick={() => setActiveTab("contradictions")}
            className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === "contradictions"
                ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-2xs font-bold"
                : "text-zinc-500 hover:bg-zinc-200/60 dark:hover:bg-zinc-800 hover:text-zinc-900"
            }`}
          >
            <Split className="w-3.5 h-3.5" />
            Conflicts ({contradictions.length})
          </button>
        </div>
      )}

      {/* Render active tab content */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {activeTab === "sources" && (
          <>
            <div className="text-xs text-zinc-500 dark:text-zinc-400 mb-1 px-1">
              The autonomous search pipeline crawled and analyzed **{sources.length} sources** across **{Array.from(new Set(sources.map(s => s.domain))).length} unique domains** to answer your query.
            </div>
            {sources.map((src, index) => (
              <SourceCard
                key={src.id}
                source={src}
                index={index}
                isSelected={selectedSourceId === src.id}
                onClick={() => onSelectSource(selectedSourceId === src.id ? null : src.id)}
              />
            ))}
          </>
        )}

        {activeTab === "plan" && plan && (
          <div className="space-y-4 bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-zinc-200 dark:border-zinc-800">
            <div>
              <h4 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">Research Objective</h4>
              <p className="text-sm text-zinc-800 dark:text-zinc-200 mt-1 font-semibold leading-relaxed">{plan.objective}</p>
            </div>
            
            {/* Chronological Research Timeline */}
            <div className="border-t border-zinc-100 dark:border-zinc-800 pt-3">
              <h4 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-3">Research Timeline</h4>
              <div className="relative pl-6 border-l border-violet-100 dark:border-violet-900/50 space-y-4">
                <div className="relative">
                  <div className="absolute -left-[30px] top-1 w-2.5 h-2.5 bg-violet-600 rounded-full ring-4 ring-violet-100 dark:ring-violet-900/30" />
                  <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">Objective Planned</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Defined topics checklist</div>
                </div>
                <div className="relative">
                  <div className="absolute -left-[30px] top-1 w-2.5 h-2.5 bg-violet-600 rounded-full ring-4 ring-violet-100 dark:ring-violet-900/30" />
                  <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">SearXNG Query Execution</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Discovered web endpoints and search items</div>
                </div>
                <div className="relative">
                  <div className="absolute -left-[30px] top-1 w-2.5 h-2.5 bg-violet-600 rounded-full ring-4 ring-violet-100 dark:ring-violet-900/30" />
                  <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">Concurrent crawl completed</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Parsed and clean text document segments</div>
                </div>
                <div className="relative">
                  <div className="absolute -left-[30px] top-1 w-2.5 h-2.5 bg-violet-600 rounded-full ring-4 ring-violet-100 dark:ring-violet-900/30" />
                  <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">Qdrant Vector indexing</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Document chunks stored securely</div>
                </div>
              </div>
            </div>

            <div className="border-t border-zinc-100 dark:border-zinc-800 pt-3">
              <h4 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-2">Checklist Coverage</h4>
              <ul className="space-y-2">
                {plan.topics.map((t) => {
                  const isCovered = coverage?.covered.includes(t) || !coverage?.missing.includes(t);
                  return (
                    <li key={t} className="flex items-center gap-2 text-xs">
                      {isCovered ? (
                        <CheckCircle2 className="w-4.5 h-4.5 text-emerald-500" />
                      ) : (
                        <Circle className="w-4.5 h-4.5 text-zinc-300 dark:text-zinc-700" />
                      )}
                      <span className={isCovered ? "text-zinc-500 dark:text-zinc-400 line-through" : "text-zinc-800 dark:text-zinc-200 font-medium"}>
                        {t}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
            {performance && (
              <div className="border-t border-zinc-200 dark:border-zinc-800 pt-3 mt-3">
                <h4 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-2">Performance & Diagnostics</h4>
                <div className="bg-zinc-100 dark:bg-zinc-900 rounded-xl p-3 space-y-1.5 text-[11px] text-zinc-700 dark:text-zinc-300">
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Request ID</span>
                    <span className="font-mono text-[9px] text-zinc-500 truncate max-w-[180px]">{performance.request_id || "N/A"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Stop Reason</span>
                    <span className="font-medium text-violet-600 dark:text-violet-400">{performance.stop_reason || "coverage_reached"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Total Duration</span>
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {((performance.total_ms || performance.total_duration_ms || 0) / 1000).toFixed(2)}s
                    </span>
                  </div>
                  <div className="border-t border-zinc-200/50 dark:border-zinc-800/50 my-1 pt-1.5 space-y-1 text-[10px]">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Planning stage</span>
                      <span>{performance.planning_ms || 0}ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Search queries</span>
                      <span>{performance.search_ms || 0}ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Concurrent crawl</span>
                      <span>{performance.crawl_ms || 0}ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Embeddings upsert</span>
                      <span>{performance.embedding_ms || 0}ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">RAG retrieval</span>
                      <span>{performance.retrieval_ms || 0}ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Answer synthesis</span>
                      <span>{performance.generation_ms || performance.llm_generation_ms || 0}ms</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "evidence" && (
          <div className="space-y-3">
            <div className="text-xs text-zinc-500 px-1">
              Click on any evidence segment to inspect Qdrant retrieval relevance, metadata, and origin links.
            </div>
            {evidences.map((ev, index) => {
              const src = sources.find(s => s.id === ev.sourceId);
              return (
                <div key={index} className="p-3 bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 text-xs shadow-sm hover:border-violet-400 dark:hover:border-violet-800 cursor-pointer transition-all flex flex-col gap-2">
                  <div className="flex justify-between items-center text-[10px] text-zinc-400 font-bold uppercase">
                    <span>Evidence [{index + 1}] - {src?.domain || "Source"}</span>
                    <span className="text-violet-600 dark:text-violet-400">Relevance: {ev.relevanceScore}%</span>
                  </div>
                  <p className="text-zinc-700 dark:text-zinc-300 leading-relaxed italic">"{ev.content}"</p>
                  {src && (
                    <div className="text-[10px] text-zinc-500 border-t border-zinc-100 dark:border-zinc-800/80 pt-2 mt-1 truncate">
                      URL: <span className="text-violet-600 dark:text-violet-400 underline">{src.url}</span>
                    </div>
                  )}
                </div>
              );
            })}
            {evidences.length === 0 && (
              <div className="text-center text-zinc-400 text-xs py-8">No evidence chunks available.</div>
            )}
          </div>
        )}

        {activeTab === "contradictions" && (
          <div className="space-y-3">
            {contradictions.map((c, index) => (
              <div key={index} className="p-4 bg-amber-50/55 dark:bg-amber-950/10 border border-amber-200 dark:border-amber-900/50 rounded-xl text-xs flex flex-col gap-2 shadow-sm">
                <div className="flex items-center gap-1.5 text-amber-800 dark:text-amber-400 font-bold uppercase text-[10px]">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  <span>Conflict: {c.topic}</span>
                </div>
                <div className="space-y-1.5 mt-1 text-zinc-800 dark:text-zinc-200">
                  <div>
                    <span className="font-bold text-violet-700 dark:text-violet-400">Claim 1:</span> "{c.claim_a}"
                    <div className="text-[10px] text-zinc-400 underline mt-0.5 truncate">{c.source_a_url}</div>
                  </div>
                  <div className="border-t border-amber-200/50 dark:border-amber-900/20 pt-1.5 mt-1.5">
                    <span className="font-bold text-violet-700 dark:text-violet-400">Claim 2:</span> "{c.claim_b}"
                    <div className="text-[10px] text-zinc-400 underline mt-0.5 truncate">{c.source_b_url}</div>
                  </div>
                </div>
              </div>
            ))}
            {contradictions.length === 0 && (
              <div className="text-center text-zinc-400 text-xs py-8">
                ✓ No contradictions detected across source claims.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
