from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertySalePaymentWizard(models.TransientModel):
    _name = 'property.sale.payment.wizard'
    _description = 'Register Property Sale Payment'

    property_sale_id = fields.Many2one('property.sale', string="Property Sale", required=True)
    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        related='property_sale_id.partner_id',
        readonly=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string="Journal",
        required=True,
        domain="['&', ('type', 'in', ('bank', 'cash')),"
               " '|', ('currency_id', '=', False), ('currency_id', '=', currency_id)]",
        default=lambda self: self.env['account.journal'].search(
            ['&', ('type', '=', 'bank'),
             '|', ('currency_id', '=', False),
             ('currency_id', '=', self.env.company.currency_id.id)],
            limit=1,
        ),
    )
    payment_date = fields.Date(
        string="Payment Date",
        required=True,
        default=fields.Date.context_today,
    )
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    communication = fields.Char(string="Memo")

    def action_create_payment(self):
        self.ensure_one()
        if self.amount <= 0:
            raise ValidationError(_("The amount must be greater than zero."))
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.property_sale_id.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'memo': self.communication,
            'property_sale_id': self.property_sale_id.id,
        })
        return {
            'name': _('Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': payment.id,
            'target': 'current',
        }
