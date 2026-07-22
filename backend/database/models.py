from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    result_count = Column(Integer, default=0, nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)

class CrawlResult(Base):
    __tablename__ = "crawl_results"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("search_queries.id", ondelete="SET NULL"), nullable=True, index=True)
    url = Column(Text, nullable=False)
    title = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)
    crawl_status = Column(String(50), nullable=False) # SUCCESS, EMPTY, TOO_SHORT, BLOCKED, TIMEOUT, etc.
    word_count = Column(Integer, default=0, nullable=False)
    extracted_text = Column(Text, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class GeneratedAnswerModel(Base):
    __tablename__ = "generated_answers"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("search_queries.id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    generation_time_ms = Column(Integer, default=0, nullable=False)
    grounded = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ResearchSessionModel(Base):
    __tablename__ = "research_sessions"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    status = Column(String(50), default="running", nullable=False)
    iterations = Column(Integer, default=0, nullable=False)
    coverage_score = Column(Float, default=0.0, nullable=False)
    sources_analyzed = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)


class ResearchSubqueryModel(Base):
    __tablename__ = "research_subqueries"

    id = Column(Integer, primary_key=True, index=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(Text, nullable=False)
    purpose = Column(Text, nullable=True)
    priority = Column(String(20), default="medium", nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    iteration = Column(Integer, default=1, nullable=False)


class ResearchSourceModel(Base):
    __tablename__ = "research_sources"

    id = Column(Integer, primary_key=True, index=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    subquery_id = Column(Integer, ForeignKey("research_subqueries.id", ondelete="SET NULL"), nullable=True)
    url = Column(Text, nullable=False)
    domain = Column(String(200), nullable=True)
    authority_score = Column(Float, default=0.0, nullable=False)
    relevance_score = Column(Float, default=0.0, nullable=False)
    freshness_score = Column(Float, default=0.0, nullable=False)
    overall_score = Column(Float, default=0.0, nullable=False)


class ResearchContradictionModel(Base):
    __tablename__ = "research_contradictions"

    id = Column(Integer, primary_key=True, index=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String(200), nullable=False)
    claim_a = Column(Text, nullable=False)
    source_a_url = Column(Text, nullable=False)
    claim_b = Column(Text, nullable=False)
    source_b_url = Column(Text, nullable=False)
    severity = Column(String(50), default="low", nullable=False)


class RequestMetricsModel(Base):
    __tablename__ = "request_metrics"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), nullable=False, unique=True, index=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    query = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)
    total_duration_ms = Column(Integer, default=0, nullable=False)
    search_duration_ms = Column(Integer, default=0, nullable=False)
    crawl_duration_ms = Column(Integer, default=0, nullable=False)
    rag_duration_ms = Column(Integer, default=0, nullable=False)
    generation_duration_ms = Column(Integer, default=0, nullable=False)
    sources_analyzed = Column(Integer, default=0, nullable=False)
    coverage_score = Column(Float, default=0.0, nullable=False)
    citation_count = Column(Integer, default=0, nullable=False)
    error_code = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    total_cases = Column(Integer, nullable=False)
    passed = Column(Integer, nullable=False)
    failed = Column(Integer, nullable=False)
    average_latency_ms = Column(Integer, nullable=False)


class ResearchConversation(Base):
    __tablename__ = "research_conversations"

    id = Column(Integer, primary_key=True, index=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ResearchMessage(Base):
    __tablename__ = "research_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("research_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # system, user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MessageEvidence(Base):
    __tablename__ = "message_evidence"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("research_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(200), nullable=False)
    citation_id = Column(Integer, nullable=True)


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WorkspaceResearch(Base):
    __tablename__ = "workspace_research"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "research_id", name="uq_workspace_research"),
    )


class ResearchNote(Base):
    __tablename__ = "research_notes"

    id = Column(Integer, primary_key=True, index=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SavedSource(Base):
    __tablename__ = "saved_sources"

    id = Column(Integer, primary_key=True, index=True)
    research_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
