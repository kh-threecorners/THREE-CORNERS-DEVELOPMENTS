# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2023.
#    Author: Eng.Mohamed Reda Mahfouz (<mohamed.reda741@gmail.com>)
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
##############################################################################

{
    'name': "px_crm_updates",

    'summary': """
            This module is for customization purpose developed By Mohamed Reda Mahfouz To modify the standard apps of ...

        """,

    'description': """
        This module is for customization purpose developed By Mohamed Reda Mahfouz
    """,

    'author': "Mohamed Reda Mahfouz",
    'contributors': "Mohamed Reda Mahfouz <mohamed.reda741@gmail.com>",

    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'crm', 'real_estate_management', 'mail','stock', 'account','stock_account'],

    'data': [
        'views/crm_lead_views.xml',
        'views/crm_stage_views.xml',
    ],
    'demo': [
    ],
    'license': 'OEEL-1',

}
