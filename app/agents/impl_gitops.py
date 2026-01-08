from pathlib import Path
from git import Repo
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage

class GitOpsAgent(BaseAgent):
    stage = JobStage.CREATE_PR

    def run(self, job, ws):
        repo = Repo(ws.target_dir)
        branch_name = f"base44-migration/{job.id[:8]}"
        try:
            if branch_name not in [h.name for h in repo.heads]:
                repo.git.checkout("-b", branch_name)
            else:
                repo.git.checkout(branch_name)

            repo.git.add(all=True)
            if repo.is_dirty(untracked_files=True):
                repo.index.commit(f"Base44 migration scaffold for job {job.id}")
            else:
                return AgentResult(self.stage, True, "No changes to commit", {"branch": branch_name, "pushed": False})

            note = Path(ws.artifacts_dir) / "gitops.md"
            note.write_text(
                "# GitOps\n\n"
                f"- Local branch created: `{branch_name}`\n"
                "- TODO: push branch and open PR via GitHub App/PAT\n",
                encoding="utf-8"
            )
            return AgentResult(self.stage, True, "Committed locally (push/PR TODO)", {
                "branch": branch_name,
                "pushed": False,
                "gitops_note": str(note.relative_to(ws.root)),
            })
        except Exception as e:
            return AgentResult(self.stage, False, f"GitOps failed: {e}", {})
