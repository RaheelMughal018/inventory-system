from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7a86fb82c723'
down_revision = '5739863d2213'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Rename old enum
    op.execute("ALTER TYPE itemtype RENAME TO itemtype_old;")
    
    # 2. Create new enum with uppercase values
    op.execute("CREATE TYPE itemtype AS ENUM ('RAW_MATERIAL', 'FINAL_PRODUCT');")
    
    # 3. Alter items.type column to use the new enum, mapping old values
    op.execute("""
        ALTER TABLE items
        ALTER COLUMN type TYPE itemtype
        USING
            CASE type::text
                WHEN 'raw_material' THEN 'RAW_MATERIAL'
                WHEN 'final_product' THEN 'FINAL_PRODUCT'
            END::itemtype;
    """)
    
    # 4. Drop old enum
    op.execute("DROP TYPE itemtype_old;")


def downgrade():
    # 1. Rename current enum
    op.execute("ALTER TYPE itemtype RENAME TO itemtype_new;")
    
    # 2. Recreate old lowercase enum
    op.execute("CREATE TYPE itemtype AS ENUM ('raw_material', 'final_product');")
    
    # 3. Alter items.type back to old enum
    op.execute("""
        ALTER TABLE items
        ALTER COLUMN type TYPE itemtype
        USING
            CASE type::text
                WHEN 'RAW_MATERIAL' THEN 'raw_material'
                WHEN 'FINAL_PRODUCT' THEN 'final_product'
            END::itemtype;
    """)
    
    # 4. Drop temporary new enum
    op.execute("DROP TYPE itemtype_new;")
