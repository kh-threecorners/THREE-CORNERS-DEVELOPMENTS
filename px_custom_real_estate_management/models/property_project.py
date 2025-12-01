from odoo import models, fields


class PropertyProjectInherit(models.Model):
    _inherit = 'property.project'

    file_attachment = fields.Binary(
        string="Project File",
        attachment=True,
        help="Upload PDF or any related file for the project"
    )
    file_name = fields.Char(
        string="File Name",
        help="The name of the uploaded file"
    )
