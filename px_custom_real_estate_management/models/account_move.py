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
            record._create_calendar_events()
            record._create_cheque_activity()
        return records

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for record in self:
            record._create_calendar_events()
            record._create_cheque_activity()
        return res

    def _create_cheque_activity(self):
        for move in self:

            activity_type = self.env.ref('mail.mail_activity_data_todo')

            if move.invoice_date:
                existing_invoice_activity = self.env['mail.activity'].search([
                    ('res_model', '=', move._name),
                    ('res_id', '=', move.id),
                    ('activity_type_id', '=', activity_type.id),
                    ('date_deadline', '=', move.invoice_date),
                    ('summary', '=', f'Invoice Date Reminder: {move.name}')
                ])
                if not existing_invoice_activity:
                    move.activity_schedule(
                        activity_type_id=activity_type.id,
                        summary=f'Invoice Date Reminder: {move.name}',
                        date_deadline=move.invoice_date
                    )


            if move.is_cheque and move.cheque_due_date:
                existing_cheque_activity = self.env['mail.activity'].search([
                    ('res_model', '=', move._name),
                    ('res_id', '=', move.id),
                    ('activity_type_id', '=', activity_type.id),
                    ('date_deadline', '=', move.cheque_due_date),
                    ('summary', '=', f'Cheque due: {move.cheque_number}')
                ])
                if not existing_cheque_activity:
                    move.activity_schedule(
                        activity_type_id=activity_type.id,
                        summary=f'Cheque due: {move.cheque_number}',
                        date_deadline=move.cheque_due_date
                    )

    def _create_calendar_events(self):
        for move in self:

            if move.invoice_date:
                existing_event = self.env['calendar.event'].search([
                    ('res_model', '=', move._name),
                    ('res_id', '=', move.id),
                    ('start_date', '=', move.invoice_date),
                    ('name', '=', f'Invoice Reminder: {move.name}')
                ], limit=1)

                if not existing_event:
                    self.env['calendar.event'].create({
                        'name': f'Invoice Reminder: {move.name}',
                        'start_date': move.invoice_date,
                        'stop_date': move.invoice_date,
                        'res_model': move._name,
                        'res_id': move.id,
                        'allday': True,
                        'user_id': move.invoice_user_id.id or self.env.user.id,
                    })

            if move.is_cheque and move.cheque_due_date:
                existing_event_cheque = self.env['calendar.event'].search([
                    ('res_model', '=', move._name),
                    ('res_id', '=', move.id),
                    ('start_date', '=', move.cheque_due_date),
                    ('name', '=', f'Cheque Due: {move.cheque_number}')
                ], limit=1)

                if not existing_event_cheque:
                    self.env['calendar.event'].create({
                        'name': f'Cheque Due: {move.cheque_number}',
                        'start_date': move.cheque_due_date,
                        'stop_date': move.cheque_due_date,
                        'res_model': move._name,
                        'res_id': move.id,
                        'allday': True,
                        'user_id': move.invoice_user_id.id or self.env.user.id,
                    })

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

    def action_post(self):
        res = super(AccountPayment, self).action_post()

        for payment in self:
            if payment.move_id:
                move_vals = {
                    'is_cheque': payment.is_cheque_payment,
                    'cheque_number': payment.cheque_payment_number,
                    'customer_cheque_bank_id': payment.customer_payment_cheque_bank_id.id,
                    'cheque_due_date': payment.cheque_payment_due_date,
                }
                payment.move_id.write(move_vals)
        return res