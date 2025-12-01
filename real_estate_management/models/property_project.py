# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2023.
#    Author: Eng.Mohamed Reda Mahfouz (<mohamed.reda741@gmail.com>)
#
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
##################################################################################

from odoo import api, fields, models

class PropertyProject(models.Model):
    _name = 'property.project'
    _description = 'Property Project'
    _rec_name = 'name'

    name = fields.Char(string='Project Name', required=True,
                       help='The name of the project')
    image = fields.Binary(string='Image',
                          help='The Project image')
    description = fields.Text(string='Description',
                              help='The description of the project')
    developer_id = fields.Many2one('res.partner', string='Developer',
                                   help='The developer of the project')
    property_ids = fields.One2many('property.property', 'property_project_id', string='Properties',
                                   help='The properties associated with the project')

    # todo add file pdf attachment , tag for project
