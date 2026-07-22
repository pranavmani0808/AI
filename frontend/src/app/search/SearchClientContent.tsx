"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "../../components/layout/Sidebar";
import SearchBar from "../../components/search/SearchBar";
import ProgressTracker from "../../components/research/ProgressTracker";
import AnswerView from "../../components/answer/AnswerView";
import SourcesPanel from "../../components/sources/SourcesPanel";
import EvidenceModal from "../../components/evidence/EvidenceModal";
import { executeSearch, executeAutonomousResearch, executeFollowUp } from "../../lib/api";
import { SearchResult, SearchMode, StageStatus } from "../../types/search";
import { Citation } from "../../types/evidence";
import { Sparkles, ArrowLeft, RefreshCw, AlertCircle, CheckCircle2, Circle, HelpCircle, Loader2 } from "lucide-react";

interface SearchClientContentProps {
  query: string;
  mode: SearchMode;
  sessionId: string | null;
}

export default function SearchClientContent({ query, mode, sessionId }: SearchClientContentProps) {
  const router = useRouter();

  const [stages, setStages] = useState<StageStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState<string>("");

  // Phase 5 Deep Research tracking state
  const [researchPlan, setResearchPlan] = useState<{ objective: string; topics: string[] } | null>(null);
  const [researchCoverage, setResearchCoverage] = useState<{ score: number; missing: string[]; covered: string[] } | null>(null);
  const [researchFollowUps, setResearchFollowUps] = useState<{ queries: string[]; iteration: number }[]>([]);
  const [researchStatusMsg, setResearchStatusMsg] = useState<string>("");
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  // UI state overlays
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [showSourcesPanel, setShowSourcesPanel] = useState(false);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);

  // Phase 7 Dynamic Research preferences
  const [researchBudget, setResearchBudget] = useState<"quick" | "standard" | "deep">("standard");
  const [includeDomains, setIncludeDomains] = useState<string[]>([]);
  const [excludeDomains, setExcludeDomains] = useState<string[]>([]);
  const [sourcePreference, setSourcePreference] = useState<string>("balanced");
  const [datePreference, setDatePreference] = useState<string>("any_time");

  const [followupLoading, setFollowupLoading] = useState(false);

  // Keyboard Shortcuts Hook
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCmdOrCtrl = e.metaKey || e.ctrlKey;
      if (isCmdOrCtrl && e.key === "k") {
        e.preventDefault();
        const ta = document.querySelector("textarea");
        if (ta) ta.focus();
      }
      if (e.key === "Escape") {
        setShowSourcesPanel(false);
        setSelectedCitation(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (sessionId) {
      handleLoadStoredSession(sessionId);
    } else if (query) {
      handleSearchExecution(query, mode);
    }
  }, [query, mode, sessionId]);

  const handleLoadStoredSession = async (id: string) => {
    setLoading(true);
    setResult(null);
    setError(null);
    setSelectedCitation(null);
    setSelectedSourceId(null);
    setStreamingAnswer("");
    setResearchPlan(null);
    setResearchCoverage(null);
    setResearchFollowUps([]);
    setResearchStatusMsg("");
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/research/${id}`);
      if (!response.ok) {
        throw new Error(`Failed to load stored session: Status code ${response.status}`);
      }
      const data = await response.json();
      
      setResult({
        query: data.query,
        mode: "research",
        answer: data.answer,
        sources: data.sources || [],
        citations: data.citations || [],
        evidences: data.evidences || [],
        contradictions: data.contradictions || [],
        researchPlan: { objective: "Deep Research Objectives", topics: data.sources.map((s: any) => s.title) },
        researchCoverage: { score: data.coverage_score, missing: [], covered: [] },
        performance: data.research_metadata || {
          total_ms: 0,
          planning_ms: 0,
          search_ms: 0,
          crawl_ms: 0,
          embedding_ms: 0,
          retrieval_ms: 0,
          generation_ms: 0,
          stop_reason: "Loaded from cache"
        }
      });
      
      setResearchPlan({ objective: "Reopened Deep Research", topics: data.sources.map((s: any) => s.title) });
      setResearchCoverage({ score: data.coverage_score, missing: [], covered: [] });
      
    } catch (err) {
      console.error("Failed to load history session:", err);
      setError(err instanceof Error ? err.message : "Failed to load session details.");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchExecution = async (searchQuery: string, searchMode: SearchMode) => {
    setLoading(true);
    setResult(null);
    setError(null);
    setSelectedCitation(null);
    setSelectedSourceId(null);
    setStreamingAnswer("");
    setResearchPlan(null);
    setResearchCoverage(null);
    setResearchFollowUps([]);
    setResearchStatusMsg("");
    
    const controller = new AbortController();
    setAbortController(controller);
    
    try {
      if (searchMode === "research") {
        let currentPlan: any = null;
        let currentCoverage: any = null;
        
        const finalResult = await executeAutonomousResearch(
          searchQuery,
          (event, data) => {
            if (event === "plan") {
              currentPlan = data;
              setResearchPlan(data);
            } else if (event === "coverage") {
              currentCoverage = data;
              setResearchCoverage(data);
            } else if (event === "follow_up") {
              setResearchFollowUps((prev) => [...prev, data]);
            } else if (event === "status") {
              setResearchStatusMsg(data.message || data.stage);
              // Extract active iteration
              const matches = data.message?.match(/Iteration (\d+)/i) || data.message?.match(/step (\d+)/i);
              const iterNum = matches ? matches[1] : "1";
              setStages([{ id: "generating", label: "Research step", status: "running", message: iterNum }]);
            }
          },
          (tokenText) => {
            setStreamingAnswer(tokenText);
          },
          controller.signal,
          researchBudget,
          includeDomains,
          excludeDomains,
          sourcePreference,
          datePreference
        );
        
        if (finalResult) {
          setResult({
            query: searchQuery,
            mode: "research",
            answer: finalResult.answer,
            sources: finalResult.sources || [],
            citations: finalResult.citations || [],
            evidences: finalResult.evidences || [],
            contradictions: finalResult.contradictions || [],
            researchPlan: currentPlan || finalResult.researchPlan,
            researchCoverage: currentCoverage || finalResult.researchCoverage,
            performance: finalResult.research_metadata
          });
        }
      } else {
        const searchResult = await executeSearch(
          searchQuery,
          searchMode,
          (updatedStages) => {
            setStages(updatedStages);
          },
          (tokenText) => {
            setStreamingAnswer(tokenText);
          }
        );
        setResult(searchResult);
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        console.log("Research request aborted by user.");
      } else {
        console.error("Search failed:", err);
        setError(err instanceof Error ? err.message : "Failed to connect to the autonomous research backend. Please verify the backend service is running.");
      }
    } finally {
      setLoading(false);
      setAbortController(null);
    }
  };

  const handleCancelResearch = () => {
    if (abortController) {
      abortController.abort();
      setLoading(false);
      setAbortController(null);
      setError("Research operation cancelled by user.");
    }
  };

  const handleFollowUpSubmit = async (followupQuery: string) => {
    if (!result) return;
    setFollowupLoading(true);
    setStreamingAnswer("");
    
    try {
      const researchId = sessionId ? parseInt(sessionId) : (result as any).research_id || 1;
      
      const res = await executeFollowUp(
        researchId,
        followupQuery,
        (tokenText) => {
          setStreamingAnswer(tokenText);
        }
      );
      
      if (res) {
        setResult((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            answer: res.answer,
            citations: res.citations || [],
            evidences: res.evidences || [],
            sources: res.sources || []
          };
        });
      }
    } catch (err) {
      console.error("Follow-up failed:", err);
    } finally {
      setFollowupLoading(false);
      setStreamingAnswer("");
    }
  };

  const handleNewSearch = (newQuery: string, newMode: SearchMode) => {
    const params = new URLSearchParams({
      q: newQuery.trim(),
      mode: newMode,
    });
    router.push(`/search?${params.toString()}`);
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

  const renderDeepResearchProgress = () => {
    return (
      <div className="w-full max-w-xl mx-auto peec-card p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/90 dark:border-zinc-800 shadow-xs my-6">
        <div className="text-center mb-6">
          <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-50 flex items-center justify-center gap-2">
            <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
            Deep Researching...
          </h3>
          <p className="text-[10px] text-zinc-400 dark:text-zinc-500 mt-1 uppercase tracking-wider font-bold">
            Iteration {stages.length > 0 ? stages[0].message || "1" : "1"}
          </p>
        </div>

        <div className="space-y-4">
          {/* Status Message */}
          {researchStatusMsg && (
            <div className="p-3 bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-xl text-xs font-semibold leading-relaxed">
              Status: {researchStatusMsg}
            </div>
          )}

          {/* Research objective */}
          {researchPlan && (
            <div className="border-t border-zinc-100 dark:border-zinc-800 pt-4">
              <h4 className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-2">Research checklist</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {researchPlan.topics.map((topic) => {
                  const isCovered = researchCoverage?.covered.includes(topic);
                  const isMissing = researchCoverage?.missing.includes(topic);
                  return (
                    <div key={topic} className="flex items-center gap-2 text-xs">
                      {isCovered ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      ) : isMissing ? (
                        <AlertCircle className="w-4 h-4 text-amber-500" />
                      ) : (
                        <Circle className="w-4 h-4 text-zinc-300 dark:text-zinc-700" />
                      )}
                      <span className={isCovered ? "text-zinc-500 dark:text-zinc-400 line-through" : "text-zinc-800 dark:text-zinc-200"}>
                        {topic}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Coverage Indicator */}
          {researchCoverage && (
            <div className="border-t border-zinc-100 dark:border-zinc-800 pt-4">
              <div className="flex justify-between text-xs font-bold mb-1">
                <span className="text-zinc-500">Evidence Coverage</span>
                <span className="text-sky-600 dark:text-sky-400">{Math.round(researchCoverage.score * 100)}%</span>
              </div>
              <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-sky-600 dark:bg-sky-400 h-full transition-all duration-500"
                  style={{ width: `${researchCoverage.score * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Target Query Expansion */}
          {researchFollowUps.length > 0 && (
            <div className="border-t border-zinc-100 dark:border-zinc-800 pt-4 space-y-2">
              <h4 className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">Follow-up Searches</h4>
              {researchFollowUps.map((fu, idx) => (
                <div key={idx} className="text-xs p-2.5 bg-zinc-50 dark:bg-zinc-800/60 rounded-lg border border-zinc-200/80 dark:border-zinc-800">
                  <div className="text-[9px] text-zinc-400 font-bold uppercase mb-1">Gap targeted in iteration {fu.iteration}</div>
                  <ul className="list-disc list-inside space-y-1 text-zinc-700 dark:text-zinc-300 pl-1">
                    {fu.queries.map((q) => (
                      <li key={q} className="truncate">{q}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}

          {/* User Cancellation control button */}
          <div className="flex justify-center border-t border-zinc-100 dark:border-zinc-800 pt-4 mt-2">
            <button
              onClick={handleCancelResearch}
              className="px-4 py-2 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/20 dark:hover:bg-rose-950/40 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50 rounded-xl text-xs font-semibold tracking-tight transition-colors shadow-2xs"
            >
              Stop Research
            </button>
          </div>
        </div>
      </div>
    );
  };

  const activeEvidence = selectedCitation && result
    ? result.evidences.find((e) => e.id === selectedCitation.evidenceId)
    : null;
  const activeSource = selectedCitation && result
    ? result.sources.find((s) => s.id === selectedCitation.sourceId)
    : null;

  return (
    <div className="flex w-full h-screen overflow-hidden bg-[#faf9f6] dark:bg-[#090d16] font-sans text-zinc-900 dark:text-zinc-50">
      {/* Collapsible Sidebar for Workspace */}
      <Sidebar onNewSearch={() => router.push("/")} />

      {/* Main Results Scroll Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        
        {/* Compact Header search box */}
        <header className="p-4 border-b border-zinc-200/90 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between gap-4 sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push("/")}
              className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-zinc-500 transition-colors"
              title="Back to home"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <span className="hidden sm:inline-flex items-center gap-1.5 py-1 px-3 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-full text-[10px] font-bold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider">
              <Sparkles className="w-3 h-3 text-sky-600 dark:text-sky-400" />
              Research Mode
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
        <div className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6 space-y-6">
          
          {/* Query Header Display */}
          {query && result?.intent !== "conversational" && result?.retrieval_used !== false && (
            <div className="border-b border-zinc-200/80 dark:border-zinc-800 pb-4">
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Research Objective
              </span>
              <h1 className="text-xl sm:text-2xl font-extrabold text-zinc-900 dark:text-zinc-50 mt-1 tracking-tight">
                "{query}"
              </h1>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-4 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl flex items-center gap-3 text-rose-700 dark:text-rose-400 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <div className="flex-1 font-semibold">{error}</div>
              <button
                onClick={() => handleSearchExecution(query, mode)}
                className="py-1 px-3 bg-rose-100 hover:bg-rose-200 dark:bg-rose-900/40 text-rose-800 dark:text-rose-300 rounded-lg text-xs font-bold transition-colors shrink-0"
              >
                Retry
              </button>
            </div>
          )}

          {/* Loading Progress State */}
          {loading && mode === "research" && result?.intent !== "conversational" && renderDeepResearchProgress()}
          {loading && mode !== "research" && result?.intent !== "conversational" && <ProgressTracker stages={stages} />}

          {/* Live Streaming Content Indicator */}
          {streamingAnswer && (
            <div className="peec-card p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/90 dark:border-zinc-800 shadow-xs">
              {result?.intent !== "conversational" && result?.retrieval_used !== false && (
                <div className="flex items-center gap-2 text-sky-600 dark:text-sky-400 mb-3 text-xs font-bold">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Synthesizing grounded response...</span>
                </div>
              )}
              <div className="prose dark:prose-invert max-w-none text-sm text-zinc-800 dark:text-zinc-200 leading-relaxed font-sans whitespace-pre-wrap">
                {streamingAnswer}
              </div>
            </div>
          )}

          {/* Final Generated Answer View */}
          {result && !loading && (
            <AnswerView
              result={result}
              onCitationClick={handleCitationClick}
              onSourceClick={handleSourceClick}
            />
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
          mode={result.mode}
          plan={result.researchPlan || researchPlan}
          coverage={result.researchCoverage || researchCoverage}
          evidences={result.evidences}
          contradictions={result.contradictions}
          performance={result.performance}
        />
      )}
    </div>
  );
}
