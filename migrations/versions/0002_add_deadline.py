"""Add task deadline for overdue task reporting.

Revision ID: 0002_add_deadline
Revises: 0001_initial
Create Date: 2026-11-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_deadline"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("deadline", sa.Date(), nullable=True))
    op.create_index("ix_tasks_assigned_deadline", "tasks", ["assigned_to", "deadline"])


def downgrade() -> None:
    op.drop_index("ix_tasks_assigned_deadline", table_name="tasks")
    op.drop_column("tasks", "deadline")
