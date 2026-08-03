from odoo import models, api, _, fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# Stamped on the invoice line when an installment is invoiced. The keys match
# sale.order.installment.line.line_type and the account settings on res.company,
# so the three stay in step.
INSTALLMENT_TYPE_SELECTION = [
    ('down_payment', 'Down Payment'),
    ('periodic', 'Periodic Installment'),
    ('annual', 'Annual Installment'),
    ('maintenance', 'Maintenance'),
]


class AccountMove(models.Model):
    _inherit = "account.move"


    sale_order_installment_id = fields.Many2one(
        'sale.order.installment.line',
        string="SO Installment"
    )
    installment_id = fields.Many2one("crm.lead.installment", string="Installment")
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", index=True, copy=False)
    property_installment_id = fields.Many2one('payment.installment.line', string="Property Installment")

    # Stamped when the invoice is created, not related to sale_order_id: an invoice is a
    # legal document and must keep the project/unit it was issued for, even if the order
    # is edited afterwards. Writable so invoices without an order (bookings, rentals) can
    # still carry a unit and show up in the Invoice Analysis report.
    property_id = fields.Many2one(
        'property.property', string="Unit", index=True, copy=False,
    )
    property_project_id = fields.Many2one(
        'property.project', string="Project", index=True, copy=False,
    )

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Linking an invoice to an order by hand pulls the unit and project across."""
        for move in self:
            if move.sale_order_id:
                move.property_id = move.sale_order_id.property_id
                move.property_project_id = move.sale_order_id.project_id

    def action_view_sale_order(self):
        """Open the Sale Order this invoice was generated from."""
        self.ensure_one()
        if not self.sale_order_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
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


    # def action_register_payment(self):
    #     action = super().action_register_payment()
    #
    #     if self.is_cheque:
    #         action['context'].update({
    #             'default_is_cheque_payment': True,
    #             'default_cheque_payment_number': self.cheque_number,
    #             'default_customer_payment_cheque_bank_id': self.customer_cheque_bank_id.id,
    #             'default_cheque_payment_due_date': self.cheque_due_date,
    #         })
    #
    #     return action

    def action_register_payment(self):
        _logger.info("تم استدعاء action_register_payment للفاتورة %s", self.name)

        action = super().action_register_payment()
        _logger.info("تم استدعاء super().action_register_payment(), النتيجة: %s", action)

        if self.is_cheque:
            _logger.info("الفاتورة هي دفعة شيك. بيانات الشيك قبل التحديث: Cheque Number=%s, Bank=%s, Due Date=%s",
                         self.cheque_number,
                         self.customer_cheque_bank_id.name if self.customer_cheque_bank_id else None,
                         self.cheque_due_date)

            action['context'].update({
                'default_is_cheque_payment': True,
                'default_cheque_payment_number': self.cheque_number,
                'default_customer_payment_cheque_bank_id': self.customer_cheque_bank_id.id if self.customer_cheque_bank_id else None,
                'default_cheque_payment_due_date': self.cheque_due_date,
            })
            _logger.info("تم تحديث context ببيانات الشيك: %s", action['context'])

        else:
            _logger.info("الفاتورة ليست دفعة شيك.")

        return action

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



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # Kept on the line rather than the move because Invoice Analysis reports one
    # row per line, and because a hand-edited invoice can mix installment types.
    installment_type = fields.Selection(
        INSTALLMENT_TYPE_SELECTION,
        string="Installment Type",
        index=True,
        copy=False,
        help="Which installment of the payment plan this line was invoiced for.",
    )


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    property_sale_id = fields.Many2one('property.sale', string="Property Sale")
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



class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_cheque_payment = fields.Boolean(string="Is Cheque")
    cheque_payment_number = fields.Char(string="Cheque Number")
    customer_payment_cheque_bank_id = fields.Many2one(
        'bank.tag',
        string="Customer Cheque Bank"
    )
    cheque_payment_due_date = fields.Date(string="Cheque Due Date")

    @api.model
    def default_get(self, fields_list):
        _logger.info("🔵 default_get اتنادت في account.payment.register")
        _logger.info("Context بالكامل: %s", self.env.context)

        res = super().default_get(fields_list)

        _logger.info("القيم بعد super(): %s", res)

        if self.env.context.get('default_is_cheque_payment'):
            _logger.info("🟢 فيه بيانات شيك جاية من الفاتورة")

            res.update({
                'is_cheque_payment': self.env.context.get('default_is_cheque_payment'),
                'cheque_payment_number': self.env.context.get('default_cheque_payment_number'),
                'customer_payment_cheque_bank_id': self.env.context.get('default_customer_payment_cheque_bank_id'),
                'cheque_payment_due_date': self.env.context.get('default_cheque_payment_due_date'),
            })

            _logger.info("القيم بعد التحديث: %s", res)

        else:
            _logger.info("🔴 مفيش بيانات شيك في الـ context")

        return res

    def _create_payments(self):
        _logger.info("🟣 تم استدعاء _create_payments")
        _logger.info("القيم في الـ wizard قبل إنشاء الدفع:")
        _logger.info("is_cheque_payment: %s", self.is_cheque_payment)
        _logger.info("cheque_payment_number: %s", self.cheque_payment_number)
        _logger.info("bank_id: %s", self.customer_payment_cheque_bank_id.id)
        _logger.info("due_date: %s", self.cheque_payment_due_date)

        payments = super()._create_payments()

        _logger.info("🟢 تم إنشاء payments: %s", payments.ids)

        for payment in payments:
            _logger.info("🔄 جاري تحديث payment ID: %s", payment.id)

            payment.write({
                'is_cheque_payment': self.is_cheque_payment,
                'cheque_payment_number': self.cheque_payment_number,
                'customer_payment_cheque_bank_id': self.customer_payment_cheque_bank_id.id,
                'cheque_payment_due_date': self.cheque_payment_due_date,
            })

            _logger.info("✅ تم تحديث payment ID %s ببيانات الشيك", payment.id)

        return payments
