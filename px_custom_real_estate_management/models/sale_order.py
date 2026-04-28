from odoo import models, api, _, fields
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError



class SaleOrder(models.Model):
    _inherit = "sale.order"


    installment_count = fields.Integer(
        string="Installment Invoices",
        compute="_compute_installment_count"
    )
    installment_invoice_created = fields.Boolean(default=False, copy=False)

    property_id = fields.Many2one('property.property', string="Property")
    payment_id = fields.Many2one('payment.plane', string="Payment Plan")
    installment_line_ids = fields.One2many('sale.order.installment.line', 'sale_order_id', string="Installment Lines", copy=False)

    so_installment_invoice_count = fields.Integer(
        string="SO Installment Invoices",
        compute="_compute_so_installment_invoice_count"
    )
    installment_start_date = fields.Date(
        string="Installment Start Date",
        default=lambda self: fields.Date.today(),
        help="Start date for installment schedule generation. Defaults to the order date."
    )
    maintenance_date = fields.Date(
        string="Maintenance Date",
        help="Date of maintenance installment"
    )
    property_maintenance_value = fields.Float(string="Maintenance Value",
                                              related="property_id.maintenance_value",
                                              store=True,)
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

    @api.onchange('date_order')
    def _onchange_date_order_set_installment_start(self):
        for order in self:
            if not order.installment_start_date and order.date_order:
                order.installment_start_date = order.date_order.date()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'installment_start_date' not in vals and vals.get('date_order'):
                from datetime import datetime
                date_order = vals['date_order']
                if isinstance(date_order, str):
                    date_order = datetime.fromisoformat(date_order).date()
                elif hasattr(date_order, 'date'):
                    date_order = date_order.date()
                vals['installment_start_date'] = date_order
        records = super().create(vals_list)
        for order in records:
            if order.property_id and order.payment_id:
                order._onchange_payment_plan()
        return records

    def write(self, vals):
        res = super().write(vals)
        for order in self:
            if 'property_id' in vals or 'payment_id' in vals or 'installment_start_date' in vals:
                order._onchange_payment_plan()
        return res

    @api.onchange('property_id', 'payment_id', 'maintenance_date', 'installment_start_date')
    def _onchange_payment_plan(self):
        for order in self:

            order.installment_line_ids = [(5, 0, 0)]

            if not order.payment_id:
                continue

            plan = order.payment_id
            start_date = order.installment_start_date or (
                order.date_order.date() if order.date_order else fields.Date.context_today(order)
            )
            total_amount = sum(line.price_unit * line.product_uom_qty for line in order.order_line)

            if not total_amount:
                continue


            discounted_price = total_amount - (total_amount * (plan.discount / 100.0))
            down_payment = discounted_price * (plan.down_payment_percentage / 100.0)
            remaining_after_down = discounted_price - down_payment

            annual_total_amount = discounted_price * (plan.annual_payment_percentage / 100.0)

            total_months = plan.payment_duration_months or 0

            if total_months <= 0:
                continue

            interval_months = {
                'monthly': 1,
                'quarterly': 3,
                'semi_annually': 6
            }.get(plan.payment_frequency, 1)

            no_of_periodic_installments = total_months // interval_months
            remaining_months = total_months % interval_months

            annual_count = total_months // 12



            amount_per_periodic = remaining_after_down - annual_total_amount
            amount_per_installment = amount_per_periodic / no_of_periodic_installments if no_of_periodic_installments else 0

            lines = []
            seq = 1
            current_date = start_date
            uom_id = order.order_line[0].product_uom_id.id if order.order_line else False

            if down_payment > 0:
                lines.append((0, 0, {
                    'sequence': seq,
                    'name': 'Down Payment',
                    'capital_repayment': round(down_payment, 2),
                    'remaining_capital': round(remaining_after_down, 2),
                    'collection_status': 'not_due',
                    'collection_date': start_date,
                    'uom_id': uom_id,
                }))
                seq += 1

            for i in range(1, no_of_periodic_installments + 1):
                current_date += relativedelta(months=interval_months)
                lines.append((0, 0, {
                    'sequence': seq,
                    'name': f'Periodic Installment {i}',
                    'capital_repayment': round(amount_per_installment, 2),
                    'remaining_capital': round(remaining_after_down - (i * amount_per_installment), 2),
                    'collection_status': 'not_due',
                    'collection_date': current_date,
                    'uom_id': uom_id,
                }))
                seq += 1

            if remaining_months > 0:
                current_date += relativedelta(months=remaining_months)
                lines.append((0, 0, {
                    'sequence': seq,
                    'name': 'Last Partial Installment',
                    'capital_repayment': round(amount_per_installment, 2),
                    'remaining_capital': 0.0,
                    'collection_status': 'not_due',
                    'collection_date': current_date,
                    'uom_id': uom_id,
                }))
                seq += 1

            total_months = plan.payment_duration_months or 0
            annual_count = plan.annual_installments_count or 0

            if annual_count > 0 and total_months > 0:
                for i in range(1, annual_count + 1):
                    lines.append((0, 0, {
                        'sequence': seq,
                        'name': f'Annual Installment {i}',
                        'capital_repayment': round(annual_total_amount / annual_count, 2),
                        'remaining_capital': round(
                            remaining_after_down - ((i * annual_total_amount) / annual_count), 2),
                        'collection_status': 'not_due',
                        'collection_date': start_date + relativedelta(years=i),
                        'uom_id': uom_id,
                    }))
                    seq += 1
            maintenance_value = discounted_price * (plan.maintenance_percentage / 100.0) \
                if hasattr(plan, 'maintenance_percentage') else 0.0

            if maintenance_value > 0:
                maintenance_months = plan.maintenance_after_months or 0
                maintenance_date = start_date + relativedelta(months=maintenance_months)

                lines.append((0, 0, {
                    'sequence': seq,
                    'name': 'Maintenance Installment',
                    'capital_repayment': round(maintenance_value, 2),
                    'remaining_capital': 0.0,
                    'collection_status': 'not_due',
                    'collection_date': maintenance_date,
                    'uom_id': uom_id,
                }))
                seq += 1

            for i, line in enumerate(lines):
                line[2]['sequence'] = i + 1

            for r in lines:
                d = r[2]

            order.installment_line_ids = lines



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

    # @api.depends('installment_count', 'installment_invoice_created')
    # def _compute_installment_exist(self):
    #     for order in self:
    #         order.installment_invoice_exist = order.installment_count > 0 or order.installment_invoice_created


    def action_create_installment_invoices_from_so(self):
        """Create invoices for each installment of the Sale Order."""
        AccountMove = self.env['account.move']
        created_invoices = AccountMove

        down_payment_account = self.env['account.account'].search(
            [('name', '=', 'دفعات حجز من العملاء')], limit=1
        )

        for order in self:
            if not order.installment_line_ids:
                continue

            order_invoices = AccountMove

            for line in order.installment_line_ids:
                if line.collection_status == 'collected':
                    continue

                invoice_vals = order._prepare_invoice() or {}

                invoice_line_vals = {
                    'product_id': order.order_line[0].product_id.id if order.order_line else False,
                    'quantity': 1,
                    'price_unit': line.capital_repayment,
                    'name': line.name,
                    'product_uom_id': line.uom_id.id if line.uom_id else False,
                }

                if line.name == 'Down Payment' and down_payment_account:
                    invoice_line_vals['account_id'] = down_payment_account.id

                invoice_date = line.collection_date or fields.Date.today()
                invoice_vals.update({
                    'move_type': 'out_invoice',
                    'invoice_date': invoice_date,
                    'invoice_date_due': invoice_date,
                    'invoice_payment_term_id': False,
                    'sale_order_id': order.id,
                    'sale_order_installment_id': line.id,
                    'invoice_line_ids': [(0, 0, invoice_line_vals)],
                })

                invoice = AccountMove.create(invoice_vals)
                order_invoices |= invoice

            if order_invoices:
                order.installment_invoice_created = True
                created_invoices |= order_invoices

        return {
            'type': 'ir.actions.act_window',
            'name': 'SO Installment Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_invoices.ids)],
        }

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
                        'invoice_date_due': installment.collection_date,
                        'invoice_payment_term_id': False,
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
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    property_product_id = fields.Many2one('property.property', string="Property")
    property_maintenance_value = fields.Float(string="Property Maintenance Value",related="property_product_id.maintenance_value")

    def action_view_related_property(self):
        self.ensure_one()
        if not self.property_product_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _('Related Property'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.property',
            'res_id': self.property_product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    property_product_id = fields.Many2one('property.property', string="Property")
    property_maintenance_value = fields.Float(string="Property Maintenance Value",related="property_product_id.maintenance_value")


    def action_view_related_property(self):
        self.ensure_one()
        if not self.property_product_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _('Related Property'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.property',
            'res_id': self.property_product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


