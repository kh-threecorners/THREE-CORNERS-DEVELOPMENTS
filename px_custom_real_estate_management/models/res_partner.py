from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_broker = fields.Boolean(string="Is Broker")

    broker_commission_invoice_ids = fields.One2many(
        'account.move',
        'partner_id',
        string="Broker Commission Invoices",
        domain=[('move_type', '=', 'in_invoice'), ('invoice_line_ids.name', 'ilike', 'Commission')]
    )