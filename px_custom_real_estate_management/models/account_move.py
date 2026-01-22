from odoo import models, api, _, fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


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

    late_fee_percentage = fields.Float(
        string="Late Fee Percentage",
        default=0.0,
        copy=False,
        tracking=True,
    )

    is_late_fee_applied = fields.Boolean(
        string="Is Late Fee Applied",
        default=False,
        copy=False,
        readonly=True
    )
    late_fee_move_line_id = fields.Many2one(
        'account.move.line',
        string='Late Fee Line',
        readonly=True,
        copy=False
    )

    @api.model
    def _process_late_fee_invoices(self):
        late_fee_product = self.env['product.product'].search(
            [('default_code', '=', 'LATE_FEE')], limit=1
        )
        if not late_fee_product:
            _logger.error("منتج غرامة التأخير (LATE_FEE) غير موجود. يرجى إنشائه أولاً.")
            return

        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'draft'),
            ('invoice_date_due', '<', fields.Date.context_today(self)),
            ('is_late_fee_applied', '=', False),
        ])

        if not overdue_invoices:
            _logger.info("لا توجد فواتير Draft متأخرة لتطبيق الغرامة عليها.")
            return

        for invoice in overdue_invoices:
            fee_amount = invoice.amount_total * (invoice.late_fee_percentage / 100.0)

            price_for_line = fee_amount if fee_amount > 0 else late_fee_product.list_price

            fee_line = self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': late_fee_product.id,
                'name': f"Late fee for invoice {invoice.name or ''}",
                'quantity': 1,
                'price_unit': price_for_line,
            })

            invoice.write({
                'is_late_fee_applied': True,
                'late_fee_move_line_id': fee_line.id,
            })

            _logger.info(
                f"تم إضافة/تحديث غرامة على الفاتورة Draft {invoice.name} بسعر {price_for_line}"
            )

        _logger.info("انتهاء مهمة تطبيق غرامات التأخير على فواتير Draft.")

    @api.onchange('late_fee_percentage')
    def _onchange_late_fee_percentage(self):

        if self.move_type == 'out_invoice' and self.late_fee_move_line_id:

            if self.late_fee_percentage > 0:
                base_amount = sum(
                    line.price_subtotal for line in self.invoice_line_ids if line.id != self.late_fee_move_line_id.id)

                new_fee_amount = base_amount * (self.late_fee_percentage / 100.0)

                if new_fee_amount > 0:
                    self.late_fee_move_line_id.price_unit = new_fee_amount
            else:
                self.late_fee_move_line_id.price_unit = self.late_fee_move_line_id.product_id.list_price


    #
    # @api.model_create_multi
    # def create(self, vals_list):
    #     records = super(AccountMove, self).create(vals_list)
    #     for record in records:
    #         record._create_calendar_events()
    #         record._create_cheque_activity()
    #     return records
    #
    # def write(self, vals):
    #     res = super(AccountMove, self).write(vals)
    #     for record in self:
    #         record._create_calendar_events()
    #         record._create_cheque_activity()
    #     return res
    #
    # def _create_cheque_activity(self):
    #     for move in self:
    #
    #         activity_type = self.env.ref('mail.mail_activity_data_todo')
    #
    #         if move.invoice_date:
    #             existing_invoice_activity = self.env['mail.activity'].search([
    #                 ('res_model', '=', move._name),
    #                 ('res_id', '=', move.id),
    #                 ('activity_type_id', '=', activity_type.id),
    #                 ('date_deadline', '=', move.invoice_date),
    #                 ('summary', '=', f'Invoice Date Reminder: {move.name}')
    #             ])
    #             if not existing_invoice_activity:
    #                 move.activity_schedule(
    #                     activity_type_id=activity_type.id,
    #                     summary=f'Invoice Date Reminder: {move.name}',
    #                     date_deadline=move.invoice_date
    #                 )
    #
    #
    #         if move.is_cheque and move.cheque_due_date:
    #             existing_cheque_activity = self.env['mail.activity'].search([
    #                 ('res_model', '=', move._name),
    #                 ('res_id', '=', move.id),
    #                 ('activity_type_id', '=', activity_type.id),
    #                 ('date_deadline', '=', move.cheque_due_date),
    #                 ('summary', '=', f'Cheque due: {move.cheque_number}')
    #             ])
    #             if not existing_cheque_activity:
    #                 move.activity_schedule(
    #                     activity_type_id=activity_type.id,
    #                     summary=f'Cheque due: {move.cheque_number}',
    #                     date_deadline=move.cheque_due_date
    #                 )
    #
    # def _create_calendar_events(self):
    #     for move in self:
    #
    #         if move.invoice_date:
    #             existing_event = self.env['calendar.event'].search([
    #                 ('res_model', '=', move._name),
    #                 ('res_id', '=', move.id),
    #                 ('start_date', '=', move.invoice_date),
    #                 ('name', '=', f'Invoice Reminder: {move.name}')
    #             ], limit=1)
    #
    #             if not existing_event:
    #                 self.env['calendar.event'].create({
    #                     'name': f'Invoice Reminder: {move.name}',
    #                     'start_date': move.invoice_date,
    #                     'stop_date': move.invoice_date,
    #                     'res_model': move._name,
    #                     'res_id': move.id,
    #                     'allday': True,
    #                     'user_id': move.invoice_user_id.id or self.env.user.id,
    #                 })
    #
    #         if move.is_cheque and move.cheque_due_date:
    #             existing_event_cheque = self.env['calendar.event'].search([
    #                 ('res_model', '=', move._name),
    #                 ('res_id', '=', move.id),
    #                 ('start_date', '=', move.cheque_due_date),
    #                 ('name', '=', f'Cheque Due: {move.cheque_number}')
    #             ], limit=1)
    #
    #             if not existing_event_cheque:
    #                 self.env['calendar.event'].create({
    #                     'name': f'Cheque Due: {move.cheque_number}',
    #                     'start_date': move.cheque_due_date,
    #                     'stop_date': move.cheque_due_date,
    #                     'res_model': move._name,
    #                     'res_id': move.id,
    #                     'allday': True,
    #                     'user_id': move.invoice_user_id.id or self.env.user.id,
    #                 })

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