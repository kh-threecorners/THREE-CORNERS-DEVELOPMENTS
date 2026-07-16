"""Runs BEFORE the ORM's _auto_init, which is where a broken upgrade otherwise dies.

An earlier iteration of this feature shipped link fields (property_id / project /
sale_order_id ...) as *text* columns, and invoice code wrote installment line names
("Periodic Installment 1", ...) into them. This version defines those fields as Many2one
(integer) columns, so _auto_init tries to cast that text to integer and raises:

    invalid input syntax for type integer: "Periodic Installment 1"

Any pre-existing column of the wrong type here holds data that cannot belong to a
Many2one and is discarded — the real links are rebuilt in post-migrate.py from the
sale order / installment / rental relations. So we simply drop the incompatible column
and let _auto_init recreate it clean. Columns already stored as integer are left alone.

The exact same script ships in `real_estate_management` (an earlier-loaded dependency)
so the columns are sanitised no matter which module the upgrade is triggered from.
"""
import logging

from odoo.tools import sql

_logger = logging.getLogger(__name__)

# Columns (table, column) that this feature defines as Many2one. If any already exists
# as a non-integer type it is a leftover from an older definition and must go before
# _auto_init tries to cast it.
_MANY2ONE_COLUMNS = [
    ('account_move', 'property_id'),
    ('account_move', 'property_project_id'),
    ('account_move', 'sale_order_id'),
    ('sale_order', 'property_id'),
    ('product_template', 'property_project_id'),
    ('product_product', 'property_project_id'),
]


def _sanitize_many2one_columns(cr):
    for table, column in _MANY2ONE_COLUMNS:
        if not sql.table_exists(cr, table):
            continue

        # Look at the column in the connection's own schema only.
        cr.execute(
            """
            SELECT data_type
              FROM information_schema.columns
             WHERE table_schema = current_schema()
               AND table_name = %s
               AND column_name = %s
            """,
            (table, column),
        )
        row = cr.fetchone()
        if not row:
            continue  # column absent -> _auto_init will create it as integer

        if row[0] in ('integer', 'bigint'):
            continue  # already the right shape; leave it and its data untouched

        # A non-integer column can only hold data incompatible with a Many2one.
        cr.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL')
        non_null = cr.fetchone()[0]
        _logger.warning(
            "pre-migrate: dropping %s.%s (type=%s, %s non-null rows) so it can be "
            "recreated as a Many2one; links are rebuilt in post-migrate.",
            table, column, row[0], non_null,
        )
        # Drop any DB views built on the column first, or the DROP COLUMN is refused.
        sql.drop_depending_views(cr, table, column)
        cr.execute(f'ALTER TABLE "{table}" DROP COLUMN "{column}"')


def migrate(cr, version):
    if not version:
        return
    _sanitize_many2one_columns(cr)
