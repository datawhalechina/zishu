"""add brain

Revision ID: c5804d64794b
Revises: 92495b2168af
Create Date: 2022-08-20 15:27:22.607094

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5804d64794b'
down_revision = '92495b2168af'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('brainitem',
    sa.Column('itid', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('graphid', sa.String(length=32), nullable=True),
    sa.Column('graphtopic', sa.String(length=256), nullable=True),
    sa.Column('parentid', sa.String(length=32), nullable=True),
    sa.Column('parenttopic', sa.String(length=256), nullable=True),
    sa.Column('itemid', sa.String(length=32), nullable=True),
    sa.Column('itemtopic', sa.String(length=256), nullable=True),
    sa.Column('childrenid', sa.TEXT(), nullable=True),
    sa.Column('childrentopic', sa.TEXT(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=False),
    sa.Column('edit_time', sa.DateTime(), nullable=True),
    sa.Column('hidden', sa.Integer(), nullable=True),
    sa.Column('hidden_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('itid')
    )
    op.create_table('brainmap',
    sa.Column('mapid', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('root_id', sa.String(length=32), nullable=True),
    sa.Column('root_topic', sa.String(length=256), nullable=True),
    sa.Column('mapdata', sa.TEXT(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=False),
    sa.Column('edit_time', sa.DateTime(), nullable=True),
    sa.Column('hidden', sa.Integer(), nullable=True),
    sa.Column('hidden_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('mapid')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('brainmap')
    op.drop_table('brainitem')
    # ### end Alembic commands ###