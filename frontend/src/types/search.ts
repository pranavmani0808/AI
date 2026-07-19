import { Source } from "./source";
import { Evidence, Citation } from "./evidence";

export type SearchMode = "web" | "research" | "academic" | "products";

export type ResearchStage =
  | "understanding"
  | "searching"
  | "selecting"
  | "crawling"
  | "extracting"
  | "indexing"
  | "rag"
  | "cross_checking"
  | "generating"
  | "verifying";

export interface StageStatus {
  id: ResearchStage;
  label: string;
  status: "idle" | "running" | "completed" | "failed";
  message?: string;
}

export interface SearchResult {
  query: string;
  mode: SearchMode;
  answer: string;
  sources: Source[];
  evidences: Evidence[];
  citations: Citation[];
  recommendedProduct?: {
    name: string;
    price: string;
    specs: string[];
    pros: string[];
  };
}
