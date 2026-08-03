"""Seed the new Down Payment account setting from the account that used to be
hardcoded in action_create_installment_invoices_from_so.

Before this version, down payment invoice lines were forced onto the account
literally named 'دفعات حجز من العملاء'. That lookup is now a company setting, so
copy the old account over to keep existing databases behaving the same. Companies
that already have the setting filled are left untouched.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

LEGACY_DOWN_PAYMENT_ACCOUNT_NAME = 'دفعات حجز من العملاء'


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

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
