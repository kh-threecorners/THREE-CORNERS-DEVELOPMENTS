"""Runs BEFORE the ORM's _auto_init, which is where a broken upgrade otherwise dies.

Earlier iterations of this feature shipped link fields (property_id / project /
sale_order_id / the installment links ...) as *text* columns, and invoice code wrote
installment line names ("Periodic Installment 1", ...) into them. This version defines
those fields as Many2one (integer) columns, so _auto_init tries to cast the text to
integer and raises:

    invalid input syntax for type integer: "Periodic Installment 1"

The crash can happen during the _auto_init of whichever module in the dependency chain
re-inits the affected model first, so the identical script ships in BOTH
`real_estate_management` and `px_custom_real_estate_management`.

Strategy: for the tables this feature owns/extends, drop any column that this feature
defines as a Many2one but that is still physically stored as text. A Many2one is never
legitimately a text column, so such a column is always a leftover from an older Char
definition; its contents cannot be a valid foreign key. Dropping it (rather than trying
to cast/clean it) also avoids the follow-up failure where a surviving integer-looking
value ("42") is a dangling id that breaks the Many2one's FK constraint. _auto_init then
recreates the column clean and post-migrate.py rebuilds the real links.

Only the exact set of columns this feature declares as Many2one is touched (see
_LINK_COLUMNS), so legitimate Char fields that merely end in "_id" — e.g.
property.sale.partner_state_id, crm.lead.reveal_id, Studio x_..._id — are left alone.
"""
import logging

from odoo.tools import sql

_logger = logging.getLogger(__name__)

# Cross-cutting tables (outside the property_* namespace) this feature defines Many2one
# link fields on. property_* tables are discovered dynamically.
_EXTRA_TABLES = (
    'account_move',
    'account_move_line',
    'sale_order',
    'sale_order_line',
    'sale_order_installment_line',
    'payment_installment_line',
    'crm_lead',
    'crm_lead_installment',
    'product_template',
    'product_product',
    'bank_tag',
    'rental_bill',
)

# Every column this feature (px_custom + real_estate) declares as a Many2one. Deliberately
# excludes the res.partner / res.company / res.users / res.currency links (always integer,
# never at risk) and — importantly — any name that is a legitimate Char somewhere
# (partner_state_id). Keep this in sync with the Many2one fields in both modules' models.
_LINK_COLUMNS = frozenset({
    'auction_id',
    'commission_plan_id',
    'customer_cheque_bank_id',
    'external_commission_plan_id',
    'installment_id',
    'internal_commission_plan_id',
    'invoice_id',
    'late_fee_move_line_id',
    'lead_id',
    'payment_id',
    'payment_plane_id',
    'payment_plan_id',
    'product_id',
    'project_id',
    'property_id',
    'property_installment_id',
    'property_order_id',
    'property_product_id',
    'property_project_id',
    'property_rental_id',
    'property_sale_id',
    'rental_id',
    'rep_rental_id',
    'sale_id',
    'sale_order_id',
    'sale_order_installment_id',
    'selected_payment_plan_id',
    'uom_id',
})

# Anything that is not already an integer: varchar/text, but also jsonb (what an old
# Char(translate=True) leaves behind — the ORM casts it via ->>'en_US' and raises the
# same InvalidTextRepresentation).
_NON_INTEGER_TYPES = ('integer', 'bigint')


def _feature_tables(cr):
    cr.execute(
        r"""
        SELECT table_name
          FROM information_schema.tables
         WHERE table_schema = current_schema()
           AND table_type = 'BASE TABLE'
           AND (table_name LIKE 'property\_%%' OR table_name = ANY(%s))
        """,
        (list(_EXTRA_TABLES),),
    )
    return [row[0] for row in cr.fetchall()]


def _text_link_columns(cr, table):
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = %s
           AND NOT (data_type = ANY(%s))
        """,
        (table, list(_NON_INTEGER_TYPES)),
    )
    return [name for (name,) in cr.fetchall() if name in _LINK_COLUMNS]


def _drop_text_many2one_columns(cr):
    for table in _feature_tables(cr):
        for column in _text_link_columns(cr, table):
            cr.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL')
            non_null = cr.fetchone()[0]
            _logger.warning(
                "pre-migrate: dropping text column %s.%s (%s non-null rows) — a Many2one "
                "stored as text is a broken leftover; it is recreated as an integer column "
                "and links are rebuilt in post-migrate.",
                table, column, non_null,
            )
            # Drop any DB views built on the column first, or the DROP COLUMN is refused.
            sql.drop_depending_views(cr, table, column)
            cr.execute(f'ALTER TABLE "{table}" DROP COLUMN "{column}"')


def migrate(cr, version):
    if not version:
        return
    _drop_text_many2one_columns(cr)
