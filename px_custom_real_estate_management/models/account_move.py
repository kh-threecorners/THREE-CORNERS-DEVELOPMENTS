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
    )

    is_late_fee_applied = fields.Boolean(
        string="Is Late Fee Applied",
        default=False,
        copy=False,
        readonly=True
    )


    #
    # @api.model
    # def _process_late_fee_invoices(self):
    #     """
    #     هذه الدالة يتم استدعاؤها بواسطة Cron Job للبحث عن الفواتير المتأخرة
    #     وتطبيق غرامة التأخير عليها.
    #     """
    #     _logger.info("بدء مهمة التحقق من غرامات التأخير...")
    #
    #     # ابحث عن منتج الغرامة. يجب أن يكون موجوداً ومُعداً بشكل صحيح.
    #     late_fee_product = self.env['product.product'].search([('default_code', '=', 'LATE_FEE')], limit=1)
    #     if not late_fee_product:
    #         _logger.error("منتج غرامة التأخير (LATE_FEE) غير موجود. يرجى إنشائه أولاً.")
    #         return
    #
    #     # جلب الفواتير المستحقة التي لم تطبق عليها الغرامة بعد
    #     overdue_invoices = self.search([
    #         ('move_type', '=', 'out_invoice'),
    #         ('state', '=', 'posted'),
    #         ('invoice_date_due', '<', fields.Date.context_today(self)),
    #         ('late_fee_percentage', '>', 0),
    #         ('is_late_fee_applied', '=', False),
    #         ('payment_state', 'in', ['not_paid', 'partial'])
    #     ])
    #
    #     if not overdue_invoices:
    #         _logger.info("لا توجد فواتير متأخرة لتطبيق الغرامة عليها.")
    #         return
    #
    #     for invoice in overdue_invoices:
    #         # --- هذا هو السطر الذي تم تعديله ---
    #         # حساب قيمة الغرامة بقسمة النسبة على 100 أولاً
    #         fee_amount = invoice.amount_total * (invoice.late_fee_percentage / 100.0)
    #         # ------------------------------------
    #
    #         if fee_amount <= 0:
    #             continue
    #
    #         # تحويل الفاتورة إلى وضع المسودة لإضافة السطر
    #         invoice.button_draft()
    #
    #         # إضافة سطر الغرامة
    #         self.env['account.move.line'].create({
    #             'move_id': invoice.id,
    #             'product_id': late_fee_product.id,
    #             'name': f"غرامة تأخير للفاتورة {invoice.name}",
    #             'quantity': 1,
    #             'price_unit': fee_amount,
    #         })
    #
    #         # تحديث حقل "تم تطبيق الغرامة" لمنع إضافتها مرة أخرى
    #         invoice.write({'is_late_fee_applied': True})
    #
    #         # إعادة ترحيل الفاتورة
    #         invoice.action_post()
    #         _logger.info(f"تم تطبيق غرامة بقيمة {fee_amount} على الفاتورة {invoice.name}")
    #
    #     _logger.info("انتهاء مهمة التحقق من غرامات التأخير.")


    @api.model
    def _process_late_fee_invoices(self):
        late_fee_product = self.env['product.product'].search([('default_code', '=', 'LATE_FEE')], limit=1)
        if not late_fee_product:
            _logger.error("منتج غرامة التأخير (LATE_FEE) غير موجود. يرجى إنشائه أولاً.")
            return
        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date_due', '<', fields.Date.context_today(self)),
            ('late_fee_percentage', '>', 0),
            ('is_late_fee_applied', '=', False),
            ('payment_state', 'in', ['not_paid', 'partial'])
        ])

        if not overdue_invoices:
            _logger.info("لا توجد فواتير متأخرة لتطبيق الغرامة عليها.")
            return

        for invoice in overdue_invoices:
            fee_amount = invoice.amount_total * (invoice.late_fee_percentage / 100.0)

            if fee_amount <= 0:
                continue

            invoice.button_draft()
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': late_fee_product.id,
                'name': f"غرامة تأخير للفاتورة {invoice.name}",
                'quantity': 1,
                'price_unit': fee_amount,
            })
            invoice.write({'is_late_fee_applied': True})
            invoice.action_post()
            _logger.info(f"تم تطبيق غرامة بقيمة {fee_amount} على الفاتورة {invoice.name}")

        _logger.info("انتهاء مهمة التحقق من غرامات التأخير.")

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