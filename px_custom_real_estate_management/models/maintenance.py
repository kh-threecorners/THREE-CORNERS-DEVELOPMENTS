from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MaintenanceMaintenance(models.Model):
    _name = "maintenance.maintenance"

    name = fields.Char(string="name")
    property_id = fields.Many2one('property.property', string="Property", ondelete="cascade")