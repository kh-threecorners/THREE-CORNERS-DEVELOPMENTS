from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    payment_id = fields.Many2one('payment.plane', string="Payment Plan")
    property_id = fields.Many2one('property.property', string='Property')
    installment_ids = fields.One2many(
        "crm.lead.installment",
        "lead_id",
        string="Installments",
        readonly=True
    )
    other_opportunity_count = fields.Integer(
        string="Other Opportunities",
        compute="_compute_other_opportunity_count"
    )

    def _compute_other_opportunity_count(self):
        for lead in self:
            if lead.property_id:
                lead.other_opportunity_count = self.env['crm.lead'].search_count([
                    ('property_id', '=', lead.property_id.id),
                    ('id', '!=', lead.id)  # يستبعد نفسه
                ])
            else:
                lead.other_opportunity_count = 0

    def action_view_other_opportunities(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Other Opportunities',
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [
                ('property_id', '=', self.property_id.id),
                ('id', '!=', self.id)
            ],
            'context': {'default_property_id': self.property_id.id},
        }

    def action_sale_quotations_new(self):
        action = super(CrmLead, self).action_sale_quotations_new()

        for lead in self:
            if lead.property_id:
                product = self.env['product.product'].search(
                    [('name', '=', lead.property_id.name)], limit=1
                )

                if not product:
                    product = self.env['product.product'].create({
                        'name': lead.property_id.name,
                        'list_price': lead.property_id.unit_price,
                        'type': 'service',
                        'detailed_type': 'service',
                    })

                ctx = action.get('context', {})
                if isinstance(ctx, str):
                    ctx = safe_eval(ctx)
                context = dict(ctx)

                context.update({
                    'default_order_line': [(0, 0, {
                        'product_id': product.id,
                        'product_uom_qty': 1,
                        'price_unit': lead.property_id.unit_price,
                        'name': lead.property_id.name,
                    })],
                    'default_project_id': lead.property_project_id.id if lead.property_project_id else False,
                })
                action['context'] = context

        return action

    def _prepare_installment_lines(self):
        """ Helper: generate installment lines values (0,0,vals) """
        self.ensure_one()
        if not self.payment_id or not self.property_id:
            return []

        plan = self.payment_id
        property_rec = self.property_id

        sale_price = property_rec.unit_price or 0.0
        discounted_price = sale_price - (sale_price * (plan.discount / 100.0))

        down_payment = discounted_price * (plan.down_payment_percentage / 100.0)
        remaining_after_down = discounted_price - down_payment
        annual_amount = remaining_after_down * (plan.annual_payment_percentage / 100.0)
        amount_to_be_installed = remaining_after_down - (annual_amount * plan.payment_duration)

        multiplier = {'monthly': 12, 'quarterly': 4, 'semi_annually': 2}.get(plan.payment_frequency, 0)
        no_of_installments = plan.payment_duration * multiplier
        amount_per_installment = amount_to_be_installed / no_of_installments if no_of_installments else 0.0

        lines = []
        current_date = plan.payment_start_date
        seq = 0

        # Down payment
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

        interval_months = {'monthly': 1, 'quarterly': 3, 'semi_annually': 6}.get(plan.payment_frequency, 1)

        # Periodic installments
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

        # Annual installments
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

        # ✅ Add Maintenance installment (if any)
        if property_rec.maintenance_value and property_rec.maintenance_value > 0:
            last_date = lines[-1][2]['collection_date'] if lines else plan.payment_start_date
            lines.append((0, 0, {
                'serial_number': seq,
                'name': "Maintenance",
                'capital_repayment': property_rec.maintenance_value,
                'remaining_capital': 0.0,
                'collection_status': 'not_due',
                'collection_date': last_date + relativedelta(days=1),
            }))
            seq += 1

        return lines

    # def _prepare_installment_lines(self):
    #     """ Helper: generate installment lines values (0,0,vals) """
    #     self.ensure_one()
    #     if not self.payment_id or not self.property_id:
    #         return []
    #
    #     plan = self.payment_id
    #     sale_price = self.property_id.unit_price or 0.0
    #     discounted_price = sale_price - (sale_price * (plan.discount / 100.0))
    #
    #     down_payment = discounted_price * (plan.down_payment_percentage / 100.0)
    #     remaining_after_down = discounted_price - down_payment
    #     annual_amount = remaining_after_down * (plan.annual_payment_percentage / 100.0)
    #     amount_to_be_installed = remaining_after_down - (annual_amount * plan.payment_duration)
    #
    #     multiplier = {'monthly': 12, 'quarterly': 4, 'semi_annually': 2}.get(plan.payment_frequency, 0)
    #     no_of_installments = plan.payment_duration * multiplier
    #     amount_per_installment = amount_to_be_installed / no_of_installments if no_of_installments else 0.0
    #
    #     lines = []
    #     current_date = plan.payment_start_date
    #     seq = 0
    #
    #     if down_payment > 0:
    #         lines.append((0, 0, {
    #             'serial_number': seq,
    #             'name': "Down Payment",
    #             'capital_repayment': down_payment,
    #             'remaining_capital': remaining_after_down,
    #             'collection_status': 'not_due',
    #             'collection_date': plan.payment_start_date,
    #         }))
    #         seq += 1
    #
    #     interval_months = {'monthly': 1, 'quarterly': 3, 'semi_annually': 6}.get(plan.payment_frequency, 1)
    #
    #     for i in range(1, no_of_installments + 1):
    #         current_date += relativedelta(months=interval_months)
    #         lines.append((0, 0, {
    #             'serial_number': seq,
    #             'name': f"Periodic Installment {i}",
    #             'capital_repayment': amount_per_installment,
    #             'remaining_capital': remaining_after_down - (i * amount_per_installment),
    #             'collection_status': 'not_due',
    #             'collection_date': current_date,
    #         }))
    #         seq += 1
    #
    #     if plan.annual_payment_percentage > 0:
    #         for i in range(1, plan.payment_duration + 1):
    #             lines.append((0, 0, {
    #                 'serial_number': seq,
    #                 'name': f"Annual Installment {i}",
    #                 'capital_repayment': annual_amount,
    #                 'remaining_capital': remaining_after_down - (i * annual_amount),
    #                 'collection_status': 'not_due',
    #                 'collection_date': plan.payment_start_date + relativedelta(years=i),
    #             }))
    #             seq += 1
    #
    #     return lines


    @api.onchange('payment_id', 'property_id')
    def _onchange_payment_plan_id(self):
        for rec in self:
            rec.installment_ids = [(5, 0, 0)] + rec._prepare_installment_lines()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.payment_id and rec.property_id:
                rec.installment_ids.unlink()
                rec.installment_ids = rec._prepare_installment_lines()
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if 'payment_id' in vals or 'property_id' in vals:
                rec.installment_ids.unlink()
                rec.installment_ids = rec._prepare_installment_lines()
        return res

    # @api.constrains('mobile', 'phone')
    # def _check_phone_mobile_length(self):
    #     for rec in self:
    #         if rec.mobile and len(rec.mobile) > 12:
    #             raise ValidationError(_("Mobile number cannot exceed 11 digits."))
    #         if rec.phone and len(rec.phone) > 12:
    #             raise ValidationError(_("Phone number cannot exceed 11 digits."))

    # def _onchange_payment_plan_id(self):
    #     """ Generate installments from payment plan when selected """
    #     for rec in self:
    #         rec.installment_ids = [(5, 0, 0)]
    #
    #         if not rec.payment_id:
    #             continue
    #
    #         plan = rec.payment_id
    #         sale_price = rec.property_id.unit_price or 0.0
    #         discounted_price = sale_price - (sale_price * (plan.discount / 100.0))
    #
    #         down_payment = discounted_price * (plan.down_payment_percentage / 100.0)
    #         remaining_after_down = discounted_price - down_payment
    #         annual_amount = remaining_after_down * (plan.annual_payment_percentage / 100.0)
    #         amount_to_be_installed = remaining_after_down - (annual_amount * plan.payment_duration)
    #         multiplier = {
    #             'monthly': 12,
    #             'quarterly': 4,
    #             'semi_annually': 2,
    #         }.get(plan.payment_frequency, 0)
    #
    #         no_of_installments = plan.payment_duration * multiplier
    #         amount_per_installment = amount_to_be_installed / no_of_installments if no_of_installments else 0.0
    #
    #         lines = []
    #         current_date = plan.payment_start_date
    #         seq = 0
    #
    #         if down_payment > 0:
    #             lines.append((0, 0, {
    #                 'serial_number': seq,
    #                 'name': "Down Payment",
    #                 'capital_repayment': down_payment,
    #                 'remaining_capital': remaining_after_down,
    #                 'collection_status': 'not_due',
    #                 'collection_date': plan.payment_start_date,
    #             }))
    #             seq += 1
    #
    #         interval_months = {
    #             'monthly': 1,
    #             'quarterly': 3,
    #             'semi_annually': 6,
    #         }.get(plan.payment_frequency, 1)
    #
    #         for i in range(1, no_of_installments + 1):
    #             current_date += relativedelta(months=interval_months)
    #             lines.append((0, 0, {
    #                 'serial_number': seq,
    #                 'name': f"Periodic Installment {i}",
    #                 'capital_repayment': amount_per_installment,
    #                 'remaining_capital': remaining_after_down - (i * amount_per_installment),
    #                 'collection_status': 'not_due',
    #                 'collection_date': current_date,
    #             }))
    #             seq += 1
    #
    #         if plan.annual_payment_percentage > 0:
    #             for i in range(1, plan.payment_duration + 1):
    #                 lines.append((0, 0, {
    #                     'serial_number': seq,
    #                     'name': f"Annual Installment {i}",
    #                     'capital_repayment': annual_amount,
    #                     'remaining_capital': remaining_after_down - (i * annual_amount),
    #                     'collection_status': 'not_due',
    #                     'collection_date': plan.payment_start_date + relativedelta(years=i),
    #                 }))
    #                 seq += 1
    #
    #         rec.installment_ids = lines

    # @api.constrains('mobile', 'phone')
    # def _check_phone_mobile_length(self):
    #     for rec in self:
    #         if rec.mobile and len(rec.mobile) > 12:
    #             raise ValidationError(_("Mobile number cannot exceed 11 digits."))
    #
    #         if rec.phone and len(rec.phone) > 12:
    #             raise ValidationError(_("Phone number cannot exceed 11 digits."))

    # @api.constrains('mobile', 'phone')
    # def _check_phone_mobile_length(self):
    #     for rec in self:
    #         if rec.mobile:
    #             print(f"Checking mobile: {rec.mobile}, length: {len(rec.mobile)}")
    #             if len(rec.mobile) != 11:
    #                 print("Mobile number is invalid!")
    #                 raise ValidationError(_("Mobile number must be exactly 11 digits."))
    #
    #         if rec.phone:
    #             print(f"Checking phone: {rec.phone}, length: {len(rec.phone)}")
    #             if len(rec.phone) != 11:
    #                 print("Phone number is invalid!")
    #                 raise ValidationError(_("Phone number must be exactly 11 digits."))


class CrmLeadInstallment(models.Model):
    _name = "crm.lead.installment"
    _description = "CRM Lead Installment"

    lead_id = fields.Many2one("crm.lead", string="Lead", ondelete="cascade")
    name = fields.Char(string="Description")
    serial_number = fields.Integer(string="Serial Number")
    capital_repayment = fields.Float(string="Installment Amount")
    remaining_capital = fields.Float(string="Remaining Capital")

    collection_status = fields.Selection(
        [
            ("not_due", "Not Due"),
            ("collected", "Collected"),
            ("pending", "Pending")
        ],
        string="Collection Status",
        default="not_due"
    )
    collection_amount = fields.Float(string="Collected Amount")
    collection_date = fields.Date(string="Collection Date")
