from odoo import api, fields, models, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

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
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def action_view_property(self):
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
