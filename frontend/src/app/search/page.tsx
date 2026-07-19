"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Sidebar from "../../components/layout/Sidebar";
import SearchBar from "../../components/search/SearchBar";
import ProgressTracker from "../../components/research/ProgressTracker";
import AnswerView from "../../components/answer/AnswerView";
import SourcesPanel from "../../components/sources/SourcesPanel";
import EvidenceModal from "../../components/evidence/EvidenceModal";
import { executeSearchMock } from "../../lib/api";
import { SearchResult, SearchMode, StageStatus } from "../../types/search";
import { Citation } from "../../types/evidence";
import { Sparkles, ArrowLeft, RefreshCw } from "lucide-react";

function SearchPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const query = searchParams.get("q") || "";
  const mode = (searchParams.get("mode") as SearchMode) || "web";

  const [stages, setStages] = useState<StageStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);

  // UI state overlays
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [showSourcesPanel, setShowSourcesPanel] = useState(false);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);

  useEffect(() => {
    if (query) {
      handleSearchExecution(query, mode);
    }
  }, [query, mode]);

  const handleSearchExecution = async (searchQuery: string, searchMode: SearchMode) => {
    setLoading(true);
    setResult(null);
    setSelectedCitation(null);
    setSelectedSourceId(null);
    
    try {
      const searchResult = await executeSearchMock(searchQuery, searchMode, (updatedStages) => {
        setStages(updatedStages);
      });
      setResult(searchResult);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewSearch = (newQuery: string, newMode: SearchMode) => {
    router.push(`/search?q=${encodeURIComponent(newQuery)}&mode=${newMode}`);
  };

  // Click on a citation reference inside the answer
  const handleCitationClick = (citationId: number) => {
    if (!result) return;
    const citation = result.citations.find((c) => c.id === citationId);
    if (citation) {
      setSelectedCitation(citation);
    }
  };

  // Click on a source card (either opens details sidebar or highlights in sidebar)
  const handleSourceClick = (sourceId: string) => {
    setShowSourcesPanel(true);
    setSelectedSourceId(sourceId || null);
  };

  const activeEvidence = selectedCitation && result
    ? result.evidences.find((e) => e.id === selectedCitation.evidenceId)
    : null;
  const activeSource = selectedCitation && result
    ? result.sources.find((s) => s.id === selectedCitation.sourceId)
    : null;

  return (
    <div className="flex w-full h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950 font-sans">
      {/* Collapsible Sidebar */}
      <Sidebar onNewSearch={() => router.push("/")} />

      {/* Main Results Scroll Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-zinc-50 dark:bg-zinc-950">
        
        {/* Compact Header search box */}
        <header className="p-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex items-center justify-between gap-4 sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push("/")}
              className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl text-zinc-500 transition-colors"
              title="Back to home"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <span className="hidden sm:inline-flex items-center gap-1.5 py-1 px-2.5 bg-violet-50 dark:bg-violet-950/40 border border-violet-100 dark:border-violet-900/50 rounded-lg text-[10px] font-bold text-violet-700 dark:text-violet-400 uppercase tracking-wider">
              <Sparkles className="w-3 h-3" />
              Research
            </span>
          </div>

          <div className="flex-1 max-w-xl">
            <SearchBar
              initialValue={query}
              initialMode={mode}
              onSearch={handleNewSearch}
              isCompact
            />
          </div>

          <div className="w-8" /> {/* Balance layout spacing */}
        </header>

        {/* Dynamic Display Area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 flex flex-col justify-between">
          <div>
            {/* 1. Loading Research Stages View */}
            {loading && !result && (
              <ProgressTracker stages={stages} />
            )}

            {/* 2. Finished Search Result View */}
            {result && !loading && (
              <AnswerView
                result={result}
                onCitationClick={handleCitationClick}
                onSourceClick={handleSourceClick}
              />
            )}

            {/* 3. Empty State (no query entered) */}
            {!query && (
              <div className="text-center py-16">
                <p className="text-sm text-zinc-400 dark:text-zinc-500">
                  Please enter a query in the search bar above to begin.
                </p>
              </div>
            )}
          </div>

          {/* Follow-up question input at the bottom of result screen */}
          {result && !loading && (
            <div className="w-full max-w-3xl mx-auto border-t border-zinc-200 dark:border-zinc-900 pt-6 mt-8">
              <SearchBar
                onSearch={handleNewSearch}
                placeholder="Ask a follow-up..."
                isCompact
              />
            </div>
          )}
        </div>
      </div>

      {/* RAG Evidence Detail Modal overlay */}
      {selectedCitation && activeEvidence && activeSource && (
        <EvidenceModal
          citation={selectedCitation}
          evidence={activeEvidence}
          source={activeSource}
          onClose={() => setSelectedCitation(null)}
        />
      )}

      {/* Slide-out Sources Sidebar Drawer */}
      {showSourcesPanel && result && (
        <SourcesPanel
          sources={result.sources}
          selectedSourceId={selectedSourceId}
          onSelectSource={(id) => setSelectedSourceId(id)}
          onClose={() => {
            setShowSourcesPanel(false);
            setSelectedSourceId(null);
          }}
        />
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="flex w-full h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <Loader2 className="w-8 h-8 text-violet-500 animate-spin" />
      </div>
    }>
      <SearchPageContent />
    </Suspense>
  );
}

// Inline fallback loader helper for Suspense
import { Loader2 } from "lucide-react";
