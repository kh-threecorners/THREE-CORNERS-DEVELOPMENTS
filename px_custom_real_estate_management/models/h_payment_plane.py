from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PaymentPlan(models.Model):
    _name = "payment.plane"
    _description = "Payment Plan"

    property_id = fields.Many2one('property.property', string="Property")
    name = fields.Char(string='Name', required=True)
    state = fields.Selection([
        ('published', 'Published'),
        ('draft', 'Draft')])
    discount = fields.Float(string="Discount %", default=0.0, tracking=True)
    down_payment_percentage = fields.Float(string="Down Payment %", tracking=True)
    annual_payment_percentage = fields.Float(string="Annual Payment %", tracking=True,
                                             help="Percentage of the price after discount to be paid annually.")
    payment_start_date = fields.Date(string="Payment Start Date", default=fields.Date.context_today, required=True)
    payment_duration = fields.Integer(string="Payment Duration (Years)", default=1, required=True, tracking=True)
    payment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annually', 'Semi-Annually')
    ], string="Periodic Payment Frequency", default='monthly', required=True, tracking=True)
    unit_price = fields.Monetary(string="Unit Price", related='property_id.unit_price', tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency", related="property_id.company_id.currency_id")
    price_after_discount = fields.Float(string="Price After Discount", compute='_compute_price_after_discount',
                                        store=True)
    down_payment = fields.Float(string="Down Payment Amount", compute="_compute_down_payment", store=True)

    total_annual_payment_amount = fields.Float(string="Total Annual Payments", compute="_compute_annual_payment",
                                               store=True,
                                               help="Total amount that will be paid through annual installments.")

    amount_to_be_installed = fields.Float(string="Amount for Periodic Installments", compute="_compute_final_amount",
                                          store=True,
                                          help="The final amount to be paid in periodic installments (monthly, quarterly, etc.)")

    no_of_installments = fields.Integer(string="Number of Periodic Installments", compute='_compute_installments',
                                        store=True)
    amount_per_installment = fields.Float(string="Amount Per Periodic Installment", compute='_compute_installments',
                                          store=True)
    installment_line_ids = fields.One2many('payment.installment.line', 'payment_plane_id', string='Installment Lines')

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    opportunity_id = fields.Many2one("crm.lead", string="Opportunity")
    annual_installments_count = fields.Integer(
        string="Annual Installments Count",
        default=0,
     )
    maintenance_percentage = fields.Float(string="Maintenance %", default=0.0)
    is_maintenance_in_middle = fields.Boolean(string="Maintenance in Middle", default=True)

    @api.depends('unit_price', 'discount')
    def _compute_price_after_discount(self):
        for record in self:
            discount_amount = record.unit_price * (record.discount / 100.0)
            record.price_after_discount = record.unit_price - discount_amount

    @api.depends('down_payment_percentage', 'price_after_discount')
    def _compute_down_payment(self):
        for record in self:
            record.down_payment = record.price_after_discount * (record.down_payment_percentage / 100.0)

    @api.depends('annual_payment_percentage', 'price_after_discount', 'payment_duration')
    def _compute_annual_payment(self):
        for record in self:
            if record.payment_duration > 0:
                single_year_payment = record.price_after_discount * (record.annual_payment_percentage / 100.0)
                record.total_annual_payment_amount = single_year_payment * record.payment_duration
            else:
                record.total_annual_payment_amount = 0.0

    @api.depends('price_after_discount', 'down_payment', 'total_annual_payment_amount')
    def _compute_final_amount(self):
        for record in self:
            record.amount_to_be_installed = record.price_after_discount - record.down_payment - record.total_annual_payment_amount

    @api.depends('amount_to_be_installed', 'payment_duration', 'payment_frequency')
    def _compute_installments(self):
        for record in self:
            if record.payment_duration > 0 and record.amount_to_be_installed > 0:
                multiplier = {
                    'monthly': 12,
                    'quarterly': 4,
                    'semi_annually': 2
                }.get(record.payment_frequency, 0)

                total_installments = record.payment_duration * multiplier
                record.no_of_installments = total_installments

                if total_installments > 0:
                    record.amount_per_installment = record.amount_to_be_installed / total_installments
                else:
                    record.amount_per_installment = 0.0
            else:
                record.no_of_installments = 0
                record.amount_per_installment = 0.0

    def generate_installment_lines_button(self):
        for record in self:
            print("=== Generating Installments for Payment Plan:", record.name, "===")
            record.installment_line_ids = [(5, 0, 0)]

            if not record.payment_duration or not record.payment_start_date:
                raise ValidationError(_("Please set the Payment Duration and Start Date before generating lines."))

            print("Payment Duration:", record.payment_duration)
            print("Payment Start Date:", record.payment_start_date)
            print("Annual Payment %:", record.annual_payment_percentage)
            print("Annual Installments Count (field):", record.annual_installments_count)

            lines = []

            if record.no_of_installments > 0 and record.amount_per_installment > 0:
                interval_months = {
                    'monthly': 1,
                    'quarterly': 3,
                    'semi_annually': 6
                }.get(record.payment_frequency, 1)

                current_date = record.payment_start_date
                for i in range(1, record.no_of_installments + 1):
                    current_date += relativedelta(months=interval_months)
                    lines.append({
                        'due_date': current_date,
                        'amount': record.amount_per_installment,
                        'type': 'periodic',
                    })

                print("Number of periodic installments:", len(lines))

            if record.annual_payment_percentage > 0:
                total_annual_amount = record.price_after_discount * (record.annual_payment_percentage / 100.0)
                if total_annual_amount > 0:
                    annual_count = record.annual_installments_count if record.annual_installments_count > 0 else record.payment_duration
                    print("Annual Count used:", annual_count)
                    for i in range(1, annual_count + 1):
                        due_date = record.payment_start_date + relativedelta(years=i)
                        lines.append({
                            'due_date': due_date,
                            'amount': total_annual_amount / annual_count,
                            'type': 'annual',
                        })
                        print(
                            f"Annual installment {i}: Due Date = {due_date}, Amount = {total_annual_amount / annual_count}")

            lines.sort(key=lambda x: x['due_date'])

            final_lines = []
            for i, line in enumerate(lines, 1):
                final_lines.append((0, 0, {
                    'sequence': i,
                    'name': f"{line['type'].capitalize()} Installment {i}",
                    'due_date': line['due_date'],
                    'amount': line['amount'],
                    'type': line['type'],
                }))

            print("Total Installments Generated:", len(final_lines))
            record.installment_line_ids = final_lines
        return True


class PaymentInstallmentLine(models.Model):
    _name = 'payment.installment.line'
    _description = 'Payment Installment Line'
    _order = 'sequence'

    payment_plane_id = fields.Many2one('payment.plane', string='Payment Plan', ondelete='cascade')
    sequence = fields.Integer(string='Seq.')
    name = fields.Char(string='Description')
    amount = fields.Float(string='Amount')
    due_date = fields.Date(string="Due Date")
    type = fields.Selection([('annual', 'Annual'), ('periodic', 'Periodic')], string="Type")
    property_id = fields.Many2one('property.property', string="Property")
    payment_plan_id = fields.Many2one(
        'payment.plane',
        string="Payment Plan",
        ondelete="cascade"
    )



