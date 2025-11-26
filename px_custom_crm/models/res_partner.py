from odoo import models, api
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"

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
        if not phone:
            return False
        import re
        arabic_digits = '٠١٢٣٤٥٦٧٨٩'
        western_digits = '0123456789'
        trans_table = str.maketrans(arabic_digits, western_digits)
        phone = phone.translate(trans_table)
        phone = re.sub(r'[^\d+]', '', phone)
        if phone.lower().startswith('p:'):
            phone = phone[2:]
        if phone.startswith('+20'):
            phone = phone[3:]
        elif phone.startswith('20') and len(phone) > 10:
            phone = phone[2:]
        if not phone.startswith('0'):
            phone = '0' + phone
        return phone

    def write(self, vals):
        if self.env.user.has_group('base.group_system'):
            return super().write(vals)

        allowed_fields = ['name']
        if any(f not in allowed_fields for f in vals):
            raise UserError("You can only modify the Name!")

        return super().write(vals)
