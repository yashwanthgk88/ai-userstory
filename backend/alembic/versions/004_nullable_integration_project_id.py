"""make integration project_id nullable and add jira_project_key to projects

Revision ID: 004
Revises: 003
Create Date: 2026-01-28
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    # Make project_id nullable to support global (user-level) integrations
    op.alter_column(
        "integrations",
        "project_id",
        existing_type=sa.dialects.postgresql.UUID(),
        nullable=True,
    )

    # Add jira_project_key column to projects table
    op.add_column(
        "projects",
        sa.Column("jira_project_key", sa.String(50), nullable=True, index=True),
    )


def downgrade():
    # Remove jira_project_key column
    op.drop_column("projects", "jira_project_key")

    # Note: This will fail if there are any rows with NULL project_id
    op.alter_column(
        "integrations",
        "project_id",
        existing_type=sa.dialects.postgresql.UUID(),
        nullable=False,
    )
