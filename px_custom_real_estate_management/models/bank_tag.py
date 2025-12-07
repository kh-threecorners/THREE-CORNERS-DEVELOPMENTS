from odoo import models, api, _, fields


class BankTag(models.Model):
    _name = "bank.tag"

    name = fields.Char(string="Bank Name ")