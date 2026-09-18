"""Store reviewed labels and gallery embeddings.

Revision ID: 73c48bf0ad22
Revises: c95c4ece6697
"""
from alembic import op
import sqlalchemy as sa

revision = "73c48bf0ad22"
down_revision = "c95c4ece6697"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "jewel_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.id"), nullable=False),
        sa.Column("instance_number", sa.Integer(), nullable=False),
        sa.Column("predicted_label", sa.String(100), nullable=False),
        sa.Column("confirmed_label", sa.String(100), nullable=False),
        sa.Column("embedding", sa.LargeBinary(), nullable=False),
        sa.Column("confirmed_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "instance_number"),
    )
    op.create_index("ix_jewel_confirmations_job_id", "jewel_confirmations", ["job_id"])


def downgrade():
    op.drop_index("ix_jewel_confirmations_job_id", table_name="jewel_confirmations")
    op.drop_table("jewel_confirmations")
