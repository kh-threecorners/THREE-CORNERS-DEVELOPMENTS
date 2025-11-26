# -*- coding: utf-8 -*-
from odoo import fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    project_id = fields.Many2one('property.project', string='Project', readonly=True)