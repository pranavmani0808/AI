import re
from typing import List, Dict, Any, Tuple
from backend.llm.gemini import GeminiProvider
from backend.intelligence.query_router import QueryRouter, QueryIntent

REFORMULATION_SYSTEM_PROMPT = (
    "You are an expert search query reformulator for an AI research engine.\n\n"
    "Your ONLY task is to rephrase the user's latest follow-up question into a single, self-contained, "
    "context-independent search query using the minimal relevant details from the conversation history.\n\n"
    "Strict Rules:\n"
    "1. If the user's query relies on conversation history (using pronouns like 'it', 'he', 'they', 'this', or contextual follow-ups like 'what about...', 'how about...', 'which one...', 'why?'), rewrite it into a clear standalone search query.\n"
    "2. If the user's query is ALREADY standalone or represents a completely new independent topic switch, output the original user query UNCHANGED.\n"
    "3. Do NOT attempt to answer the question.\n"
    "4. Do NOT invent new facts or entities not present in the conversation history.\n"
    "5. Output ONLY the raw standalone query string. No preamble, no quotes, no markdown."
)

class QueryReformulator:
    """
    Reformulates contextual follow-up questions into standalone queries
    using recent conversation history.
    """
    def __init__(self, provider: GeminiProvider = None):
        self.provider = provider or GeminiProvider()
        self.router = QueryRouter()

    def _heuristic_reformulate(self, query: str, chat_history: List[Dict[str, str]]) -> str:
        """Heuristic pattern fallback for common follow-up phrases if LLM is rate-limited."""
        trimmed = query.strip()
        last_user_msg = next((m.get("content", "") for m in reversed(chat_history) if m.get("role") == "user"), "")
        
        lower_query = trimmed.lower()
        if lower_query.startswith("what about ") or lower_query.startswith("how about "):
            topic = trimmed[11:].strip("? ")
            if last_user_msg:
                return f"{last_user_msg} - {topic}"
        elif " it " in f" {lower_query} " or lower_query.startswith("how does it "):
            if last_user_msg:
                return f"{trimmed} ({last_user_msg})"
                
        return trimmed

    async def reformulate(self, query: str, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Evaluates whether query requires conversation context and returns
        reformulated metadata object.
        """
        trimmed_query = query.strip()
        
        # 1. Fast-path check: empty history or conversational greetings skip reformulation
        if not chat_history or len(chat_history) == 0:
            return {
                "original_query": trimmed_query,
                "standalone_query": trimmed_query,
                "reformulated": False
            }

        fast_intent = self.router.classify_fast_path(trimmed_query)
        if fast_intent == QueryIntent.CONVERSATIONAL:
            return {
                "original_query": trimmed_query,
                "standalone_query": trimmed_query,
                "reformulated": False
            }

        # 2. Extract recent minimum conversation context (up to last 3 turns)
        recent_history = chat_history[-6:]
        history_formatted_lines = []
        for msg in recent_history:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "").strip()
            if content:
                history_formatted_lines.append(f"{role}: {content[:300]}")
        history_str = "\n".join(history_formatted_lines)

        # 3. Assemble prompt for LLM reformulation
        user_prompt = (
            f"<conversation_history>\n{history_str}\n</conversation_history>\n\n"
            f"Latest User Query: {trimmed_query}\n\n"
            f"Standalone Search Query:"
        )

        try:
            reformulated_text = await self.provider.generate(REFORMULATION_SYSTEM_PROMPT, user_prompt)
            reformulated_text = reformulated_text.strip().strip('"\'')
            
            if not reformulated_text or reformulated_text.lower() == trimmed_query.lower():
                return {
                    "original_query": trimmed_query,
                    "standalone_query": trimmed_query,
                    "reformulated": False
                }
            
            return {
                "original_query": trimmed_query,
                "standalone_query": reformulated_text,
                "reformulated": True
            }
        except Exception as e:
            print(f"Gemini LLM call failed during reformulation: {e}. Falling back to heuristic pattern parser.")
            fallback_query = self._heuristic_reformulate(trimmed_query, chat_history)
            is_changed = fallback_query.lower() != trimmed_query.lower()
            return {
                "original_query": trimmed_query,
                "standalone_query": fallback_query,
                "reformulated": is_changed
            }
