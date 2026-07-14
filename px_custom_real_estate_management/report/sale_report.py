from odoo import fields, models


class SaleReport(models.Model):
    """Add the real-estate dimensions to Sales > Reporting > Sales, so orders can be
    sliced by Project or Unit.

    The fields are named `property_*` on purpose: Odoo's own `sale_project` module
    defines `sale.report.project_id` as a `project.project`, and auto-installs with the
    Project app. Reusing that name for a `property.project` would silently corrupt the
    report.
    """

    _inherit = 'sale.report'

    property_project_id = fields.Many2one('property.project', string="Project", readonly=True)
    property_id = fields.Many2one('property.property', string="Unit", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        # sale.order still names its property.project column `project_id`.
        res['property_project_id'] = 's.project_id'
        res['property_id'] = 's.property_id'
        return res

    def _group_by_sale(self):
        return super()._group_by_sale() + """,
            s.project_id,
            s.property_id"""
