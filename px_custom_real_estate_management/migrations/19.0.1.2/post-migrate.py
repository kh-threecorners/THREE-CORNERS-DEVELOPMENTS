"""Installment accounts configuration + Invoice Analysis by installment type.

1. Seed the new Down Payment account setting from the account that used to be
   hardcoded in action_create_installment_invoices_from_so. Before this version,
   down payment invoice lines were forced onto the account literally named
   'دفعات حجز من العملاء'. That lookup is now a company setting, so copy the old
   account over to keep existing databases behaving the same.
2. Backfill `installment_type` on the lines of invoices that were generated
   before the field existed, so Invoice Analysis can group historical invoices
   by installment type instead of showing them all as "None".

Both steps only fill what is still empty, so the script is safe to re-run.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

LEGACY_DOWN_PAYMENT_ACCOUNT_NAME = 'دفعات حجز من العملاء'


def _seed_down_payment_account(env):
    for company in env['res.company'].search([]):
        if company.installment_down_payment_account_id:
            continue
        account = env['account.account'].with_company(company).search([
            ('name', '=', LEGACY_DOWN_PAYMENT_ACCOUNT_NAME),
        ], limit=1)
        if not account:
            continue
        company.installment_down_payment_account_id = account.id
        _logger.info(
            "Seeded the Down Payment installment account of %s with %s.",
            company.name, account.display_name,
        )


def _backfill_installment_types(env):
    """Stamp the type on the product lines of existing installment invoices.

    SO installment invoices carry the schedule line and can be read straight off
    its `line_type`; CRM-path invoices only have a description, which the same
    helper that runs at invoice creation knows how to interpret.
    """
    Company = env['res.company']
    lines = env['account.move.line'].search([
        ('installment_type', '=', False),
        ('display_type', '=', 'product'),
        '|',
        ('move_id.sale_order_installment_id', '!=', False),
        ('move_id.installment_id', '!=', False),
    ])

    by_type = {}
    for line in lines:
        schedule_line = line.move_id.sale_order_installment_id
        installment_type = Company._resolve_installment_type(
            line_type=schedule_line.line_type if schedule_line else False,
            name=line.name or line.move_id.installment_id.name,
        )
        if installment_type:
            by_type.setdefault(installment_type, env['account.move.line'])
            by_type[installment_type] |= line

    for installment_type, typed_lines in by_type.items():
        typed_lines.write({'installment_type': installment_type})
        _logger.info(
            "Backfill: stamped %s invoice lines as %s.", len(typed_lines), installment_type,
        )

    unresolved = len(lines) - sum(len(v) for v in by_type.values())
    if unresolved:
        _logger.info(
            "Backfill: %s installment invoice lines could not be typed from their "
            "description and were left empty.", unresolved,
        )


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    _seed_down_payment_account(env)
    _backfill_installment_types(env)
