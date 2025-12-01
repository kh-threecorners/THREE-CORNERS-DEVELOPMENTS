# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2023.
#    Author: Eng.Mohamed Reda Mahfouz (<mohamed.reda741@gmail.com>)
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
##################################################################################


from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError
from lxml import etree


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    property_project_id = fields.Many2one('property.project', string='Property Project',
                                          help='The project of the property')
    property_id = fields.Many2one('property.property', string='Property',
                                  help='The property of the project', domain=[('state', '!=', 'sold')])
    property_price = fields.Monetary(string='Property Price', related='property_id.unit_price', store=True,
                                     help='The price of the property')
    currency_id = fields.Many2one(
        "res.currency", string="Currency", related="company_id.currency_id")
    call_counter = fields.Integer(string="Call Count", default=0)
    message_counter = fields.Integer(string="Message Count", default=0)
    whatsapp_counter = fields.Integer(string="WhatsApp Count", default=0)

    req_property_type = fields.Selection(
        [
            ("land", "Land"),
            ("residential", "Residential"),
            ("commercial", "Commercial"),
            ("industry", "Industry"),
        ],
        string="Required Type",
        help="The Required type of the property",
    )
    req_property_size = fields.Float(
        string='Required Property Size',
        help='The Required size of the property'
    )
    req_property_bedrooms = fields.Integer(
        string='Required Bedrooms',
        help='The Required number of bedrooms in the property'
    )
    req_property_bathrooms = fields.Integer(
        string='Required  Bathrooms',
        help='The Required number of bathrooms in the property'
    )
    req_floor = fields.Integer(
        string='Required Floors',
        help='The Required floor of the property'
    )
    req_price = fields.Monetary(
        string='Required Price',
        help='The Required price of the property'
    )

    booking_ids = fields.One2many('property.sale', 'lead_id', string='Bookings')
    booking_count = fields.Integer(string='Booking Count', compute='_compute_booking_count')

    # use get_view to make phone and mobile readonly in case of the user is not in sales_team.group_sale_salesman_all_leads or sales_team.group_sale_manager
    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super(CrmLead, self).get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            user = self.env.user
            if not user.has_group('sales_team.group_sale_salesman_all_leads') and not user.has_group(
                    'sales_team.group_sale_manager'):
                for node in doc.xpath("//field[@name='phone']"):
                    node.set('readonly', '1')
                for node in doc.xpath("//field[@name='mobile']"):
                    node.set('readonly', '1')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def _compute_booking_count(self):
        """Calculates the number of bookings associated with this lead."""
        for lead in self:
            lead.booking_count = len(lead.booking_ids)

    def action_view_bookings(self):
        self.ensure_one()
        return {
            'name': _('Bookings'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.sale',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.booking_ids.ids)],
            'context': {'default_lead_id': self.id}
        }

    def action_create_property_booking(self):
        """
        Creates a new property booking (property.sale) from the lead.
        """
        self.ensure_one()

        if not self.partner_id:
            raise ValidationError(_("Please select or create a customer for this lead before creating a booking."))
        if not self.property_id:
            raise ValidationError(_("Please select a property unit to book."))

        booking_context = {
            'default_partner_id': self.partner_id.id,
            'default_project_id': self.property_project_id.id,
            'default_property_id': self.property_id.id,
            'default_sale_price': self.property_price,
            'default_note': self.description,
            'default_lead_id': self.id,

        }

        return {
            'name': _('Create Property Booking'),
            'view_mode': 'form',
            'res_model': 'property.sale',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': booking_context,
        }
