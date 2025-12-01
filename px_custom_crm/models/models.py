from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo import tools


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    source_id = fields.Many2one('utm.source', string='Plate form', help='The source of the opportunity')

    import_file_name = fields.Char(string="Imported File")
    import_date = fields.Datetime(string="Import Date")
    property_id = fields.Many2one('property.property', string="Property")
    last_user_id = fields.Many2one('res.users', string="Last Salesperson", readonly=True)
    last_stage_id = fields.Many2one('crm.stage', string="Last Stage", readonly=True)
    user_change_count = fields.Integer(string="Salesperson Change Count", default=0, readonly=True)

    all_log_notes_text = fields.Text("Feedback", compute="_compute_all_log_notes_text", store=False)

    def _compute_all_log_notes_text(self):
        for lead in self:
            messages = lead.message_ids.sorted("date")
            notes = []
            for msg in messages:
                if msg.body:
                    clean_text = tools.html2plaintext(msg.body).strip()
                    notes.append(
                        f"[{msg.date.strftime('%Y-%m-%d %H:%M')}] {msg.author_id.name or 'System'}: {clean_text}")
            lead.all_log_notes_text = "\n".join(notes) if notes else ""

    def _cron_move_fresh_leads(self):
        """Move all leads in 'Fresh leads' stage to 'Not Communicated' at midnight"""
        fresh_stage = self.env['crm.stage'].search([('name', '=', 'Fresh leads')], limit=1)
        not_comm_stage = self.env['crm.stage'].search([('name', '=', 'Not Communicated')], limit=1)

        stages = self.env['crm.stage'].search([])
        print("List of CRM Stages:")
        for stage in stages:
            print(f"- ID: {stage.id}, Name: '{stage.name}'")

        if not fresh_stage or not not_comm_stage:
            print("Warning: Stages not found: 'Fresh leads' or 'Not Communicated'")
            return

        leads = self.search([('stage_id', '=', fresh_stage.id)])
        if leads:
            leads.write({'stage_id': not_comm_stage.id})
            print(f"Moved {len(leads)} leads from Fresh leads to Not Communicated")
        else:
            print("No leads to move at this time")

    def _cron_move_to_rotated_stage(self):
        """Move leads to 'rotated-opportunity' stage only on second or later Salesperson change"""
        rotated_stage = self.env['crm.stage'].search([('name', '=', 'rotated-opportunity')], limit=1)
        if not rotated_stage:
            print("Rotated stage not found!")
            return

        leads = self.search([])
        print(f"Checking {len(leads)} leads for salesperson changes...")

        for lead in leads:
            print(
                f"\nProcessing Lead {lead.id} ({lead.name}): current user = {lead.user_id.name if lead.user_id else 'None'}, last_user_id = {lead.last_user_id.name if lead.last_user_id else 'None'}, change_count = {lead.user_change_count}")

            if not lead.last_user_id and lead.user_id:
                lead.last_user_id = lead.user_id.id
                lead.user_change_count = 0
                print(f"  -> Initial assignment: last_user_id set to {lead.user_id.name}, stage not changed")
                continue

            if lead.user_id != lead.last_user_id:
                lead.user_change_count += 1
                print(
                    f"  -> User changed: last_user_id = {lead.last_user_id.name if lead.last_user_id else 'None'} -> new user = {lead.user_id.name if lead.user_id else 'None'}, change_count = {lead.user_change_count}")

                if lead.user_change_count >= 2:
                    lead.last_stage_id = lead.stage_id.id
                    lead.stage_id = rotated_stage.id
                    print(
                        f"  -> Stage changed from {lead.last_stage_id.name if lead.last_stage_id else 'N/A'} to {rotated_stage.name}")

                lead.last_user_id = lead.user_id.id if lead.user_id else False
            else:
                print(f"  -> No change in Salesperson, stage remains {lead.stage_id.name if lead.stage_id else 'N/A'}")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("phone"):
                vals["phone"] = self.normalize_phone_number(vals["phone"])
            if vals.get("mobile"):
                vals["mobile"] = self.normalize_phone_number(vals["mobile"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("phone"):
            vals["phone"] = self.normalize_phone_number(vals["phone"])
        if vals.get("mobile"):
            vals["mobile"] = self.normalize_phone_number(vals["mobile"])
        return super().write(vals)

    def normalize_phone_number(self, phone):
        return self.env['res.partner'].normalize_phone_number(phone)

    @api.constrains('phone', 'mobile')
    def _check_unique_phone_mobile(self):
        if self.env.is_superuser() or self.env.context.get('skip_duplication_check'):
            return

        for lead in self:
            if lead.phone:

                phone_without_zero = lead.phone.lstrip('0')

                phone_with_zero = '0' + phone_without_zero if len(
                    phone_without_zero) == 10 and not lead.phone.startswith('0') else lead.phone

                search_list = list(set([phone_with_zero, phone_without_zero]))
                domain = [
                    ('id', '!=', lead.id),
                    '|',
                    ('phone', 'in', search_list),
                    ('mobile', 'in', search_list)
                ]

                if self.search_count(domain) > 0:
                    raise ValidationError(
                        _('The phone number "%s" (or a variation of it) already exists for another record.') % lead.phone)

            if lead.mobile and lead.mobile != lead.phone:
                mobile_without_zero = lead.mobile.lstrip('0')
                mobile_with_zero = '0' + mobile_without_zero if len(
                    mobile_without_zero) == 10 and not lead.mobile.startswith('0') else lead.mobile

                search_list = list(set([mobile_with_zero, mobile_without_zero]))

                domain = [
                    ('id', '!=', lead.id),
                    '|',
                    ('phone', 'in', search_list),
                    ('mobile', 'in', search_list)
                ]

                if self.search_count(domain) > 0:
                    raise ValidationError(
                        _('The mobile number "%s" (or a variation of it) already exists for another record.') % lead.mobile)
