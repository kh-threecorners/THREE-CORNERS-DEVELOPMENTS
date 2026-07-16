"""Runs BEFORE the ORM's _auto_init, which is where a broken upgrade otherwise dies.

An earlier iteration of this feature shipped `account.move.property_id` (and possibly
the sibling links) as a *text* column, and invoice code wrote installment line names
("Periodic Installment 1", ...) into it. This version redefines those fields as Many2one
(integer) columns, so _auto_init tries to cast that text to integer and raises:

    invalid input syntax for type integer: "Periodic Installment 1"

Any pre-existing column of the wrong type here holds data that cannot belong to a
Many2one and is discarded — the real links are rebuilt in post-migrate.py from the
sale order / installment / rental relations. So we simply drop the incompatible column
and let _auto_init recreate it clean. Columns already stored as integer are left alone.
"""
import logging

_logger = logging.getLogger(__name__)

# Columns this version (re)defines as Many2one. If any already exists as a non-integer
# type, it is a leftover from an older definition and must go before _auto_init.
_MANY2ONE_COLUMNS = [
    ('account_move', 'property_id'),
    ('account_move', 'property_project_id'),
    ('account_move', 'sale_order_id'),
    ('sale_order', 'property_id'),
    ('product_template', 'property_project_id'),
    ('product_product', 'property_project_id'),
]


def migrate(cr, version):
    if not version:
        return

    for table, column in _MANY2ONE_COLUMNS:
        cr.execute(
            """
            SELECT data_type
              FROM information_schema.columns
             WHERE table_name = %s AND column_name = %s
            """,
            (table, column),
        )
        row = cr.fetchone()
        if not row:
            continue  # column does not exist yet -> _auto_init will create it as integer

        data_type = row[0]
        if data_type in ('integer', 'bigint'):
            continue  # already the right shape, leave it and its data untouched

        # Non-integer column can only hold data incompatible with a Many2one. Log a
        # sample for the record, then drop it so _auto_init recreates it as integer.
        cr.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL')
        non_null = cr.fetchone()[0]
        _logger.warning(
            "pre-migrate: dropping %s.%s (type=%s, %s non-null rows) so it can be "
            "recreated as a Many2one; links are rebuilt in post-migrate.",
            table, column, data_type, non_null,
        )
        cr.execute(f'ALTER TABLE "{table}" DROP COLUMN "{column}"')
