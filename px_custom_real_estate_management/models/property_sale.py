from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class PropertySale(models.Model):
    _inherit = "property.sale"

    reservation_duration_hours = fields.Float(related="property_id.reservation_duration_hours", readonly=False)

    payment_plan_id = fields.Many2one(
        "payment.plane",
        string="Payment Plan",
        help="Select a payment plan for this sale"
    )
    property_sale_line_ids = fields.One2many(
        'property.sale.line',
        'sale_id',
        string="Installments"
    )

    def action_broker_commission_invoice(self):
        for rec in self:
            if not rec.broker_id:
                raise ValidationError(_("No broker selected."))

            if not rec.commission or rec.commission <= 0:
                raise ValidationError(_("Commission amount is missing or zero."))

            invoice = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': rec.broker_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, {
                    'name': f'Commission for {rec.name}',
                    'price_unit': rec.commission,
                    'quantity': 1,
                })]
            })

            return {
                'name': _('Broker Commission Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
            }

    def action_cancel(self):
        """Cancel sale and reset property to available if needed"""
        for rec in self:
            rec.state = "cancel"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    @api.model
    def create(self, vals):
        """Prevent creating a sale if the property is sold"""
        property_id = self.env["property.property"].browse(vals.get("property_id"))
        if property_id and property_id.state == "sold":
            raise ValidationError(_("This property is already sold and cannot be booked or sold again."))
        return super(PropertySale, self).create(vals)

    def write(self, vals):
        """Prevent changing to a sold property in write"""
        if vals.get("property_id"):
            property_id = self.env["property.property"].browse(vals["property_id"])
            if property_id and property_id.state == "sold":
                raise ValidationError(_("This property is already sold and cannot be booked or sold again."))
        return super(PropertySale, self).write(vals)


    def action_temp_reserve_property(self):
        for rec in self:
            if rec.property_id:
                rec.property_id.action_temp_reserve_sold()

    @api.onchange('payment_plan_id')
    def _onchange_payment_plan_id(self):
        for rec in self:
            rec.property_sale_line_ids = [(5, 0, 0)]
            if not rec.payment_plan_id:
                continue

            plan = rec.payment_plan_id

            discount_amount = rec.sale_price * (plan.discount / 100.0)
            price_after_discount = rec.sale_price - discount_amount

            down_payment = price_after_discount * (plan.down_payment_percentage / 100.0)
            remaining_after_down = price_after_discount - down_payment

            annual_amount = remaining_after_down * (plan.annual_payment_percentage / 100.0)

            amount_to_be_installed = remaining_after_down - (annual_amount * plan.payment_duration)

            multiplier = {
                'monthly': 12,
                'quarterly': 4,
                'semi_annually': 2,
            }.get(plan.payment_frequency, 0)

            no_of_installments = plan.payment_duration * multiplier
            amount_per_installment = amount_to_be_installed / no_of_installments if no_of_installments else 0.0

            lines = []
            current_date = plan.payment_start_date
            seq = 0

            if down_payment > 0:
                lines.append((0, 0, {
                    'serial_number': seq,
                    'name': "Down Payment",
                    'capital_repayment': down_payment,
                    'remaining_capital': remaining_after_down,
                    'collection_status': 'not_due',
                    'collection_date': plan.payment_start_date,
                }))
                seq += 1

            interval_months = {
                'monthly': 1,
                'quarterly': 3,
                'semi_annually': 6,
            }.get(plan.payment_frequency, 1)

            for i in range(1, no_of_installments + 1):
                current_date += relativedelta(months=interval_months)
                lines.append((0, 0, {
                    'serial_number': seq,
                    'name': f"Periodic Installment {i}",
                    'capital_repayment': amount_per_installment,
                    'remaining_capital': remaining_after_down - (i * amount_per_installment),
                    'collection_status': 'not_due',
                    'collection_date': current_date,
                }))
                seq += 1

            if plan.annual_payment_percentage > 0:
                for i in range(1, plan.payment_duration + 1):
                    lines.append((0, 0, {
                        'serial_number': seq,
                        'name': f"Annual Installment {i}",
                        'capital_repayment': annual_amount,
                        'remaining_capital': remaining_after_down - (i * annual_amount),
                        'collection_status': 'not_due',
                        'collection_date': plan.payment_start_date + relativedelta(years=i),
                    }))
                    seq += 1

            rec.property_sale_line_ids = lines

class PropertySaleLine(models.Model):
    _name = "property.sale.line"
    _description = "Property Sale Line"

    sale_id = fields.Many2one("property.sale", string="Sale", ondelete="cascade")
    name = fields.Char(string="Description")
    serial_number = fields.Integer(string="Serial Number")
    capital_repayment = fields.Float(string="Installment Amount")
    remaining_capital = fields.Float(string="Remaining Capital")

    collection_status = fields.Selection(
        [("not_due", "Not Due"),
         ("collected", "Collected"),
         ("pending", "Pending")],
        string="Collection Status",
        default="not_due"
    )
    collection_amount = fields.Float(string="Collected Amount")
    collection_date = fields.Date(string="Collection Date")
