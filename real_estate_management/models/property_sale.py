# -*- coding: utf-8 -*-
################################################################################
#
#    Kolpolok Ltd. (https://www.kolpolok.com)
#    Author: Kaushik Ahmed Apu, Aqil Mahmud, Zarin Tasnim(<https://www.kolpolok.com>)
#
################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class PropertySale(models.Model):
    """A class for the model property sale to represent
    the sale order of a property"""
    _name = 'property.sale'
    _description = 'Sale of the Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(string='Reference', readonly=True,
                       copy=False, default='New',
                       help='The reference code/sequence of the property sale')
    property_id = fields.Many2one(
        'property.property', required=True,
        domain="[('state', '=', 'available'), ('sale_rent', '=', 'for_sale')]",
        string="Property Name",
        help='The property to be sold')
    project_id = fields.Many2one('property.project', string="Project", help="The project of the property")

    note = fields.Text(string="Note", help="The note of the property")
    property_name = fields.Selection([('Arena', 'Arena')], default='Arena', string="Property Name", help="The name of the property")
    finishing_type = fields.Selection(related='property_id.finishing_type', string="Finishing Type", help="The finishing type of the property")
    property_type = fields.Selection(related='property_id.property_type', string="Property Type", help="The property type of the property")
    floor_number = fields.Char(related='property_id.floor_number', string="Floor Number", help="The floor number of the property")
    model_number = fields.Char(related='property_id.model_number', string="Model Number", help="The model number of the property")
    unit_area = fields.Char(related='property_id.street', string="Unit Area", required=True, help="The unit area of the property")
    client_source = fields.Many2one('res.partner', string="Client Source", help="The client source of the property")
    sales_person = fields.Many2one(related='lead_id.user_id', default='', string="Sales Person", help="The sales person of the property")
    sales_manager = fields.Many2one('res.partner', string="Sales Manager", help="The sales manager of the property")
    broker_company = fields.Many2one('res.company', string="Sales Manager", help="The broker company of the property")

    partner_id = fields.Many2one('res.partner', string="Customer",
                                 required=True,
                                 help='The customer who is buying the property')
    # partner_street = fields.Char(related='partner_id.street', string='Street')
    # partner_street2 = fields.Char(related='partner_id.street2', string='Street 2')
    # partner_zip = fields.Char(related='partner_id.zip', string='Zip')
    # partner_jop = fields.Char(related='partner_id.function',string='Job Position')
    # contact_code = fields.Char(related='partner_id.contact_code',string='Contact Code')
    # partner_city = fields.Char(related='partner_id.city',string='City')
    # partner_state_id = fields.Many2one(related='partner_id.state_id',string='State')
    # partner_country_id = fields.Many2one(related='partner_id.country_id',string='Country')
    # partner_email = fields.Char(related='partner_id.email', string="Email")
    # partner_phone = fields.Char(related='partner_id.phone', string="Phone")
    # partner_mobile = fields.Char(related='partner_id.mobile',string="Mobile")
    # id_number = fields.Char(related='partner_id.id_number', string="Id Number")
    order_date = fields.Date(string="Order Date",
                             help='The order date of property')
    state = fields.Selection([('draft', 'Draft'), ('invisible', ''),('proposed','Proposed'),('confirm', 'Confirm'),('cancel','Cancel')],
                             default='draft', string="State", tracking=True, domain=lambda self: [('state', '!=', 'invisible')])
    invoice_id = fields.Many2one('account.move', readonly=True,
                                 string="Invoice",
                                 help='The invoice reference for the property')
    invoiced = fields.Boolean(string='Invoiced',
                              help='Is the property sale invoiced')
    billed = fields.Boolean(string='Commission Billed',
                            help='Is the commission given for this property '
                                 'sale')
    sale_price = fields.Monetary(string="Sale Price", readonly=False,
                                 related='property_id.unit_price',
                                 help='The price of the property')
    discount = fields.Float(string="Discount (%)", default=0.0,computed='_onchange_discount',
                            help='The discount percentage for the property sale', readonly=True)
    price_after_discount = fields.Monetary(
        string="Price After Discount",
        store=True,
        help='The price of the property after applying the discount.',
    )

    # price_after_discount = fields.Monetary(string="Price After Discount",
    #                                        compute='_compute_price_after_discount',
    #                                        store=True,
    #                                        help='The price of the property after applying the discount.')
    paid = fields.Monetary(string='Paid', default=0.0)
    remaining = fields.Monetary(string='Remaining', compute='_compute_remaining', store=True)
    reservation_date = fields.Date(string='Reservation Date', default=datetime.now())
    completion_date = fields.Date(string='Completion Date')
    payment_method = fields.Selection([('cash', 'Cash'),
                                       ('visa', 'visa')],
                                      string='Payment Method')
    any_broker = fields.Boolean(string='Any Broker',
                                help="Enable if this sale have a Broker")
    broker_id = fields.Many2one('res.partner', string="Broker name",
                                help='The broker for this property sale')
    commission_plan_id = fields.Many2one('property.commission',
                                         string="Commission Plan",
                                         help="Select the Commission Plan for "
                                              "the broker")
    commission_type = fields.Char(
        compute='_compute_commission_and_commission_type',
        string="Commission Type",
        help='The type of the commission')
    commission = fields.Monetary(string='Commission',
                                 compute='_compute_commission_and_commission_type',
                                 help='THe amount of commission')
    company_id = fields.Many2one('res.company',
                                 string="Property Management Company",
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  related='company_id.currency_id',
                                  required=True)
    is_installment_payment = fields.Boolean(string="Installment Payment", readonly=False,
                                 related='property_id.is_installment_payment',
                                 help='The price of the property')
    no_of_installments = fields.Integer(string="Number of Installments", related='property_id.no_of_installments')
    amount_per_installment = fields.Float(string="Amount Per Installment", related='property_id.amount_per_installment')
    property_sale_line_ids = fields.One2many('property.sale.line', 'property_sale_id', string="Property Sale Line")
    day_of_week = fields.Char(string="Day of the Week", compute='_compute_day_of_week', store=True)
    # partner_nationality = fields.Char(related='partner_id.nationality', string='Nationality', readonly=True)
    lead_id = fields.Many2one('crm.lead', string='Originating Lead', readonly=True,
                              help="The lead from which this booking was created.")

    def action_view_lead(self):
        self.ensure_one()
        return {
            'name': _('Originating Lead'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.lead_id.id,
        }


    @api.depends('reservation_date')
    def _compute_day_of_week(self):
        days_in_arabic = {
            'Monday': 'الاثنين',
            'Tuesday': 'الثلاثاء',
            'Wednesday': 'الأربعاء',
            'Thursday': 'الخميس',
            'Friday': 'الجمعة',
            'Saturday': 'السبت',
            'Sunday': 'الأحد'
        }
        for rec in self:
            if rec.reservation_date:
                day_name = rec.reservation_date.strftime('%A')
                rec.day_of_week = days_in_arabic.get(day_name, day_name)
            else:
                rec.day_of_week = ''


    @api.depends('sale_price', 'paid')
    def _compute_remaining(self):
        """
        Computes the remaining amount to be paid.
        """
        for rec in self:
            rec.remaining = rec.price_after_discount - rec.paid


    # @api.depends('sale_price', 'discount')
    # def _compute_price_after_discount(self):
    #     """
    #     Calculates the price after applying the discount percentage.
    #     """
    #     for rec in self:
    #         if rec.discount < 0 or rec.discount > 100:
    #             raise ValidationError(_("Discount percentage must be between 0 and 100."))
    #
    #         discount_amount = (rec.sale_price * rec.discount) / 100
    #         rec.price_after_discount = rec.sale_price - discount_amount

    @api.onchange('price_after_discount', 'sale_price')
    def _onchange_discount(self):
        for rec in self:
            if rec.sale_price > 0:
                rec.discount = round((rec.sale_price - rec.price_after_discount) / rec.sale_price * 100, 2)
            else:
                rec.discount = 0

    @api.model
    def create(self, vals_list):
        records = []
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('property.sale') or 'New'

            rec = super(PropertySale, self).create(vals)
            records.append(rec)

        return records[0] if len(records) == 1 else records

    @api.depends('commission_plan_id', 'sale_price')
    def _compute_commission_and_commission_type(self):
        """Calculate commission based on commission plan and sale price"""
        for rec in self:
            rec.commission_type = rec.commission_plan_id.commission_type
            if rec.commission_plan_id.commission_type == 'fixed':
                rec.commission = rec.commission_plan_id.commission
            else:
                rec.commission = (rec.sale_price *
                                  rec.commission_plan_id.commission / 100)

    def create_invoice(self):
        """Generate Invoice Based on the Monetary Values and return
        Invoice Form View"""
        self.invoiced = True
        return {
            'name': _('Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {
                'default_move_type': 'out_invoice',
                'default_company_id': self.env.user.company_id.id,
                'default_partner_id': self.partner_id.id,
                'default_property_order_id': self.id,
                'default_invoice_line_ids': [fields.Command.create({
                    'name': self.property_id.name,
                    'price_unit': self.sale_price,
                    'currency_id': self.env.user.company_id.currency_id.id,
                })]
            }
        }

    def commission_bill(self):
        """Generate Bills Based on the Monetary Values and return
            Bills Form View"""
        self.billed = True
        return {
            'name': _('Commission Bill'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {
                'default_move_type': 'in_invoice',
                'default_company_id': self.env.user.company_id.id,
                'default_partner_id': self.broker_id.id,
                'default_property_order_id': self.id,
                'default_invoice_line_ids': [fields.Command.create({
                    'name': self.property_id.name,
                    'price_unit': self.commission,
                    'currency_id': self.env.user.company_id.currency_id.id,
                })]
            }
        }

    def action_view_invoice(self):
        """Return Invoices Tree View"""
        return {
            'name': _('Invoices'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain': [('property_order_id', '=', self.id),
                       ('move_type', '=', 'out_invoice')]
        }

    def action_view_commission_bill(self):
        """Return Bills Tree View"""
        return {
            'name': _('Commission Bills'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain': [('property_order_id', '=', self.id),
                       ('move_type', '=', 'in_invoice')]
        }

    def action_confirm(self):
        """Confirm the sale order and Change necessary fields"""
        if self.partner_id.blacklisted:
            raise ValidationError(
                _('The Customer %r is Blacklisted.', self.partner_id.name))
        self.state = 'confirm'
        self.property_id.state = 'sold'
        self.property_id.sale_id = self.id

    def action_propose(self):
        """Sets the state to 'proposed', post message in chatter, and create activity for Property Managers."""
        property_manager_group = self.env.ref('real_estate_management.group_property_manager')
        manager_users = property_manager_group.user_ids.sudo()

        for rec in self:
            rec.state = 'proposed'

            rec.message_post(
                body='Installment proposed for this booking.',
                subtype_xmlid='mail.mt_comment',
            )

            for manager in manager_users:
                rec.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    user_id=manager.id,
                    note=f'Installment proposed for booking {rec.name}. Please review.',
                )

    @api.onchange('is_installment_payment', 'no_of_installments', 'paid', 'price_after_discount')
    def onchange_installment(self):
        """ This method is used to compute the installment amortization line
            based on price_after_discount minus advance (paid). """
        if self.is_installment_payment and self.no_of_installments > 0:
            self.property_sale_line_ids = [(5, 0, 0)]

            remaining_amount = self.price_after_discount - self.paid

            # if remaining_amount <= 0:
            #     raise ValidationError(_("Remaining amount must be greater than zero to generate installments."))

            installment_value = remaining_amount / self.no_of_installments

            property_sale_line_ids = []
            for i in range(1, self.no_of_installments + 1):
                property_sale_line_ids.append((0, 0, {
                    'serial_number': i,
                    'capital_repayment': installment_value,
                    'remaining_capital': remaining_amount - (installment_value * i),
                }))

            self.property_sale_line_ids = property_sale_line_ids


    # @api.onchange('is_installment_payment')
    # def onchange_installment(self):
    #     ''' This method is used to compute the installment amortization line '''
    #     if self.is_installment_payment:
    #         self.property_sale_line_ids = [(5, 0, 0)]
    #         property_sale_line_ids = []
    #         for i in range(1, self.no_of_installments + 1):
    #             property_sale_line_ids.append((0, 0, {
    #                 'serial_number': i,
    #                 'capital_repayment': self.amount_per_installment,
    #                 'remaining_capital': self.sale_price - (self.amount_per_installment * i),
    #                 }))
    #         self.property_sale_line_ids = property_sale_line_ids
    #
    @api.onchange('property_id',  'property_sale_line_ids')
    def onchange_show_confirm(self):
        if self.is_installment_payment:
            total_amount = 0.00
            self.state = 'invisible'
            if self.property_sale_line_ids:
                for rec in self.property_sale_line_ids:
                    total_amount += rec.collection_amount
                if self.sale_price == round(total_amount, 1):
                    self.state = 'draft'
                else:
                    self.state = 'invisible'
        else:
            self.state = 'draft'



class PropertySaleLine(models.Model):
    """A class for the model property sale line to represent
    the installment payment of a property"""
    _name = 'property.sale.line'
    _description = 'Sale of the Property'
    _order = 'id'
    
    property_sale_id = fields.Many2one('property.sale', string="Property Sale")
    name = fields.Integer(string='Installment No')
    serial_number = fields.Integer(string='Installment No')
    remaining_capital = fields.Float(string='Remaining Capital')
    capital_repayment = fields.Float(string='Capital Repayment')
    collection_status = fields.Boolean(string='Collection Status')
    collection_amount = fields.Float(string='Collection Amount')
    collection_date = fields.Date(string='Collection Date')

    @api.onchange('collection_status')
    def onchange_collection_status(self):
        for rec in self:
            if rec.collection_status:
                rec.collection_date = datetime.now()
                rec.collection_amount = rec.capital_repayment