"""add persistent AI conversations and login activity

Revision ID: 94e1d3c7b2a8
Revises: 36725bd94ff0
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "94e1d3c7b2a8"
down_revision = "36725bd94ff0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("report_analysis_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_analysis_id"], ["report_analyses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    with op.batch_alter_table("ai_conversations") as batch_op:
        batch_op.create_index(batch_op.f("ix_ai_conversations_patient_id"), ["patient_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ai_conversations_public_id"), ["public_id"], unique=True)

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_role", sa.String(length=20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_messages") as batch_op:
        batch_op.create_index(batch_op.f("ix_ai_messages_conversation_id"), ["conversation_id"], unique=False)

    op.create_table(
        "login_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("login_activities") as batch_op:
        batch_op.create_index(batch_op.f("ix_login_activities_email"), ["email"], unique=False)
        batch_op.create_index(batch_op.f("ix_login_activities_occurred_at"), ["occurred_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_login_activities_user_id"), ["user_id"], unique=False)


def downgrade():
    op.drop_table("login_activities")
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
