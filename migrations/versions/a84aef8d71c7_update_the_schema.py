"""update the schema

Revision ID: a84aef8d71c7
Revises: 205f13854aa3
Create Date: 2026-01-26 16:10:24.392510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a84aef8d71c7'
down_revision: Union[str, Sequence[str], None] = '205f13854aa3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Create enum types FIRST before using them in columns
    # Check if they exist first to avoid errors on re-run
    
    # Create PaymentAccountType enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentaccounttype AS ENUM ('CASH', 'BANK', 'JAZZCASH', 'EASYPAISA');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create PaymentType enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymenttype AS ENUM ('FULL', 'PARTIAL', 'UN_PAID');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create InvoiceStatus enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE invoicestatus AS ENUM ('UNPAID', 'PARTIAL', 'PAID');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Now alter the columns to use the enum types
    # For payment_accounts.type - convert VARCHAR to ENUM
    op.execute("""
        ALTER TABLE payment_accounts 
        ALTER COLUMN type TYPE paymentaccounttype 
        USING type::paymentaccounttype
    """)
    
    # Add new columns
    op.add_column('payments', sa.Column('payment_type', 
                                        postgresql.ENUM('FULL', 'PARTIAL', 'UN_PAID', name='paymenttype'), 
                                        nullable=False,
                                        server_default='UN_PAID'))  # Add default to avoid NOT NULL constraint error
    
    op.add_column('purchase_invoices', sa.Column('paid_amount', sa.Numeric(precision=15, scale=2), 
                                                  nullable=True, server_default='0.00'))
    op.add_column('purchase_invoices', sa.Column('balance_due', sa.Numeric(precision=15, scale=2), 
                                                  nullable=False, server_default='0.00'))
    op.add_column('purchase_invoices', sa.Column('payment_status', 
                                                  postgresql.ENUM('UNPAID', 'PARTIAL', 'PAID', name='invoicestatus'), 
                                                  nullable=True, server_default='UNPAID'))
    
    op.add_column('sale_invoices', sa.Column('recieved_amount', sa.Numeric(precision=15, scale=2), 
                                             nullable=True, server_default='0.00'))
    op.add_column('sale_invoices', sa.Column('balance_due', sa.Numeric(precision=15, scale=2), 
                                             nullable=False, server_default='0.00'))
    op.add_column('sale_invoices', sa.Column('payment_status', 
                                             postgresql.ENUM('UNPAID', 'PARTIAL', 'PAID', name='invoicestatus'), 
                                             nullable=True, server_default='UNPAID'))
    
    # Remove server defaults after setting initial values (optional but cleaner)
    op.alter_column('payments', 'payment_type', server_default=None)
    op.alter_column('purchase_invoices', 'paid_amount', server_default=None)
    op.alter_column('purchase_invoices', 'balance_due', server_default=None)
    op.alter_column('purchase_invoices', 'payment_status', server_default=None)
    op.alter_column('sale_invoices', 'recieved_amount', server_default=None)
    op.alter_column('sale_invoices', 'balance_due', server_default=None)
    op.alter_column('sale_invoices', 'payment_status', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    
    # Drop columns
    op.drop_column('sale_invoices', 'payment_status')
    op.drop_column('sale_invoices', 'balance_due')
    op.drop_column('sale_invoices', 'recieved_amount')
    op.drop_column('purchase_invoices', 'payment_status')
    op.drop_column('purchase_invoices', 'balance_due')
    op.drop_column('purchase_invoices', 'paid_amount')
    op.drop_column('payments', 'payment_type')
    
    # Convert enum back to VARCHAR
    op.execute("""
        ALTER TABLE payment_accounts 
        ALTER COLUMN type TYPE VARCHAR(20) 
        USING type::text
    """)
    
    # Drop the enum types
    op.execute('DROP TYPE IF EXISTS invoicestatus')
    op.execute('DROP TYPE IF EXISTS paymenttype')
    op.execute('DROP TYPE IF EXISTS paymentaccounttype')