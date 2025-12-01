from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    supplier_invoice_count = fields.Integer(
        string='Supplier Invoice Count',
        # compute='_compute_supplier_invoice_count'
    )


    # def _compute_supplier_invoice_count(self):
    #     for partner in self:
    #         partner.supplier_invoice_count = self.env['account.move'].search_count([
    #             ('partner_id', '=', partner.id),
    #             ('move_type', '=', 'in_invoice'),
    #             ('state', '=', 'posted')
    #         ])
