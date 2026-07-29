"""Fix non-int Run.distance_millimeters

Revision ID: 809b91667a60
Revises: 544772e43962
Create Date: 2026-07-29 11:13:48.404268

"""

from typing import Sequence, Union

from alembic import op

# For custom TypeAnnotations


# revision identifiers, used by Alembic.
revision: str = "809b91667a60"
down_revision: Union[str, Sequence[str], None] = "544772e43962"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE run SET distance_millimeters = CAST(ROUND(distance_millimeters) AS INTEGER)")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
