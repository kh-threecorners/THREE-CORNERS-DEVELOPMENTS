from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    installment_down_payment_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.installment_down_payment_account_id',
        string="Down Payment Account",
        check_company=True,
        readonly=False,
    )
    installment_periodic_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.installment_periodic_account_id',
        string="Periodic Installment Account",
        check_company=True,
        readonly=False,
    )
    installment_annual_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.installment_annual_account_id',
        string="Annual Installment Account",
        check_company=True,
        readonly=False,
    )
    installment_maintenance_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.installment_maintenance_account_id',
        string="Maintenance Account",
        check_company=True,
        readonly=False,
    )
