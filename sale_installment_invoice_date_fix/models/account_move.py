# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Core fix: set the correct dates the moment an installment invoice
    # is created (before it gets posted by the generation method).
    #
    #   invoice_date      -> Sales Order date  (date_order)
    #   invoice_date_due  -> installment line's collection_date
    #
    # We only touch invoices that carry `sale_order_installment_id`, i.e.
    # the ones produced by "Create Installment Invoices" on the Sale Order.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_so_installment_dates(vals)
        return super().create(vals_list)

    def _apply_so_installment_dates(self, vals):
        """Mutate the create vals of a single installment invoice in place."""
        line_id = vals.get('sale_order_installment_id')
        if not line_id:
            # Not an SO-installment invoice -> leave standard behaviour untouched.
            return

        line = self.env['sale.order.installment.line'].browse(line_id)
        if not line.exists():
            return

        order = line.sale_order_id
        if not order and vals.get('sale_order_id'):
            order = self.env['sale.order'].browse(vals['sale_order_id'])

        # Invoice Date = Sales Order Order Date
        if order and order.date_order:
            vals['invoice_date'] = fields.Date.to_date(order.date_order)

        # Due Date = installment collection date (the real maturity of the line)
        if line.collection_date:
            vals['invoice_date_due'] = line.collection_date
