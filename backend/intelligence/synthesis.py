import asyncio
import time
from typing import List
from backend.rag.models import RetrievedChunk
from backend.llm.models import GeneratedAnswer
from backend.llm.context_builder import build_grounding_context
from backend.llm.prompts import SYSTEM_INSTRUCTION
from backend.llm.gemini import GeminiProvider
from backend.llm.citation_validator import validate_and_repair_citations
from backend.intelligence.models import Contradiction
from backend.core.config import settings

class ResearchSynthesizer:
    """
    Synthesizes the final research report. Reuses Phase 4 grounding configurations,
    system instructions, and citation validation checks, while injecting source contradictions.
    """
    def __init__(self, provider: GeminiProvider = None):
        self.provider = provider or GeminiProvider()

    async def synthesize(
        self,
        query: str,
        search_id: int,
        retrieved_chunks: List[RetrievedChunk],
        contradictions: List[Contradiction]
    ) -> GeneratedAnswer:
        start_time = time.time()
        
        # 1. Build Grounding Context
        context_str, evidences = build_grounding_context(retrieved_chunks)
        
        if not evidences:
            generation_time = int((time.time() - start_time) * 1000)
            return GeneratedAnswer(
                query=query,
                search_id=search_id,
                answer="I couldn't find enough reliable evidence in the retrieved sources to answer this confidently.",
                citations=[],
                grounded=False,
                model=settings.GEMINI_MODEL,
                generation_time_ms=generation_time
            )
            
        # 2. Append contradiction context if disagreements were detected
        contradiction_guidance = ""
        if contradictions:
            contradiction_guidance = (
                "\n\n[CRITICAL NOTE: THE FOLLOWING CONTRADICTIONS WERE DETECTED BETWEEN SOURCE EVIDENCE CHUNKS.\n"
                "Do NOT choose one statement as correct. Instead, state clearly in your response that the sources disagree "
                "or conflict on these points, and cite both conflicting sources respectively.]\n"
            )
            for c in contradictions:
                contradiction_guidance += (
                    f"- Topic '{c.topic}':\n"
                    f"  * Source A ({c.source_a}) claims: \"{c.claim_a}\"\n"
                    f"  * Source B ({c.source_b}) claims: \"{c.claim_b}\"\n"
                )
                
        # 3. Assemble final synthesis prompt
        prompt = (
            f"User Search Query: {query}\n\n"
            f"Reference Evidence Chunks:\n{context_str}\n"
            f"{contradiction_guidance}\n"
            f"Answer:"
        )
        
        try:
            raw_answer = None
            for attempt in range(2):
                try:
                    raw_answer = await self.provider.generate(SYSTEM_INSTRUCTION, prompt)
                    raw_answer = raw_answer.strip()
                    break
                except Exception as ex:
                    if "429" in str(ex) or "429" in getattr(ex, "message", "") or "quota" in str(ex).lower():
                        if attempt == 0:
                            print("Gemini API rate limit hit in synthesis. Sleeping 5s before retry...")
                            await asyncio.sleep(5.0)
                            continue
                    raise ex
            
            if raw_answer:
                # 4. Run post-generation citation validator & repair pass
                validated_text, citations, grounded = await validate_and_repair_citations(
                    raw_answer,
                    evidences,
                    self.provider
                )
            else:
                raise Exception("Empty synthesis generation")
            
        except Exception as e:
            print(f"Research synthesis generation failed: {e}")
            fallback_lines = [
                "### Deep Research Synthesis (Rate-Limited Fallback)\n",
                "Due to Gemini API rate limits on the free tier, a fully generated summary could not be retrieved. "
                "However, the autonomous pipeline successfully crawled and analyzed the following evidence from official sources:\n"
            ]
            citations = []
            # Create fallback citations for top 4 evidences
            for idx, ev in enumerate(evidences[:4]):
                cit_id = idx + 1
                fallback_lines.append(f"- **[{cit_id}]** {ev.text[:220]}... *(Source: {ev.url})*")
                
                from backend.llm.models import Citation
                citations.append(Citation(
                    id=cit_id,
                    chunk_id=ev.chunk_id,
                    url=ev.url,
                    domain=ev.domain
                ))
            validated_text = "\n".join(fallback_lines)
            grounded = True
            
        generation_time = int((time.time() - start_time) * 1000)
        
        return GeneratedAnswer(
            query=query,
            search_id=search_id,
            answer=validated_text,
            citations=citations,
            grounded=grounded,
            model=settings.GEMINI_MODEL,
            generation_time_ms=generation_time
        )
