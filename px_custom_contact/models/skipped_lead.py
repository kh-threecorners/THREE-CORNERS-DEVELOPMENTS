from odoo import models, fields


class SkippedLead(models.Model):
    _name = 'skipped.lead'
    _description = 'Duplicated Opportunity'

    lead_id = fields.Many2one('crm.lead', string="Duplicated Lead", required=True)
    import_date = fields.Datetime(string="Import Date", default=fields.Datetime.now)

    # Related fields to be usable in tree/kanban views
    # name = fields.Char(related='lead_id.name', store=True)
    # phone = fields.Char(related='lead_id.phone', store=True)
    # email_from = fields.Char(related='lead_id.email_from', store=True)
    # user_id = fields.Many2one('res.users', related='lead_id.user_id', store=True)
    # stage_id = fields.Many2one('crm.stage', related='lead_id.stage_id', store=True)
    # probability = fields.Float(related='lead_id.probability', store=True)
    # active = fields.Boolean(related='lead_id.active', store=True)
    # company_id = fields.Many2one('res.company', related='lead_id.company_id', store=True)
    # is_partner_visible = fields.Boolean(related='lead_id.is_partner_visible', store=True)
    # type = fields.Selection([
    #     ('lead', 'Lead'), ('opportunity', 'Opportunity')], index=True, related='lead_id.type',
    #     default='lead')
    # partner_id = fields.Many2one(related='lead_id.partner_id', store=True)
    # contact_name = fields.Char(related='lead_id.contact_name', store=True)
    # title = fields.Many2one(related='lead_id.contact_name', store=True)
    # street = fields.Char(related='lead_id.street', store=True)
    # street2 = fields.Char(related='lead_id.street2', store=True)
    # city = fields.Char(related='lead_id.city', store=True)
    # state_id = fields.Many2one(related='lead_id.state_id', store=True)
    # zip = fields.Char(related='lead_id.zip', store=True)
    # country_id = fields.Many2one(related='lead_id.country_id', store=True)
    # function = fields.Char(related='lead_id.function', store=True)
    # mobile = fields.Char(related='lead_id.mobile', store=True)
    # team_id = fields.Many2one('crm.team', related='lead_id.team_id', store=True)
    # website = fields.Char(related='lead_id.website', store=True)
    # lang_code = fields.Char(related='lead_id.lang_code', store=True)
    # partner_name = fields.Char(related='lead_id.partner_name', store=True)
    # lang_active_count = fields.Integer(related='lead_id.lang_active_count', store=True)
    # lang_id = fields.Many2one(related='lead_id.lang_id', store=True)

# ###############################################
#     from odoo import models, fields
#
#     class SkippedLead(models.Model):
#         _name = 'skipped.lead'
#         _description = 'Duplicated Opportunity'
#
#         lead_id = fields.Many2one('crm.lead', string="Duplicated Lead", required=True)
#         import_date = fields.Datetime(string="Import Date", default=fields.Datetime.now)
#
#         # Related fields to be usable in tree/kanban views
#         name = fields.Char(related='lead_id.name', store=True)
#         phone = fields.Char(related='lead_id.phone', store=True)
#         email_from = fields.Char(related='lead_id.email_from', store=True)
#         user_id = fields.Many2one('res.users', related='lead_id.user_id', store=True)
#         stage_id = fields.Many2one('crm.stage', related='lead_id.stage_id', store=True)
#         user_company_ids = fields.Many2many('res.company', related='lead_id.user_company_ids', store=True)
#         team_id = fields.Many2one('crm.team', related='lead_id.team_id', store=True)
#         company_id = fields.Many2one('res.company', related='lead_id.company_id', store=True)
#         referred = fields.Char(related='lead_id.referred', store=True)
#         description = fields.Html(related='lead_id.description', store=True)
#         active = fields.Boolean(related='lead_id.active', store=True)
#         type = fields.Selection(related='lead_id.type', store=True)
#         priority = fields.Selection(related='lead_id.priority', store=True)
#         kanban_state = fields.Selection(related='lead_id.kanban_state', store=True)
#         tag_ids = fields.Many2many(related='lead_id.tag_ids', store=True)
#         color = fields.Integer(related='lead_id.color', store=True)
#
#         day_open = fields.Float(related='lead_id.day_open', store=True)
#         day_close = fields.Float(related='lead_id.day_close', store=True)
#
#         partner_id = fields.Many2one(related='lead_id.partner_id', store=True)
#         partner_is_blacklisted = fields.Boolean(related='lead_id.partner_is_blacklisted', store=True)
#         contact_name = fields.Char(related='lead_id.contact_name', store=True)
#         partner_name = fields.Char(related='lead_id.partner_name', store=True)
#         function = fields.Char(related='lead_id.function', store=True)
#         title = fields.Many2one(related='lead_id.title', store=True)
#         email_normalized = fields.Char(related='lead_id.email_normalized', store=True)
#         email_domain_criterion = fields.Char(related='lead_id.email_domain_criterion', store=True)
#         email_state = fields.Selection(related='lead_id.email_state', store=True)
#         phone_sanitized = fields.Char(related='lead_id.phone_sanitized', store=True)
#         phone_state = fields.Selection(related='lead_id.phone_state', store=True)
#         website = fields.Char(related='lead_id.website', store=True)
#         lang_id = fields.Many2one(related='lead_id.lang_id', store=True)
#         lang_code = fields.Char(related='lead_id.lang_code', store=True)
#         lang_active_count = fields.Integer(related='lead_id.lang_active_count', store=True)
#         street = fields.Char(related='lead_id.street', store=True)
#         street2 = fields.Char(related='lead_id.street2', store=True)
#         zip = fields.Char(related='lead_id.zip', store=True)
#         city = fields.Char(related='lead_id.city', store=True)
#         state_id = fields.Many2one(related='lead_id.state_id', store=True)
#         country_id = fields.Many2one(related='lead_id.country_id', store=True)
#         probability = fields.Float(related='lead_id.probability', store=True)
#         automated_probability = fields.Float(related='lead_id.automated_probability', store=True)
#         is_automated_probability = fields.Boolean(related='lead_id.is_automated_probability', store=True)
#         lost_reason_id = fields.Many2one(related='lead_id.lost_reason_id', store=True)
#         calendar_event_ids = fields.One2many(related='lead_id.calendar_event_ids', store=True)
#         duplicate_lead_ids = fields.Many2many(related='lead_id.duplicate_lead_ids', store=True)
#         duplicate_lead_count = fields.Integer(related='lead_id.duplicate_lead_count', store=True)
#         meeting_display_label = fields.Char(related='lead_id.meeting_display_label', store=True)
#
#         is_partner_visible = fields.Boolean(related='lead_id.is_partner_visible', store=True)
#         # UTMs
#         campaign_id = fields.Many2one(related='lead_id.campaign_id', store=True)
#         medium_id = fields.Many2one(related='lead_id.medium_id', store=True)
#         source_id = fields.Many2one(related='lead_id.source_id', store=True)