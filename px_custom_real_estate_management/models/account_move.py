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
    is_cheque = fields.Boolean(string="Is Cheque")
    cheque_number = fields.Char(string="Cheque Number")
    customer_cheque_bank = fields.Char(string="Customer Cheque Bank")
    customer_cheque_bank_id = fields.Many2one('bank.tag',string="Customer Cheque Bank")
    cheque_due_date = fields.Date(string="Cheque Due Date")


    @api.model_create_multi
    def create(self, vals_list):
        records = super(AccountMove, self).create(vals_list)
        for record in records:
            record._create_cheque_activity()
        return records

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        # نعمل Activity بعد التحديث لو فيه cheque info
        for record in self:
            record._create_cheque_activity()
        return res

    def _create_cheque_activity(self):
        for move in self:
            # بس نضيف Activity لو السجل فعلاً شيك والتاريخ موجود
            if move.is_cheque and move.cheque_due_date:
                activity_type = self.env.ref('mail.mail_activity_data_todo')
                # تحقق لو مفيش Activity موجودة لنفس التاريخ والشيك
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', move._name),
                    ('res_id', '=', move.id),
                    ('activity_type_id', '=', activity_type.id),
                    ('date_deadline', '=', move.cheque_due_date),
                    ('summary', '=', f'Cheque due: {move.cheque_number}')
                ])
                if not existing:
                    move.activity_schedule(
                        activity_type_id=activity_type.id,
                        summary=f'Cheque due: {move.cheque_number}',
                        date_deadline=move.cheque_due_date
                    )

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            installment = self.env['property.rental.installment'].search([
                ('invoice_id', '=', move.id),
                ('state', '=', 'un_paid'),
            ], limit=1)
            if installment:
                installment.state = 'paid'
        return res



class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_cheque_payment = fields.Boolean(string="Is Cheque")
    cheque_payment_number = fields.Char(string="Cheque Number")
    customer_payment_cheque_bank = fields.Char(string="Customer Cheque Bank")
    customer_payment_cheque_bank_id = fields.Many2one('bank.tag',string="Customer Cheque Bank")
    cheque_payment_due_date = fields.Date(string="Cheque Due Date")
