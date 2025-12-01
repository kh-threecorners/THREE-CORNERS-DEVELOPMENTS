# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2023.
#    Author: Eng.Mohamed Reda Mahfouz (<mohamed.reda741@gmail.com>)
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
##################################################################################


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.stage'

    color_hex = fields.Char(string='Color Hex', default='#0000FF')
    # color = fields.Char(string='Color Index', default='#0000FF')
    opportunity_count = fields.Integer(string='Opportunity Count', compute='_compute_opportunity_count', )

    def _compute_opportunity_count(self):
        for stage in self:
            stage.opportunity_count = self.env['crm.lead'].search_count([('stage_id', '=', stage.id)])


class ProductCategory(models.Model):
    _inherit = 'product.category'

    account_stock_variation_id = fields.Many2one('account.account', string='Stock Variation Account')
