from odoo import models, api, _, fields


class AccountMove(models.Model):
    _inherit = "account.move"



    sale_order_installment_id = fields.Many2one(
        'sale.order.installment.line',
        string="SO Installment"
    )
    installment_id = fields.Many2one("crm.lead.installment", string="Installment")
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    property_installment_id = fields.Many2one('payment.installment.line', string="Property Installment")

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            # لو دي فاتورة مرتبطة بقسط إيجار
            installment = self.env['property.rental.installment'].search([
                ('invoice_id', '=', move.id),
                ('state', '=', 'un_paid'),
            ], limit=1)
            if installment:
                installment.state = 'paid'
        return res
