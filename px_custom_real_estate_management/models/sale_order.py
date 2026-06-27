import math

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
    installment_round_step = fields.Integer(
        string="Round To Nearest",
        default=0,
        help="Round each periodic installment amount to the nearest multiple of this number "
             "(e.g. 10, 100, 1000). Leave 0 to keep exact amounts.",
    )
    installment_round_direction = fields.Selection(
        [('up', 'Round Up'), ('down', 'Round Down')],
        string="Rounding Direction",
        default='up',
    )
    installment_total_target = fields.Float(
        string="Installments Target Total",
        copy=False,
        help="The total the installment schedule must add up to. Captured when the "
             "schedule is generated and held fixed while rebalancing.",
    )
    installment_difference = fields.Float(
        string="Difference",
        compute="_compute_installment_difference",
        help="Target total minus the sum of the installment amounts. Should be 0 when "
             "the schedule is balanced; a non-zero value means the lines no longer match "
             "the target (click Rebalance to fix).",
    )

    @api.depends('installment_total_target', 'installment_line_ids.capital_repayment')
    def _compute_installment_difference(self):
        for order in self:
            lines_total = sum(order.installment_line_ids.mapped('capital_repayment'))
            order.installment_difference = round(order.installment_total_target - lines_total, 2)

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
        return records

    def action_generate_installments(self):
        """Button: (re)generate the installment schedule for this order."""
        self.ensure_one()
        if self.installment_invoice_created:
            raise ValidationError(_(
                "Installment invoices have already been created for this order. "
                "Regenerating the schedule would desync those invoices. "
                "Cancel/delete the existing installment invoices first."
            ))
        self._generate_installment_lines()
        return True

    def action_round_installments(self):
        """Button: round periodic installments to the nearest step and recalculate."""
        self.ensure_one()
        if self.installment_invoice_created:
            raise ValidationError(_(
                "Installment invoices have already been created for this order. "
                "Regenerating the schedule would desync those invoices. "
                "Cancel/delete the existing installment invoices first."
            ))
        if not self.installment_round_step or self.installment_round_step <= 0:
            raise ValidationError(_("Set a positive 'Round To Nearest' value before rounding."))
        if not self.installment_round_direction:
            raise ValidationError(_("Select a rounding direction (Up or Down) before rounding."))
        self._generate_installment_lines()
        return True

    def _installment_tax_multiplier(self):
        """After-tax value of one pre-tax currency unit for this order's product line.

        Used to round the *after-tax* installment amount: an amount paid by the
        customer of `x` corresponds to a pre-tax `capital_repayment` of `x / multiplier`.
        Returns 1.0 when the line has no taxes.
        """
        self.ensure_one()
        order_line = self.order_line[:1]
        taxes = order_line.tax_ids
        if not taxes:
            return 1.0
        res = taxes.compute_all(
            1.0,
            currency=self.currency_id,
            quantity=1.0,
            product=order_line.product_id,
            partner=self.partner_id,
        )
        base = res['total_excluded'] or 1.0
        return res['total_included'] / base

    @staticmethod
    def _round_amount_to_step(value, step, direction):
        """Round a single amount up/down to the nearest multiple of step."""
        if not step or step <= 0:
            return value
        ratio = round(value / step, 6)
        if direction == 'up':
            return math.ceil(ratio) * step
        if direction == 'down':
            return math.floor(ratio) * step
        return value

    def _build_periodic_amounts(self, total, default_count, step, direction):
        """Return the list of periodic installment amounts.

        When a rounding step is given, each installment is the rounded unit and
        the number of installments floats (more when rounding down, fewer when
        rounding up); any leftover is added as a final reconciling installment so
        the amounts still sum exactly to `total`.
        """
        total = round(total, 2)
        if default_count <= 0 or total <= 0:
            return []
        unit = self._round_amount_to_step(total / default_count, step, direction)
        if unit <= 0:
            raise ValidationError(_(
                "The rounding step %s is too large to round the installment amount down. "
                "Use a smaller step."
            ) % step)
        full_count = int(total // unit)
        amounts = [float(unit)] * full_count
        remainder = round(total - unit * full_count, 2)
        if remainder > 0.005:
            amounts.append(remainder)
        return amounts

    @staticmethod
    def _absorb_difference(amounts, diff, normal):
        """Push `diff` into the tail of the periodic amounts list.

        diff > 0: grow the last installment up to `normal`; overflow spills into
        new `normal`-sized installments plus a final partial.
        diff < 0: shrink/remove installments from the tail.
        Returns the new list, or None when a negative diff cannot be absorbed
        (it would drive the periodic total below zero).
        """
        P = [round(a, 2) for a in amounts]
        diff = round(diff, 2)
        if abs(diff) < 0.005 or not P:
            return P
        if diff > 0:
            room = round(normal - P[-1], 2)
            if diff <= room + 0.005:
                P[-1] = round(P[-1] + diff, 2)
                return P
            P[-1] = round(normal, 2)
            remaining = round(diff - room, 2)
            while remaining > normal + 0.005:
                P.append(round(normal, 2))
                remaining = round(remaining - normal, 2)
            if remaining > 0.005:
                P.append(remaining)
            return P
        remaining = round(-diff, 2)
        while remaining > 0.005 and P:
            last = P[-1]
            if last > remaining + 0.005:
                P[-1] = round(last - remaining, 2)
                remaining = 0.0
            else:
                remaining = round(remaining - last, 2)
                P.pop()
        if remaining > 0.005:
            return None
        return P

    def action_rebalance_installments(self):
        """Button: hold the target total fixed and push the difference (created by
        editing the down payment / maintenance amount) into the periodic block."""
        self.ensure_one()
        if self.installment_invoice_created:
            raise ValidationError(_(
                "Installment invoices have already been created for this order. "
                "Rebalancing would desync those invoices. "
                "Cancel/delete the existing installment invoices first."
            ))
        if not self.installment_total_target:
            raise ValidationError(_("Generate the installment schedule before rebalancing."))

        all_lines = self.installment_line_ids.sorted('sequence')
        periodic_lines = all_lines.filtered(lambda l: l.line_type == 'periodic')
        if not periodic_lines:
            raise ValidationError(_("There are no periodic installments to absorb the difference."))

        current_sum = round(sum(all_lines.mapped('capital_repayment')), 2)
        diff = round(self.installment_total_target - current_sum, 2)
        if abs(diff) < 0.005:
            return True  # already balanced

        periodic_amounts = periodic_lines.mapped('capital_repayment')
        normal = max(periodic_amounts)
        new_amounts = self._absorb_difference(periodic_amounts, diff, normal)
        if new_amounts is None:
            raise ValidationError(_(
                "The change is larger than the periodic installments can absorb. "
                "Reduce the down payment / maintenance change, or regenerate the schedule."
            ))

        # Dates: reuse existing periodic dates; extend the cadence for any new lines.
        plan = self.payment_id
        interval_months = {
            'monthly': 1,
            'quarterly': 3,
            'semi_annually': 6,
        }.get(plan.payment_frequency, 1) if plan else 1
        existing_dates = periodic_lines.mapped('collection_date')
        periodic_dates = []
        last_date = existing_dates[-1] if existing_dates else (
            self.installment_start_date or fields.Date.context_today(self)
        )
        for idx in range(len(new_amounts)):
            if idx < len(existing_dates):
                periodic_dates.append(existing_dates[idx])
                last_date = existing_dates[idx]
            else:
                last_date = last_date + relativedelta(months=interval_months)
                periodic_dates.append(last_date)

        uom_id = periodic_lines[0].uom_id.id if periodic_lines[0].uom_id else False

        def _keep(line):
            return {
                'name': line.name,
                'line_type': line.line_type,
                'capital_repayment': round(line.capital_repayment, 2),
                'collection_status': line.collection_status,
                'collection_date': line.collection_date,
                'uom_id': line.uom_id.id if line.uom_id else False,
            }

        # Rebuild every line in canonical order: down payment, periodic, annual, maintenance.
        ordered_vals = []
        ordered_vals += [_keep(l) for l in all_lines.filtered(lambda l: l.line_type == 'down_payment')]
        for idx, amount in enumerate(new_amounts):
            ordered_vals.append({
                'name': f'Periodic Installment {idx + 1}',
                'line_type': 'periodic',
                'capital_repayment': round(amount, 2),
                'collection_status': 'not_due',
                'collection_date': periodic_dates[idx],
                'uom_id': uom_id,
            })
        ordered_vals += [_keep(l) for l in all_lines.filtered(lambda l: l.line_type == 'annual')]
        ordered_vals += [_keep(l) for l in all_lines.filtered(lambda l: l.line_type == 'maintenance')]

        # Running remaining balance + sequence.
        running = self.installment_total_target
        commands = [(5, 0, 0)]
        for seq, vals in enumerate(ordered_vals, start=1):
            running = round(running - vals['capital_repayment'], 2)
            vals['sequence'] = seq
            vals['remaining_capital'] = running
            commands.append((0, 0, vals))

        self.installment_line_ids = commands
        return True

    def _generate_installment_lines(self):
        for order in self:

            if not order.payment_id:
                raise ValidationError(_("Please select a Payment Plan before generating installments."))

            plan = order.payment_id
            start_date = order.installment_start_date or (
                order.date_order.date() if order.date_order else fields.Date.context_today(order)
            )
            total_amount = sum(line.price_unit * line.product_uom_qty for line in order.order_line)

            if not total_amount:
                raise ValidationError(_(
                    "Add at least one order line with a price before generating installments."
                ))


            discounted_price = total_amount - (total_amount * (plan.discount / 100.0))
            down_payment = discounted_price * (plan.down_payment_percentage / 100.0)
            remaining_after_down = discounted_price - down_payment

            annual_total_amount = discounted_price * (plan.annual_payment_percentage / 100.0)

            # Total months come from the plan duration (years) plus any extra months.
            # Using only `payment_duration_months` (which defaults to 0) silently skipped
            # all installment generation for most plans.
            total_months = (plan.payment_duration or 0) * 12 + (plan.payment_duration_months or 0)

            if total_months <= 0:
                raise ValidationError(_(
                    "The selected Payment Plan '%s' has no duration set. "
                    "Set a Payment Duration (years or months) on the plan before generating installments."
                ) % plan.name)

            interval_months = {
                'monthly': 1,
                'quarterly': 3,
                'semi_annually': 6
            }.get(plan.payment_frequency, 1)

            no_of_periodic_installments = total_months // interval_months
            remaining_months = total_months % interval_months

            annual_count = total_months // 12



            amount_per_periodic = remaining_after_down - annual_total_amount

            rounding_active = bool(
                order.installment_round_step
                and order.installment_round_step > 0
                and order.installment_round_direction
            )

            lines = [(5, 0, 0)]
            seq = 1
            current_date = start_date
            uom_id = order.order_line[0].product_uom_id.id if order.order_line else False

            if down_payment > 0:
                lines.append((0, 0, {
                    'sequence': seq,
                    'name': 'Down Payment',
                    'line_type': 'down_payment',
                    'capital_repayment': round(down_payment, 2),
                    'remaining_capital': round(remaining_after_down, 2),
                    'collection_status': 'not_due',
                    'collection_date': start_date,
                    'uom_id': uom_id,
                }))
                seq += 1

            if rounding_active:
                # Round the *after-tax* amount the customer pays, then back-solve the
                # pre-tax capital_repayment (= after_tax / tax multiplier).
                multiplier = order._installment_tax_multiplier()
                periodic_after_tax_total = amount_per_periodic * multiplier
                after_tax_amounts = order._build_periodic_amounts(
                    periodic_after_tax_total,
                    no_of_periodic_installments,
                    order.installment_round_step,
                    order.installment_round_direction,
                )
                running_remaining = remaining_after_down
                for idx, after_tax_amount in enumerate(after_tax_amounts, start=1):
                    current_date += relativedelta(months=interval_months)
                    pre_tax_amount = after_tax_amount / multiplier if multiplier else after_tax_amount
                    running_remaining -= pre_tax_amount
                    lines.append((0, 0, {
                        'sequence': seq,
                        'name': f'Periodic Installment {idx}',
                        'line_type': 'periodic',
                        'capital_repayment': round(pre_tax_amount, 2),
                        'remaining_capital': round(running_remaining, 2),
                        'collection_status': 'not_due',
                        'collection_date': current_date,
                        'uom_id': uom_id,
                    }))
                    seq += 1
            else:
                amount_per_installment = amount_per_periodic / no_of_periodic_installments if no_of_periodic_installments else 0

                for i in range(1, no_of_periodic_installments + 1):
                    current_date += relativedelta(months=interval_months)
                    lines.append((0, 0, {
                        'sequence': seq,
                        'name': f'Periodic Installment {i}',
                        'line_type': 'periodic',
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
                        'line_type': 'periodic',
                        'capital_repayment': round(amount_per_installment, 2),
                        'remaining_capital': 0.0,
                        'collection_status': 'not_due',
                        'collection_date': current_date,
                        'uom_id': uom_id,
                    }))
                    seq += 1

            annual_count = plan.annual_installments_count if plan.annual_installments_count > 0 else (plan.payment_duration or 0)

            if annual_total_amount > 0 and annual_count > 0:
                for i in range(1, annual_count + 1):
                    lines.append((0, 0, {
                        'sequence': seq,
                        'name': f'Annual Installment {i}',
                        'line_type': 'annual',
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
                    'line_type': 'maintenance',
                    'capital_repayment': round(maintenance_value, 2),
                    'remaining_capital': 0.0,
                    'collection_status': 'not_due',
                    'collection_date': maintenance_date,
                    'uom_id': uom_id,
                }))
                seq += 1

            seq = 1
            for command in lines:
                if command[0] == 0:
                    command[2]['sequence'] = seq
                    seq += 1

            order.installment_line_ids = lines
            # Capture the total the schedule must always add up to; rebalancing keeps
            # this fixed while shifting the difference into the periodic block.
            order.installment_total_target = round(
                sum(command[2]['capital_repayment'] for command in lines if command[0] == 0), 2
            )



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
    line_type = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('periodic', 'Periodic'),
        ('annual', 'Annual'),
        ('maintenance', 'Maintenance'),
    ], string="Type")
    capital_repayment = fields.Float(string='Installment Amount')
    amount_after_tax = fields.Float(
        string='Amount After Taxes',
        compute='_compute_amount_after_tax',
        store=True,
    )
    remaining_capital = fields.Float(string='Remaining Capital')
    collection_status = fields.Selection([
        ('not_due', 'Not Due'),
        ('collected', 'Collected'),
        ('pending', 'Pending')
    ], string="Collection Status", default='not_due')
    collection_date = fields.Date(string="Collection Date")
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")

    @api.depends('capital_repayment', 'sale_order_id.order_line.tax_ids')
    def _compute_amount_after_tax(self):
        for line in self:
            order = line.sale_order_id
            order_line = order.order_line[:1]
            taxes = order_line.tax_ids
            if taxes and line.capital_repayment:
                res = taxes.compute_all(
                    line.capital_repayment,
                    currency=order.currency_id,
                    quantity=1.0,
                    product=order_line.product_id,
                    partner=order.partner_id,
                )
                line.amount_after_tax = res['total_included']
            else:
                line.amount_after_tax = line.capital_repayment


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


