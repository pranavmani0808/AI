import contextvars
import time
from contextlib import contextmanager
from typing import Optional
from backend.observability.models import ObservabilityMetrics

# Request-scoped container for request/research metrics
_metrics_context = contextvars.ContextVar("metrics_context", default=None)

def get_current_metrics() -> Optional[ObservabilityMetrics]:
    """Retrieves current request metrics instance."""
    return _metrics_context.get()

def start_metrics_tracking(query: str, request_id: str) -> ObservabilityMetrics:
    """Initializes and registers metrics tracking for the current context."""
    metrics = ObservabilityMetrics(request_id=request_id, query=query, status="running")
    _metrics_context.set(metrics)
    return metrics

@contextmanager
def track_stage_duration(stage_attr: str):
    """
    Context manager tracking real monotonic execution times in milliseconds.
    Updates the context-local metrics instance dynamically.
    """
    metrics = get_current_metrics()
    if not metrics:
        yield
        return
        
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        # Ensure timings model gets updated
        setattr(metrics.timings, stage_attr, duration_ms)
