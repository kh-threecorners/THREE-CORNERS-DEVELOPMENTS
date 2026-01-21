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
    partner_nationality = fields.Char(string='Nationality')


    partner_street = fields.Char(string='Street')
    partner_street2 = fields.Char(string='Street 2')
    partner_zip = fields.Char(string='Zip')
    partner_jop = fields.Char(string='Job Position')
    contact_code = fields.Char(string='Contact Code')
    partner_city = fields.Char(string='City')
    partner_state_id = fields.Char(string='State')
    partner_country_id = fields.Many2one("res.country",string='Country')
    partner_email = fields.Char(string="Email")
    partner_phone = fields.Char(string="Phone")
    partner_mobile = fields.Char(string="Mobile")
    id_number = fields.Char(string="Id Number")

    property_sale_line_ids = fields.One2many(
        'property.sale.line',
        'sale_id',
        string="Installments"
    )
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", readonly=True)
    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True)
    is_sale_order_created = fields.Boolean(string="Sale Order Created", default=False)
    is_payment_created = fields.Boolean(string="Payment Created", default=False)

    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        readonly=True
    )

    internal_sales_person_id = fields.Many2one('res.partner', string="Sales Person ")
    internal_commission_plan_id = fields.Many2one('property.commission', string="Commission Plan")
    internal_commission_type = fields.Char(compute='_compute_internal_commission', store=True, string="Commission Type")
    internal_commission = fields.Monetary(string='Commission', compute='_compute_internal_commission', store=True)

    external_broker_id = fields.Many2one(
        'res.partner',
        string="Broker",
        domain="[('is_broker', '=', True)]",
        help="The external broker for this property sale"
    )
    external_commission_plan_id = fields.Many2one(
        'property.commission',
        string="Commission Plan",
        help="Select the Commission Plan for the external broker"
    )
    external_commission_type = fields.Char(
        compute='_compute_external_commission',
        string="Commission Type",
        store=True
    )
    external_commission = fields.Monetary(
        string='Commission',
        compute='_compute_external_commission',
        store=True
    )


    @api.depends('external_commission_plan_id', 'sale_price')
    def _compute_external_commission(self):
        """Calculate external broker commission based on commission plan and sale price"""
        for rec in self:
            if rec.external_commission_plan_id and rec.sale_price > 0:
                rec.external_commission_type = rec.external_commission_plan_id.commission_type
                if rec.external_commission_plan_id.commission_type == 'fixed':
                    rec.external_commission = rec.external_commission_plan_id.commission
                else:  # percentage
                    rec.external_commission = (rec.sale_price * rec.external_commission_plan_id.commission) / 100
            else:
                rec.external_commission_type = ''
                rec.external_commission = 0.0


    def action_external_commission_invoice(self):
        for rec in self:
            if not rec.external_broker_id:
                raise ValidationError(_("No external broker selected."))

            if not rec.external_commission or rec.external_commission <= 0:
                raise ValidationError(_("External commission amount is missing or zero."))

            invoice = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': rec.external_broker_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, {
                    'name': f'External Broker Commission for {rec.name}',
                    'price_unit': rec.external_commission,
                    'quantity': 1,
                })]
            })

            return {
                'name': _('External Broker Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
            }

    @api.depends('internal_commission_plan_id', 'sale_price')
    def _compute_internal_commission(self):
        for rec in self:
            if rec.internal_commission_plan_id and rec.sale_price > 0:
                rec.internal_commission_type = rec.internal_commission_plan_id.commission_type
                if rec.internal_commission_plan_id.commission_type == 'fixed':
                    rec.internal_commission = rec.internal_commission_plan_id.commission
                else:
                    rec.internal_commission = (rec.sale_price * rec.internal_commission_plan_id.commission) / 100
            else:
                rec.internal_commission_type = ''
                rec.internal_commission = 0.0

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

    def action_internal_commission_invoice(self):
        for rec in self:
            if not rec.internal_sales_person_id:
                raise ValidationError(_("No internal sales person selected."))

            if not rec.internal_commission or rec.internal_commission <= 0:
                raise ValidationError(_("Internal commission amount is missing or zero."))

            partner = rec.internal_sales_person_id
            if not partner:
                raise ValidationError(_("The selected internal sales person does not have a related partner record."))

            invoice = self.env['account.move'].create({
                'move_type': 'in_invoice',

                'partner_id': partner.id,

                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, {
                    'name': f'Internal Commission for {rec.name}',

                    # 5. استخدام مبلغ عمولة الشخص الجديد
                    'price_unit': rec.internal_commission,

                    'quantity': 1,
                })]
            })

            return {
                'name': _('Internal Commission Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
            }

    def action_cancel(self):
        """Cancel sale and reset property to available if needed"""
        for rec in self:
            rec.state = "cancel"
            if rec.property_id:
                rec.property_id.state = "available"

    # def action_cancel(self):
    #     """Cancel sale and reset property to available if needed"""
    #     for rec in self:
    #         rec.state = "cancel"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"


    @api.model
    def create(self, vals_list):
        records = []
        for vals in vals_list:
            property_id = self.env["property.property"].browse(vals.get("property_id"))
            if property_id and property_id.state == "sold":
                raise ValidationError(_("This property is already sold and cannot be booked or sold again."))

            rec = super(PropertySale, self).create(vals)
            records.append(rec)

        return records[0] if len(records) == 1 else records

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

    def action_create_sale_order(self):
        """
        Create a linked Sale Order for this Property Sale.
        Ensures the property has a product and the customer is set.
        """

        for rec in self:
            if rec.sale_order_id:
                raise ValidationError(_("A Sale Order already exists for this record."))

            if not rec.partner_id:
                raise ValidationError(_("Please select a customer before creating a Sale Order."))

            product_id = rec.property_id.product_id.id if rec.property_id and rec.property_id.product_id else False
            if not product_id:
                raise ValidationError(_("The property does not have a linked product for the Sale Order."))

            sale_order = self.env['sale.order'].create({
                'partner_id': rec.partner_id.id,
                'property_sale_id': rec.id,
                'project_id': rec.project_id.id if rec.project_id else False,
                'payment_id': rec.payment_plan_id.id if rec.payment_plan_id else False,
                'order_line': [(0, 0, {
                    'name': rec.name or "Property Sale",
                    'product_id': product_id,
                    'price_unit': rec.sale_price,
                    'product_uom_qty': 1,
                })]
            })

            rec.write({
                'sale_order_id': sale_order.id,
                'is_sale_order_created': True,
            })

            rec.sale_order_id = sale_order.id

            return {
                'name': "Sale Order",
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': sale_order.id,
            }

    def action_view_sale_order(self):
        """Open the linked Sale Order"""
        self.ensure_one()
        if not self.sale_order_id:
            return
        return {
            'name': 'Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    def action_view_invoice(self):
        """Open the linked Invoice"""
        self.ensure_one()
        if not self.invoice_id:
            return
        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }




    def action_create_invoice(self):
            for rec in self:
                if rec.invoice_id:
                    raise ValidationError(_("An invoice already exists for this sale record."))

                if not rec.partner_id:
                    raise ValidationError(_("Please select a customer before creating an invoice."))

                invoice = self.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'partner_id': rec.partner_id.id,
                    'invoice_origin': rec.name,
                    'invoice_line_ids': [(0, 0, {
                        'name': rec.name or "Property Invoice",
                        'price_unit': rec.sale_price,
                        'quantity': 1,
                    })],
                })

                rec.invoice_id = invoice.id

                return {
                    'name': "Invoice",
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'view_mode': 'form',
                    'res_id': invoice.id,
                }

    def action_create_downpayment(self):
        for rec in self:
            if not rec.partner_id:
                raise ValidationError(_("Please select a customer before creating a payment."))

            if rec.paid <= 0:
                raise ValidationError(_("The 'Paid' amount must be greater than zero."))

            payment = self.env['account.payment'].create({
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': rec.partner_id.id,
                'amount': rec.paid,
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
            })
            rec.write({
                'payment_id': payment.id,
                'is_payment_created': True,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': "Payments",
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': payment.id,
        }

    def action_view_payment(self):
        self.ensure_one()
        if not self.payment_id:
            return False

        return {
            'name': _('Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.payment_id.id,
            'target': 'current',
        }


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



