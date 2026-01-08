from dataclasses import dataclass
from enum import Enum

class JobStage(str, Enum):
    CLONE_SOURCE = "CLONE_SOURCE"
    CLONE_TARGET = "CLONE_TARGET"
    INTAKE_UI_CONTRACT = "INTAKE_UI_CONTRACT"
    DESIGN_DB_SCHEMA = "DESIGN_DB_SCHEMA"
    DESIGN_API = "DESIGN_API"
    GENERATE_BACKEND = "GENERATE_BACKEND"
    ADD_ASYNC = "ADD_ASYNC"
    WIRE_FRONTEND = "WIRE_FRONTEND"
    VERIFY = "VERIFY"
    CREATE_PR = "CREATE_PR"
    DONE = "DONE"
    FAILED = "FAILED"

@dataclass(frozen=True)
class StageResult:
    stage: JobStage
    ok: bool
    message: str
    artifacts: list[str]
