# -*- coding: utf-8 -*-
from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Safety net: after the installment invoices are generated, make sure
    # any invoice still in DRAFT carries the right dates. The real work is
    # normally done at creation time in account.move.create (see
    # account_move.py); this only re-aligns anything that was linked to its
    # installment line AFTER creation.
    # ------------------------------------------------------------------
    def _sync_installment_invoice_dates(self):
        for order in self:
            if not order.date_order:
                continue
            so_date = fields.Date.to_date(order.date_order)

            invoices = self.env['account.move'].search([
                ('sale_order_id', '=', order.id),
                ('sale_order_installment_id', '!=', False),
                ('state', '=', 'draft'),  # never rewrite posted entries
            ])
            for inv in invoices:
                new_vals = {}
                due = inv.sale_order_installment_id.collection_date
                if inv.invoice_date != so_date:
                    new_vals['invoice_date'] = so_date
                if due and inv.invoice_date_due != due:
                    new_vals['invoice_date_due'] = due
                if new_vals:
                    inv.write(new_vals)
                    _logger.info(
                        "Installment date fix: %s -> invoice_date=%s, due=%s",
                        inv.name or inv.id,
                        new_vals.get('invoice_date', inv.invoice_date),
                        new_vals.get('invoice_date_due', inv.invoice_date_due),
                    )

    def action_create_installment_invoices(self):
        res = super().action_create_installment_invoices()
        self._sync_installment_invoice_dates()
        return res

    def action_create_installment_invoices_from_so(self):
        res = super().action_create_installment_invoices_from_so()
        self._sync_installment_invoice_dates()
        return res

    # ------------------------------------------------------------------
    # One-off maintenance: re-align every DRAFT installment invoice in the
    # database. Safe to run manually (used by the server action shipped in
    # data/fix_dates_action.xml). Posted invoices are left untouched.
    # ------------------------------------------------------------------
    def action_fix_all_draft_installment_invoice_dates(self):
        orders = self.env['account.move'].search([
            ('sale_order_installment_id', '!=', False),
            ('state', '=', 'draft'),
        ]).mapped('sale_order_id')
        if orders:
            orders._sync_installment_invoice_dates()
        return True
