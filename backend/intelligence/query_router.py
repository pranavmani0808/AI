from enum import Enum
from typing import Dict, Any, Optional
import re
from backend.llm.gemini import GeminiProvider

class QueryIntent(str, Enum):
    CONVERSATIONAL = "conversational"
    GENERAL_KNOWLEDGE = "general_knowledge"
    WEB_SEARCH = "web_search"
    RESEARCH = "research"
    ACADEMIC = "academic"
    PRODUCT = "product"

CONVERSATIONAL_EXACT_PATTERNS = {
    "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
    "thanks", "thank you", "who are you", "what can you do", "how are you",
    "who created you", "who made you", "help", "hi there", "hello there",
    "greetings", "hey there", "what's up", "whats up", "sup", "yo",
    "thank you so much", "bye", "goodbye", "see ya"
}

CONVERSATIONAL_REGEX_PATTERNS = [
    r"^(hi|hello|hey|greetings|howdy|sup|yo)(\s+there|\s+bot|\s+ai)?[\s!\.\?]*$",
    r"^who\s+(are\s+you|created\s+you|made\s+you)[\s!\.\?]*$",
    r"^what\s+(can\s+you\s+do|are\s+your\s+capabilities)[\s!\.\?]*$",
    r"^how\s+are\s+you(\s+doing)?[\s!\.\?]*$",
    r"^(thanks|thank\s+you|thx|ty)[\s!\.\?]*$"
]

FRESHNESS_KEYWORDS = {
    "latest", "today", "current", "2026", "2025", "now", "price", "prices",
    "weather", "news", "recent", "release", "stock", "score", "versus", "vs",
    "who won", "breaking", "update"
}

PRODUCT_KEYWORDS = {
    "phone", "laptop", "price", "buy", "best under", "specs", "iphone",
    "macbook", "galaxy", "review", "deal", "discount", "brand"
}

class QueryRouter:
    """
    Intelligent Query Classifier & Pipeline Router.
    Determines query intent BEFORE expensive web search, crawling, and RAG retrieval.
    """

    def __init__(self):
        self.llm = GeminiProvider()

    def classify_fast_path(self, query: str) -> Optional[QueryIntent]:
        """Runs instant regex & pattern matching for conversational greetings."""
        cleaned = query.strip().lower()
        cleaned_no_punct = re.sub(r"[^\w\s]", "", cleaned)

        if cleaned_no_punct in CONVERSATIONAL_EXACT_PATTERNS:
            return QueryIntent.CONVERSATIONAL

        for pattern in CONVERSATIONAL_REGEX_PATTERNS:
            if re.match(pattern, cleaned, re.IGNORECASE):
                return QueryIntent.CONVERSATIONAL

        return None

    async def route_query(self, query: str, selected_mode: str = "web") -> Dict[str, Any]:
        """
        Classifies query intent and determines if retrieval is necessary.
        Returns routing metadata: intent, retrieval_used, strategy.
        """
        # 1. Check fast-path for conversational queries
        fast_intent = self.classify_fast_path(query)
        if fast_intent == QueryIntent.CONVERSATIONAL:
            return {
                "intent": QueryIntent.CONVERSATIONAL.value,
                "retrieval_used": False,
                "strategy": "conversational_llm"
            }

        # 2. Check explicit selected mode overrides
        query_lower = query.strip().lower()
        words = set(re.findall(r"\w+", query_lower))
        has_freshness = bool(words & FRESHNESS_KEYWORDS)

        if selected_mode == "academic":
            intent = QueryIntent.ACADEMIC
            retrieval_used = True
        elif selected_mode == "products" or (words & PRODUCT_KEYWORDS and ("best" in words or "price" in words)):
            intent = QueryIntent.PRODUCT
            retrieval_used = True
        elif selected_mode == "research":
            # If user explicitly selected Research mode, check if it's general knowledge or deep research
            intent = QueryIntent.RESEARCH
            retrieval_used = True
        else:
            # Mode is "web"
            if not has_freshness and len(words) <= 7 and (
                query_lower.startswith("what is ") or 
                query_lower.startswith("explain ") or 
                query_lower.startswith("how does ") or 
                query_lower.startswith("define ")
            ):
                # General knowledge conceptual query
                intent = QueryIntent.GENERAL_KNOWLEDGE
                retrieval_used = False
            else:
                intent = QueryIntent.WEB_SEARCH
                retrieval_used = True

        return {
            "intent": intent.value,
            "retrieval_used": retrieval_used,
            "strategy": "direct_llm" if not retrieval_used else "search_rag"
        }
