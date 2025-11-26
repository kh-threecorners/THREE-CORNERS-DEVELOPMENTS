from dataclasses import fields

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # @api.constrains('name', 'mobile')
    # def _check_unique_name_mobile(self):
    #     for rec in self:
    #         # Check for duplicate name
    #         print(rec.name)
    #         partner=self.search([
    #             ('name', '=', rec.name),
    #             ('id', '!=', rec.id),
    #             ('active', '=', True)
    #         ])
    #         print(partner)
    #         if rec.name and  len(partner) >0:
    #
    #             raise ValidationError(_("A 1 contact with the same name already exists: %s") % rec.name)
    #
    #         # Check for duplicate mobile (ignore empty mobiles)
    #         if rec.mobile and self.search_count([
    #             ('mobile', '=', rec.mobile),
    #             ('id', '!=', rec.id),
    #             ('active', '=', True)
    #         ]) > 0:
    #             raise ValidationError(_("A 2 contact with the same mobile number already exists: %s") % rec.mobile)
    #
    #         # Check for duplicate phones (ignore empty phones)
    #         if rec.phone and self.search_count([
    #             ('phone', '=', rec.phone),
    #             ('id', '!=', rec.id),
    #             ('active', '=', True)
    #         ]) > 0:
    #             raise ValidationError(_("A 3 contact with the same phone number already exists: %s") % rec.phone)
    #
    # @api.constrains('name', 'mobile')
    # def _check_unique_name_mobile(self):
    #     for rec in self:
    #         # Check for duplicate name
    #         if rec.name and self.search_count([
    #             ('name', '=', rec.name),
    #             ('id', '!=', rec.id),
    #             ('active', '=', True)
    #         ]) > 0:
    #             raise ValidationError(_("A contact with the same name already exists: %s") % rec.name)
    #
    #         # Check for duplicate mobile (ignore empty mobiles)
    #         if rec.mobile and self.search_count([
    #             ('mobile', '=', rec.mobile),
    #             ('id', '!=', rec.id),
    #             ('active', '=', True)
    #         ]) > 0:
    #             raise ValidationError(
    #                 _("A contact with the same mobile number already exists: %s") % rec.mobile)
    #
    #         # Check for duplicate phones (ignore empty phones)
    #         if rec.phone and self.search_count([
    #             ('phone', '=', rec.phone),
    #             ('id', '!=', rec.id),
    #             ('active', '=', True)
    #         ]) > 0:
    #             raise ValidationError(_("A contact with the same phone number already exists: %s") % rec.phone)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    duplicate = fields.Boolean(string="Duplicate")

    # @api.constrains('phone')
    # def _check_duplicate_phone(self):
    #     for record in self:
    #         if record.phone:
    #             duplicate = self.env['crm.lead'].search([
    #                 ('phone', '=', record.phone),
    #                 ('id', '!=', record.id),
    #                 ('type', '=', 'opportunity'),
    #             ], limit=1)
    #             if duplicate:
    #                 raise ValidationError(
    #                     " A d  lead with the same phone number already exists: %s" % duplicate.name)

    # @api.constrains('name')
    # def _check_duplicate_name(self):
    #     for record in self:
    #         if record.name:
    #             duplicate = self.env['crm.lead'].search([
    #                 ('name', '=', record.name),
    #                 ('id', '!=', record.id),
    #                 ('type', '=', 'opportunity'),
    #             ], limit=1)
    #             if duplicate:
    #                 raise ValidationError(" A lead with the same name already exists: %s" % duplicate.name)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     leads = super().create(vals_list)
    #     for lead in leads:
    #         if lead.type == 'opportunity' and not lead.partner_id:
    #             partner = self.env['res.partner'].create({
    #                 'name': lead.name,
    #                 'phone': lead.phone,
    #                 'email': lead.email_from,
    #                 'mobile': lead.mobile,
    #             })
    #             lead.partner_id = partner.id
    #     return leads
