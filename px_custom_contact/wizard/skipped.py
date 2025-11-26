from odoo import models, fields

class SkippedLeadsWizard(models.TransientModel):
    _name = 'skipped.leads.wizard'
    _description = 'Skipped Leads Wizard'

    skipped_ids = fields.One2many('skipped.leads.line', 'wizard_id', string="Duplicated Opportunities")


class SkippedLeadsLine(models.TransientModel):
    _name = 'skipped.leads.line'
    _description = 'Skipped Lead Line'

    wizard_id = fields.Many2one('skipped.leads.wizard', string="Wizard")
    name = fields.Char(string="Opportunity Name")
    phone = fields.Char(string="Phone")
    user_id = fields.Char(string="Salesperson")
    stage_id = fields.Char(string="Stage")