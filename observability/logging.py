"""structlog setup with JSON rendering and trace context."""
import sys
import structlog


def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger():
    return structlog.get_logger()


def bind_trace_id(trace_id: str):
    structlog.contextvars.bind_contextvars(trace_id=trace_id)


def clear_trace_context():
    structlog.contextvars.clear_contextvars()
