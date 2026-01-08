"""create migration_jobs table

Revision ID: 0001
Revises:
Create Date: 2026-01-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "migration_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("source_repo_url", sa.Text(), nullable=False),
        sa.Column("target_repo_url", sa.Text(), nullable=False),
        sa.Column("backend_stack", sa.String(length=20), nullable=False),
        sa.Column("db_stack", sa.String(length=20), nullable=False),
        sa.Column("commit_mode", sa.String(length=20), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("artifacts", sa.JSON(), nullable=False),
    )

def downgrade():
    op.drop_table("migration_jobs")
