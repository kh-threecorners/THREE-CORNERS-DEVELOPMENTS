from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    active_payment_plan_id = fields.One2many('payment.plane', 'property_id', string="Active Payment Plan")
    original_state = fields.Selection(
        selection=lambda self: self._fields['state'].selection,
        string="Original State",
        help="The state of the property before temporary reservation"
    )
    landlord_id = fields.Many2one(
        "res.partner", string="Customer", help="The owner of the property"
    )
    installment_line_ids = fields.One2many(
        'payment.installment.line',
        'property_id',
        string="Installments"
    )
    selected_payment_plan_id = fields.Many2one(
        'payment.plane',
        string="Selected Payment Plan",
    )
    temp_reserved_until = fields.Datetime(
        string="Reserved Until",
        help="Datetime until the property is temporarily reserved as sold"
    )
    reservation_duration_hours = fields.Float(
        string="Reservation Duration (Hours)",
        help="How many hours the property should remain reserved. Leave empty or 0 for open reservation.",default=0.0
    )
    state = fields.Selection(selection_add=[ ('draft',), ("under_maintenance", "Under Maintenance"), ("under_construction", "Under Construction")
                                             , ('booked','Booked'), ('hold','Hold')],
                             ondelete={
                                 "under_maintenance": "set default","under_construction": "set default",
                                 "booked": "set default","hold": "set default",
                             })
    product_id = fields.Many2one('product.product', string="Related Product")
    maintenance = fields.Float(
        string="Maintenance",
        help="Enter the percentage of maintenance/repairs from the original price"
    )
    maintenance_value = fields.Float(
        string="Maintenance Value",
        compute='_compute_maintenance_value',
        store=True,
        force=True,
        help="The value of maintenance based on the percentage of the original price"
    )

    sale_order_count = fields.Integer(
        string="Sale Orders",
        compute="_compute_sale_order_count"
    )

    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = self.env['sale.order'].search_count([
                ('origin', '=', rec.name)
            ])

    def action_view_sale_orders(self):
        """Open all Sale Orders related to this property"""
        self.ensure_one()
        return {
            'name': _('Sale Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)],
            'context': {'default_origin': self.name},
        }


    def action_create_booking(self):
        self.ensure_one()
        self.state = 'booked'
        return {
            'name': _('Create Booking'),
            'view_mode': 'form',
            'res_model': 'property.sale',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {
                'default_property_id': self.id,
                'default_project_id': self.property_project_id.id,
                'default_sale_price': self.unit_price,
                'default_is_installment_payment': self.is_installment_payment,
                'default_no_of_installments': self.no_of_installments,
                'default_amount_per_installment': self.amount_per_installment,
            }
        }


    @api.depends('unit_price', 'maintenance')
    def _compute_maintenance_value(self):
        for rec in self:
            if rec.unit_price and rec.maintenance:
                perc = rec.maintenance
                if 0 < perc < 1:
                    perc = perc * 100
                rec.maintenance_value = rec.unit_price * (perc / 100)
            else:
                rec.maintenance_value = 0.0


    def action_set_under_maintenance(self):
        self.write({'state': 'under_maintenance'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_set_under_construction(self):
        self.write({'state': 'under_construction'})
    #
    # def create(self, vals):
    #     record = super(PropertyProperty, self).create(vals)
    #
    #     category = self.env['product.category'].search([('name', '=', 'property')], limit=1)
    #
    #     price = record.unit_price if record.unit_price else 0.0
    #     product_vals = {
    #         'name': record.name,
    #         'list_price': price,
    #         'type': 'service',
    #         'sale_ok': True,
    #         'purchase_ok': False,
    #         'categ_id': category.id if category else False,
    #     }
    #
    #     product = self.env['product.product'].create(product_vals)
    #
    #     # ربط المنتج بالعقار
    #     product.write({'property_product_id': record.id})
    #
    #     record.product_id = product.id
    #
    #     if record.selected_payment_plan_id:
    #         record._onchange_selected_payment_plan_id()
    #
    #     return record

    def create(self, vals):
        record = super(PropertyProperty, self).create(vals)

        category = self.env['product.category'].search([('name', '=', 'property')], limit=1)
        price = record.unit_price or 0.0

        product_vals = {
            'name': record.name,
            'list_price': price,
            'type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
            'categ_id': category.id if category else False,
        }

        # إنشاء المنتج
        product = self.env['product.product'].create(product_vals)

        # ربط المنتج بالعقار على مستوى product.product
        product.write({'property_product_id': record.id})

        # ربط المنتج بالعقار على مستوى product.template
        product.product_tmpl_id.write({'property_product_id': record.id})

        record.product_id = product.id

        # تحديث الأقساط إذا كانت هناك خطة دفع
        if record.selected_payment_plan_id:
            record._onchange_selected_payment_plan_id()

        return record

    def write(self, vals):
        res = super(PropertyProperty, self).write(vals)
        if 'selected_payment_plan_id' in vals or 'unit_price' in vals or 'maintenance' in vals:
            self._onchange_selected_payment_plan_id()
        return res

    @api.model
    def _cron_create_missing_products(self):
        properties = self.search([('product_id', '=', False)])
        category = self.env['product.category'].search([('name', '=', 'property')], limit=1)

        for prop in properties:
            price = prop.unit_price or 0.0
            product_vals = {
                'name': prop.name or 'Unnamed Property',
                'list_price': price,
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                'categ_id': category.id if category else False,
            }

            # إنشاء المنتج
            product = self.env['product.product'].create(product_vals)

            # ربط المنتج بالعقار على مستوى product.product
            product.write({'property_product_id': prop.id})

            # ربط المنتج بالعقار على مستوى product.template
            product.product_tmpl_id.write({'property_product_id': prop.id})

            prop.product_id = product.id

    # @api.model
    # def _cron_create_missing_products(self):
    #     properties = self.search([('product_id', '=', False)])
    #     print(f"🔵 Found {len(properties)} properties without products.")
    #
    #     category = self.env['product.category'].search([('name', '=', 'property')], limit=1)
    #     if category:
    #         print(f"🔹 Using category '{category.name}' with ID {category.id}")
    #     else:
    #         print("⚠ Category 'property' not found. Products will have no category!")
    #
    #     for prop in properties:
    #         price = prop.unit_price or 0.0
    #         print(f"➡ Creating product for property '{prop.name}' (ID {prop.id}) with price {price}")
    #
    #         product_vals = {
    #             'name': prop.name or 'Unnamed Property',
    #             'list_price': price,
    #             'type': 'service',
    #             'sale_ok': True,
    #             'purchase_ok': False,
    #             'categ_id': category.id if category else False,
    #         }
    #
    #         product = self.env['product.product'].create(product_vals)
    #
    #         # ربط المنتج بالعقار
    #         product.write({'property_product_id': prop.id})
    #
    #         prop.product_id = product.id
    #         print(f"✅ Product '{product.name}' (ID {product.id}) created and linked to property '{prop.name}'")

    def action_temp_reserve_sold(self):
        self.ensure_one()
        print(self.reservation_duration_hours)
        if self.state == 'hold' and (
            (self.temp_reserved_until and self.temp_reserved_until > fields.Datetime.now())
            or (not self.temp_reserved_until)
        ):
            raise ValidationError(_("This property is already reserved."))

        vals = {
            'original_state': self.state,
            'state': 'hold',
        }

        if self.reservation_duration_hours and self.reservation_duration_hours > 0:
            vals['temp_reserved_until'] = fields.Datetime.now() + timedelta(hours=self.reservation_duration_hours)
        else:
            vals['temp_reserved_until'] = False

        self.write(vals)

    @api.model
    def _cron_release_temp_reservations(self):
        expired = self.search([
            ('state', '=', 'sold'),
            ('temp_reserved_until', '!=', False),
            ('temp_reserved_until', '<', fields.Datetime.now()),
            ('original_state', '!=', False)
        ])
        for rec in expired:
            rec.write({
                'state': rec.original_state,
                'original_state': False,
                'temp_reserved_until': False,
            })

    @api.onchange('selected_payment_plan_id')
    def _onchange_selected_payment_plan_id(self):
        for rec in self:
            rec.installment_line_ids = [(5, 0, 0)]
            if rec.selected_payment_plan_id:
                plan = rec.selected_payment_plan_id

                discount_amount = rec.unit_price * (plan.discount / 100.0)
                price_after_discount = rec.unit_price - discount_amount

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

                if down_payment > 0:
                    lines.append((0, 0, {
                        'sequence': 0,
                        'name': "Down Payment",
                        'due_date': plan.payment_start_date,
                        'amount': down_payment,
                        'type': 'down',
                    }))

                interval_months = {
                    'monthly': 1,
                    'quarterly': 3,
                    'semi_annually': 6,
                }.get(plan.payment_frequency, 1)

                for i in range(1, no_of_installments + 1):
                    current_date += relativedelta(months=interval_months)
                    lines.append((0, 0, {
                        'sequence': i,
                        'name': f"Periodic Installment {i}",
                        'due_date': current_date,
                        'amount': amount_per_installment,
                        'type': 'periodic',
                    }))

                if plan.annual_payment_percentage > 0:
                    for i in range(1, plan.payment_duration + 1):
                        lines.append((0, 0, {
                            'sequence': no_of_installments + i,
                            'name': f"Annual Installment {i}",
                            'due_date': plan.payment_start_date + relativedelta(years=i),
                            'amount': annual_amount,
                            'type': 'annual',
                        }))

                if rec.maintenance_value and rec.maintenance_value > 0:
                    last_seq = lines[-1][2]['sequence'] if lines else 0
                    last_date = lines[-1][2]['due_date'] if lines else plan.payment_start_date
                    lines.append((0, 0, {
                        'sequence': last_seq + 1,
                        'name': "Maintenance",
                        'due_date': last_date + relativedelta(days=1),
                        'amount': rec.maintenance_value,
                        'type': 'maintenance',
                    }))

                rec.installment_line_ids = lines

    def action_view_related_product(self):
        self.ensure_one()
        if not self.product_id:
            return {
                'type': 'ir.actions.act_window_close'
            }
        return {
            'name': _('Related Product'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class PaymentInstallmentLine(models.Model):
    _name = 'payment.installment.line'
    _description = 'Payment Installment Line'

    property_id = fields.Many2one('property.property', string="Property", ondelete="cascade")
    payment_plane_id = fields.Many2one('payment.plane', string="Payment Plan", ondelete="cascade")

    sequence = fields.Integer(string='Seq.')
    name = fields.Char(string='Description')
    due_date = fields.Date(string="Due Date")
    amount = fields.Float(string="Amount")
    type = fields.Selection([('annual', 'Annual'), ('periodic', 'Periodic'),('maintenance', 'Maintenance'), ('down', 'Down Payment')], string="Type")






