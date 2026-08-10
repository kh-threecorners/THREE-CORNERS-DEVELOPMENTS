from odoo import api, fields, models
from odoo.tools import SQL

from ..models.account_move import INSTALLMENT_TYPE_SELECTION


class AccountInvoiceReport(models.Model):
    """Add the real-estate dimensions to Accounting > Reporting > Invoice Analysis,
    so invoices can be sliced by Sale Order, Project, Unit or installment type."""

    _inherit = 'account.invoice.report'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", readonly=True)
    property_project_id = fields.Many2one('property.project', string="Project", readonly=True)
    property_id = fields.Many2one('property.property', string="Unit", readonly=True)
    installment_type = fields.Selection(
        INSTALLMENT_TYPE_SELECTION, string="Installment Type", readonly=True,
    )

    # Makes the ORM flush these columns before the report's inline query runs.
    _depends = {
        'account.move': ['sale_order_id', 'property_project_id', 'property_id'],
        'account.move.line': ['installment_type'],
    }

    @api.model
    def _select(self) -> SQL:
        return SQL(
            "%s, move.sale_order_id, move.property_project_id, move.property_id,"
            " line.installment_type",
            super()._select(),
        )
