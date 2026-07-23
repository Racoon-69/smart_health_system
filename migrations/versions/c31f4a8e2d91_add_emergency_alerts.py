"""add emergency alert recipients and delivery records

Revision ID: c31f4a8e2d91
Revises: 94e1d3c7b2a8
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "c31f4a8e2d91"
down_revision = "94e1d3c7b2a8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("patient_profiles") as batch_op:
        batch_op.add_column(sa.Column("family_contact_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("family_contact_phone", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("family_contact_relationship", sa.String(length=60), nullable=True))
    with op.batch_alter_table("doctor_profiles") as batch_op:
        batch_op.add_column(sa.Column("sms_phone", sa.String(length=30), nullable=True))

    op.create_table(
        "emergency_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("idempotency_key", sa.String(length=140), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctor_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    with op.batch_alter_table("emergency_alerts") as batch_op:
        batch_op.create_index("ix_emergency_alerts_public_id", ["public_id"], unique=True)
        batch_op.create_index("ix_emergency_alerts_patient_id", ["patient_id"], unique=False)
        batch_op.create_index("ix_emergency_alerts_doctor_id", ["doctor_id"], unique=False)

    op.create_table(
        "emergency_alert_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("recipient_type", sa.String(length=20), nullable=False),
        sa.Column("recipient_name", sa.String(length=120), nullable=False),
        sa.Column("recipient_phone", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider_message_id", sa.String(length=150), nullable=True),
        sa.Column("error_message", sa.String(length=300), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["emergency_alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("emergency_alert_deliveries") as batch_op:
        batch_op.create_index("ix_emergency_alert_deliveries_alert_id", ["alert_id"], unique=False)


def downgrade():
    op.drop_table("emergency_alert_deliveries")
    op.drop_table("emergency_alerts")
    with op.batch_alter_table("doctor_profiles") as batch_op:
        batch_op.drop_column("sms_phone")
    with op.batch_alter_table("patient_profiles") as batch_op:
        batch_op.drop_column("family_contact_relationship")
        batch_op.drop_column("family_contact_phone")
        batch_op.drop_column("family_contact_name")