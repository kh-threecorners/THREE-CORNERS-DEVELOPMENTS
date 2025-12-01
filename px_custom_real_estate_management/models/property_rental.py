from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class PropertyRental(models.Model):
    """A class for the model property rental to represent
    the rental order of a property"""
    _inherit = 'property.rental'

    rent_type = fields.Selection([
        ('month','Month'),
        ('3 month','3 Month'),
        ('6 month','6 Month'),
    ])
    monthly_rent = fields.Float(string='Monthly Rent', required=True)
    security_deposit = fields.Float(string='Security Deposit', required=True)
    contract_date = fields.Date(string='Contract Date', required=True)
    confirmation_date = fields.Date(string='Confirmation Date', required=True)
    duration = fields.Integer(string='Duration By Month', compute='_compute_duration', store=True)
    installment_ids = fields.One2many('property.rental.installment', 'rental_id', string="Installments")
    repairs_ids = fields.One2many('property.rental.repair', 'rep_rental_id', string="Repairs")

    def action_print_contract(self):
        return self.env.ref('px_custom_real_estate_management.property_rental_contract_report').report_action(self)

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                delta = relativedelta(rec.end_date, rec.start_date)
                rec.duration = delta.years * 12 + delta.months
            else:
                rec.duration = 0

    @api.onchange('monthly_rent', 'duration', 'start_date', 'rent_type')
    def _generate_installments(self):
        for rec in self:
            if rec.monthly_rent and rec.duration and rec.start_date and rec.rent_type:

                # Clear old lines
                rec.installment_ids = [(5, 0, 0)]

                interval_map = {
                    'month': 1,
                    '3 month': 3,
                    '6 month': 6,
                }
                months_interval = interval_map.get(rec.rent_type, 1)

                num_installments = rec.duration // months_interval

                lines = []
                for i in range(num_installments):
                    lines.append((0, 0, {
                        'installment_date': fields.Date.add(rec.start_date, months=i * months_interval),
                        'amount': rec.monthly_rent,
                    }))

                rec.installment_ids = lines

    # def action_generate_installment_invoices(self):
    #     for rec in self:
    #         pending_installments = rec.installment_ids.filtered(lambda i: i.state == 'un_paid')
    #         if not pending_installments:
    #             raise ValidationError(_("No pending installments to invoice."))
    #
    #         for installment in pending_installments:
    #             invoice = self.env['account.move'].create({
    #                 'move_type': 'out_invoice',
    #                 'partner_id': rec.renter_id.id,
    #                 'invoice_date': installment.installment_date,
    #                 'invoice_line_ids': [(0, 0, {
    #                     'name': f'Installment for {rec.name} - {installment.installment_date}',
    #                     'price_unit': installment.amount,
    #                 })],
    #                 'property_rental_id': rec.id,
    #             })
    #
    #             installment.invoice_id = invoice.id
    #
    #
    #     return True

    def action_generate_installment_invoices(self):
        invoices = self.env['account.move']
        for rec in self:
            pending_installments = rec.installment_ids.filtered(lambda i: i.state == 'un_paid')
            if not pending_installments:
                raise ValidationError(_("No pending installments to invoice."))

            for installment in pending_installments:
                invoice = self.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'partner_id': rec.renter_id.id,
                    'invoice_date': installment.installment_date,
                    'invoice_line_ids': [(0, 0, {
                        'name': f'Installment for {rec.name} - {installment.installment_date}',
                        'price_unit': installment.amount,
                    })],
                    'property_rental_id': rec.id,
                })

                installment.invoice_id = invoice.id
                invoices |= invoice  # نجمع الفواتير اللي اتعملت

        # لو اتعملت فاتورة واحدة → افتحها مباشرة
        if len(invoices) == 1:
            return {
                'name': _('Installment Invoice'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': invoices.id,
            }

        # لو أكتر من فاتورة → افتحهم في List View
        return {
            'name': _('Installment Invoices'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', invoices.ids)],
        }

    def action_security_deposit_invoice(self):
        for rec in self:
            if not rec.security_deposit or rec.security_deposit <= 0:
                raise ValidationError(_("No security deposit amount defined."))

            existing_deposit_invoice = self.env['account.move'].search([
                ('property_rental_id', '=', rec.id),
                ('move_type', '=', 'out_invoice'),
                ('invoice_line_ids.name', 'ilike', 'Security Deposit'),
            ], limit=1)

            if existing_deposit_invoice:
                raise ValidationError(_("Security deposit invoice already exists."))

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.renter_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, {
                    'name': f'Security Deposit for {rec.name}',
                    'price_unit': rec.security_deposit,
                })],
                'property_rental_id': rec.id,
            })

            return {
                'name': _('Security Deposit Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
            }

    def action_generate_repair_invoices(self):
        for rec in self:
            pending_repairs = rec.repairs_ids.filtered(lambda r: r.state == 'un_paid')
            if not pending_repairs:
                raise ValidationError(_("No pending repairs to invoice."))

            invoice_lines = []
            for repair in pending_repairs:
                invoice_lines.append((0, 0, {
                    'name': f'Repair: {repair.repair_name}',
                    'price_unit': repair.repair_cost,
                }))
                repair.state = 'invoiced'

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.renter_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'property_rental_id': rec.id,
            })

            return {
                'name': _('Repair Invoice'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': invoice.id,
            }


class PropertyRentalInstallment(models.Model):
    _name = 'property.rental.installment'
    _description = 'Property Rental Installment'

    rental_id = fields.Many2one('property.rental', string="Rental", ondelete="cascade")
    installment_date = fields.Date(string="Installment Date")
    amount = fields.Float(string="Amount")
    state = fields.Selection([
        ('un_paid', 'Un Paid'),
        ('paid', 'Paid'),
    ], default='un_paid')
    renter_id = fields.Many2one('res.partner', string="Renter", related='rental_id.renter_id', store=True,
                                readonly=True)
    property_id = fields.Many2one('property.property', string="Property", related='rental_id.property_id', store=True,
                                  readonly=True)
    invoice_id = fields.Many2one('account.move', string="Invoice", readonly=True)

class PropertyRentalRepair(models.Model):
    _name = 'property.rental.repair'
    _description = 'Property Rental Repairs'

    rep_rental_id = fields.Many2one('property.rental', string="Rental", ondelete="cascade")
    repair_name = fields.Char(string="Maintenance Name", required=True)
    repair_cost = fields.Float(string="Maintenance Cost", required=True)
    state = fields.Selection([
        ('un_paid', 'Un Paid'),
        ('invoiced', 'Invoiced'),
    ], default='un_paid', readonly=True)

