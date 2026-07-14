from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    property_product_id = fields.Many2one('property.property', string="Property")
    property_maintenance_value = fields.Float(
        string="Property Maintenance Value",
        related="property_product_id.maintenance_value",
    )
    property_project_id = fields.Many2one(
        'property.project',
        string="Project",
        related='property_product_id.property_project_id',
        store=True,
        index=True,
        readonly=True,
    )

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


class ProductProduct(models.Model):
    _inherit = 'product.product'

    property_product_id = fields.Many2one('property.property', string="Property")
    property_maintenance_value = fields.Float(
        string="Property Maintenance Value",
        related="property_product_id.maintenance_value",
    )
    property_project_id = fields.Many2one(
        'property.project',
        string="Project",
        related='property_product_id.property_project_id',
        store=True,
        index=True,
        readonly=True,
    )

    property_count = fields.Integer(
        string="Properties",
        compute="_compute_property_count"
    )

    def _compute_property_count(self):
        for product in self:
            product.property_count = self.env['property.property'].search_count([
                ('product_id', '=', product.id)
            ])

    def action_view_properties(self):
        self.ensure_one()
        return {
            'name': _('Properties'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.property',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def action_view_property(self):
        """زر سابق لفتح أول عقار مرتبط"""
        self.ensure_one()
        prop = self.env['property.property'].search([('product_id', '=', self.id)], limit=1)
        if not prop:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _('Property'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.property',
            'view_mode': 'form',
            'res_id': prop.id,
            'target': 'current',
        }

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
