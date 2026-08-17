"""Production schema alignment v1
Revision ID: a1c9554f9b9c
Revises: None
Create Date: 2026-08-17 16:10:40.467789
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1c9554f9b9c'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. Handle 'sources' table (Add missing columns to existing table)
    # We use a try/except block so it doesn't fail if columns already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'sources' not in tables:
        op.create_table('sources',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('feed_url', sa.String(length=500), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('feed_url')
        )
    
    # 2. Handle 'articles' table - Adding the missing source_id and content_hash
    if 'articles' in tables:
        columns = [c['name'] for c in inspector.get_columns('articles')]
        if 'source_id' not in columns:
            op.add_column('articles', sa.Column('source_id', sa.Integer(), nullable=True))
        if 'content_hash' not in columns:
            op.add_column('articles', sa.Column('content_hash', sa.String(length=64), nullable=True))
        if 'source_name' not in columns:
            op.add_column('articles', sa.Column('source_name', sa.String(length=100), nullable=True))
    else:
        op.create_table('articles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=500), nullable=False),
            sa.Column('article_url', sa.String(length=500), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('article_url')
        )

    # 3. Create 'library' table if it doesn't exist
    if 'library' not in tables:
        op.create_table('library',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('article_id', sa.Integer(), nullable=True),
            sa.Column('saved_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('article_id')
        )

def downgrade():
    pass
