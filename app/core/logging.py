import logging
import sys


class ContextFormatter(logging.Formatter):
    """Custom formatter that handles optional job_id and stage fields."""
    def format(self, record):
        # Add default values for job_id and stage if not present
        if not hasattr(record, 'job_id'):
            record.job_id = '-'
        if not hasattr(record, 'stage'):
            record.stage = '-'
        return super().format(record)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ContextFormatter(
        "%(asctime)s %(levelname)s %(name)s [job_id=%(job_id)s stage=%(stage)s] - %(message)s"
    ))
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
    )
