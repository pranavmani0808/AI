import React, { Suspense } from "react";
import SearchClientContent from "./SearchClientContent";
import { SearchMode } from "../../types/search";
import { Loader2 } from "lucide-react";

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{
    q?: string;
    mode?: string;
    session_id?: string;
  }>;
}

export default async function SearchPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const query = params.q || "";
  const mode = (params.mode as SearchMode) || "web";
  const sessionId = params.session_id || null;

  return (
    <Suspense
      fallback={
        <div className="flex w-full h-screen items-center justify-center bg-[#faf9f6] dark:bg-[#090d16]">
          <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
        </div>
      }
    >
      <SearchClientContent
        query={query}
        mode={mode}
        sessionId={sessionId}
      />
    </Suspense>
  );
}
