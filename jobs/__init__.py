from nautobot.extras.jobs import register_jobs
from .generate_records import GenerateRecords

register_jobs(GenerateRecords)

__all__ = ["GenerateRecords"] 