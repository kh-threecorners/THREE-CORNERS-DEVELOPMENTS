# -*- coding: utf-8 -*-
################################################################################
#
#    Kolpolok Ltd. (https://www.kolpolok.com)
#    Author: Kaushik Ahmed Apu, Aqil Mahmud, Zarin Tasnim(<https://www.kolpolok.com>)
#
################################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    """A class that inherits the already existing model res partner"""
    _inherit = 'res.partner'

    blacklisted = fields.Boolean(string='Blacklisted', default=False,
                                 help='Is this contact a blacklisted contact '
                                      'or not')
    is_developer = fields.Boolean(
        string='Is Developer',
        help='Check this box if the partner is a developer',
    )
    id_number = fields.Char(
        string='ID Number',
        help='The ID number of the contact',
    )
    contact_code = fields.Char(
        string='Contact Code',
        help='The code of the contact',
    )
    nationality = fields.Char(string='Nationality')


    @api.constrains('contact_code')
    def _check_unique_contact_code(self):
        for rec in self:
            if rec.contact_code and self.search_count([
                ('contact_code', '=', rec.contact_code),
                ('id', '!=', rec.id),
                ('active', '=', True)
            ]) > 0:
                raise ValidationError(_("A  contact with the same contact code already exists: %s") % rec.contact_code)


    def action_add_blacklist(self):
        """Sets the field blacklisted to True"""
        self.blacklisted = True

    def action_remove_blacklist(self):
        """Sets the field blacklisted to False"""
        self.blacklisted = False
