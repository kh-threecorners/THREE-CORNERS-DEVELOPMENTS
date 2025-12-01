{
    'name': "Booking Report",
    'version': '19.0.1.0',
    'sequence': 1,
    'summary': """
booking report   """,

    'description': """
        Real Estate Management System
    """,
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'sale_management', 'website',
                'base_geolocalize', 'web', 'sale', 'board', 'px_custom_contact', 'real_estate_management'],
    'data': [
        'security/ir.model.access.csv',
        'reports/report_paperformat.xml',
        'reports/action_view.xml',
        'reports/report_property_booking.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': True
}
# -*- coding: utf-8 -*-
################################################################################
#
#    Kolpolok Ltd. (https://www.kolpolok.com)
#    Author: Kaushik Ahmed Apu, Aqil Mahmud, Zarin Tasnim(<https://www.kolpolok.com>)
#
################################################################################
