from odoo import models, api, _, fields
from dateutil.relativedelta import relativedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"


    installment_count = fields.Integer(
        string="Installment Invoices",
        compute="_compute_installment_count"
    )
    installment_invoice_created = fields.Boolean(default=False)
    installment_invoice_exist = fields.Boolean(
        string="Has Installment Invoices",
        compute="_compute_installment_exist"
    )
    property_id = fields.Many2one('property.property', string="Property")
    payment_id = fields.Many2one('payment.plane', string="Payment Plan")
    installment_line_ids = fields.One2many('sale.order.installment.line', 'sale_order_id', string="Installment Lines")

    so_installment_invoice_count = fields.Integer(
        string="SO Installment Invoices",
        compute="_compute_so_installment_invoice_count"
    )
    property_sale_id = fields.Many2one('property.sale', string="Property Sale")
    @api.depends('installment_line_ids')
    def _compute_so_installment_invoice_count(self):
        for order in self:
            count = self.env['account.move'].search_count([
                ('sale_order_installment_id.sale_order_id', '=', order.id)
            ])
            order.so_installment_invoice_count = count


    @api.depends('order_line', 'installment_invoice_created')
    def _compute_installment_count(self):
        for order in self:
            count = self.env['account.move'].search_count([
                ('sale_order_id', '=', order.id),
                ('installment_id', '!=', False)
            ])
            order.installment_count = count

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for order in records:
            if order.property_id and order.payment_id:
                order._onchange_payment_plan()
        return records

    def write(self, vals):
        res = super().write(vals)
        for order in self:
            if 'property_id' in vals or 'payment_id' in vals:
                order._onchange_payment_plan()
        return res

    @api.onchange('property_id', 'payment_id')
    def _onchange_payment_plan(self):
        for order in self:
            order.installment_line_ids = [(5, 0, 0)]
            if not order.property_id or not order.payment_id:
                continue

            plan = order.payment_id
            unit_price = order.property_id.unit_price or 0.0
            discounted_price = unit_price - (unit_price * (plan.discount / 100.0))
            down_payment = discounted_price * (plan.down_payment_percentage / 100.0)
            remaining_after_down = discounted_price - down_payment
            annual_amount = remaining_after_down * (plan.annual_payment_percentage / 100.0)
            amount_to_be_installed = remaining_after_down - (annual_amount * plan.payment_duration)

            multiplier = {'monthly': 12, 'quarterly': 4, 'semi_annually': 2}.get(plan.payment_frequency, 0)
            no_of_installments = plan.payment_duration * multiplier
            amount_per_installment = amount_to_be_installed / no_of_installments if no_of_installments else 0

            lines = []
            seq = 1
            current_date = plan.payment_start_date

            if down_payment > 0:
                lines.append((0, 0, {
                    'sequence': seq,
                    'name': 'Down Payment',
                    'capital_repayment': down_payment,
                    'remaining_capital': remaining_after_down,
                    'collection_status': 'not_due',
                    'collection_date': plan.payment_start_date,
                }))
                seq += 1

            interval_months = {'monthly': 1, 'quarterly': 3, 'semi_annually': 6}.get(plan.payment_frequency, 1)
            for i in range(1, no_of_installments + 1):
                current_date += relativedelta(months=interval_months)
                lines.append((0, 0, {
                    'sequence': seq,
                    'name': f'Periodic Installment {i}',
                    'capital_repayment': amount_per_installment,
                    'remaining_capital': remaining_after_down - (i * amount_per_installment),
                    'collection_status': 'not_due',
                    'collection_date': current_date,
                }))
                seq += 1

            for i in range(1, plan.payment_duration + 1):
                lines.append((0, 0, {
                    'sequence': seq,
                    'name': f'Annual Installment {i}',
                    'capital_repayment': annual_amount,
                    'remaining_capital': remaining_after_down - (i * annual_amount),
                    'collection_status': 'not_due',
                    'collection_date': plan.payment_start_date + relativedelta(years=i),
                }))
                seq += 1

            maintenance_value = order.property_id.maintenance_value or 0.0
            if maintenance_value > 0:
                last_date = lines[-1][2]['collection_date'] if lines else plan.payment_start_date
                lines.append((0, 0, {
                    'sequence': seq,
                    'name': 'Maintenance',
                    'capital_repayment': maintenance_value,
                    'remaining_capital': 0.0,
                    'collection_status': 'not_due',
                    'collection_date': last_date + relativedelta(days=1),
                }))

            order.installment_line_ids = lines



    @api.onchange('property_id')
    def _onchange_property_add_product(self):
        for order in self:
            if order.property_id and order.property_id.product_id:
                product = order.property_id.product_id
                order.order_line = [(5, 0, 0)]
                order.order_line = [(0, 0, {
                    'product_id': product.id,
                    'name': product.name,
                    'product_uom_qty': 1,
                    'price_unit': order.property_id.unit_price or product.lst_price,
                })]

    @api.depends('installment_count', 'installment_invoice_created')
    def _compute_installment_exist(self):
        for order in self:
            order.installment_invoice_exist = order.installment_count > 0 or order.installment_invoice_created


    def action_create_installment_invoices_from_so(self):
        invoices = self.env['account.move']
        for order in self:
            if order.installment_invoice_exist:
                continue

            for line in order.installment_line_ids:
                if line.collection_status == 'collected':
                    continue

                invoice_vals = order._prepare_invoice()
                invoice_vals.update({
                    'invoice_date': line.collection_date,
                    'sale_order_id': order.id,
                    'sale_order_installment_id': line.id,
                    'invoice_line_ids': [(0, 0, {
                        'product_id': order.order_line[0].product_id.id if order.order_line else False,
                        'quantity': 1,
                        'price_unit': line.capital_repayment,
                        'name': line.name,
                    })],
                })

                invoices |= self.env['account.move'].create(invoice_vals)

            order.installment_invoice_created = True
        return invoices

    def action_create_installment_invoices(self):
        invoices = self.env['account.move']
        for order in self:
            if order.installment_invoice_exist:
                continue

            lead = order.opportunity_id
            if lead and lead.installment_ids:
                for installment in lead.installment_ids:
                    invoice_vals = order._prepare_invoice()
                    invoice_vals.update({
                        'invoice_date': installment.collection_date,
                        'sale_order_id': order.id,
                        'installment_id': installment.id,
                        'invoice_line_ids': [(0, 0, {
                            'product_id': order.order_line[0].product_id.id if order.order_line else False,
                            'quantity': 1,
                            'price_unit': installment.capital_repayment,
                            'name': installment.name,
                        })],
                    })
                    invoices |= self.env['account.move'].create(invoice_vals)

            order.installment_invoice_created = True
        return invoices


    def action_view_installment_invoices(self):
        """Open installment invoices linked to this Sale Order."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Installment Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id), ('installment_id', '!=', False)],
            'context': {'create': False},
        }

    def action_view_so_installment_invoices_so(self):
        """Open invoices created from SO Installments (action_create_installment_invoices_from_so)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'SO Installment Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('sale_order_installment_id.sale_order_id', '=', self.id)],
            'context': {'create': False},
        }


class SaleOrderInstallmentLine(models.Model):
    _name = 'sale.order.installment.line'
    _description = 'Sale Order Installment Line'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade')
    sequence = fields.Integer(string='Seq.')
    name = fields.Char(string='Description')
    capital_repayment = fields.Float(string='Installment Amount')
    remaining_capital = fields.Float(string='Remaining Capital')
    collection_status = fields.Selection([
        ('not_due', 'Not Due'),
        ('collected', 'Collected'),
        ('pending', 'Pending')
    ], string="Collection Status", default='not_due')
    collection_date = fields.Date(string="Collection Date")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    property_product_id = fields.Many2one('property.property', string="Property")
