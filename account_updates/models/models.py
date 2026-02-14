# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2023.
#    Author: Eng.Mohamed Reda Mahfouz (<mohamed.reda741@gmail.com>)
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
##################################################################################


from odoo import models, fields, api,_
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[]",
        check_company=True)





