# -*- coding: utf-8 -*-
{
    'name': "Custom Real Estate | Property Management System",
    'version': '19.0.1.0',
    'sequence': 1,
    'summary': """
        Real estate system manages viewing, brochures, auctions, mapping, commissions, reporting, invoicing, payments, blacklist.
    """,

    'description': """
        Real Estate Management System
    """,
    'depends': ['base', 'mail', 'sale_management', 'website',
                'base_geolocalize', 'web', 'sale', 'board', 'px_custom_contact' , 'real_estate_management', 'px_custom_contact'],
    'data': [
        'data/cron.xml',
        'security/ir.model.access.csv',
        'reports/paperformat.xml',
        'reports/report_action.xml',
        'views/h_payment_plane.xml',
        'views/property_property_view.xml',
        'views/property_sale_view.xml',
        'views/crm_inherit.xml',
        'views/sale_view.xml',
        'views/property_project_view.xml',
        'views/property_rental_view.xml',
        'views/res_partner.xml',
        'views/installments.xml',
        # 'views/maintenance.xml',
        'reports/property_rental_report.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [

    ],
}
