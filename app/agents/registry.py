from dataclasses import dataclass
from typing import Dict
from app.core.workflow import JobStage
from app.agents.base import BaseAgent
from app.agents.impl_clone import CloneSourceAgent, CloneTargetAgent
from app.agents.impl_intake import RepoIntakeAgent
from app.agents.impl_design import DomainModelerAgent, ApiDesignerAgent
from app.agents.impl_build import BackendBuilderAgent, AsyncArchitectAgent, FrontendWiringAgent, VerificationAgent
from app.agents.impl_gitops import GitOpsAgent

@dataclass
class AgentRegistry:
    mapping: Dict[JobStage, BaseAgent]

    def get(self, stage: JobStage) -> BaseAgent:
        return self.mapping[stage]

    @staticmethod
    def default() -> "AgentRegistry":
        return AgentRegistry(mapping={
            JobStage.CLONE_SOURCE: CloneSourceAgent(),
            JobStage.CLONE_TARGET: CloneTargetAgent(),
            JobStage.INTAKE_UI_CONTRACT: RepoIntakeAgent(),
            JobStage.DESIGN_DB_SCHEMA: DomainModelerAgent(),
            JobStage.DESIGN_API: ApiDesignerAgent(),
            JobStage.GENERATE_BACKEND: BackendBuilderAgent(),
            JobStage.ADD_ASYNC: AsyncArchitectAgent(),
            JobStage.WIRE_FRONTEND: FrontendWiringAgent(),
            JobStage.VERIFY: VerificationAgent(),
            JobStage.CREATE_PR: GitOpsAgent(),
        })
