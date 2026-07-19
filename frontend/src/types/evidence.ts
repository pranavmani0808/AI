export interface Evidence {
  id: string;
  sourceId: string;
  content: string;
  relevanceScore: number; // Percentage (e.g. 92)
}

export interface Citation {
  id: number; // 1-indexed citation number displayed in text (e.g. [1])
  sourceId: string;
  evidenceId?: string;
}
