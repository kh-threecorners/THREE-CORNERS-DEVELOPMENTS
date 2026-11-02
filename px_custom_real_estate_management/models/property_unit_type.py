from odoo import fields, models


class PropertyUnitType(models.Model):
    _name = "property.unit.type"
    _description = "Property Unit Type"
    _order = "sequence, id"

    name = fields.Char(string="Type", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
