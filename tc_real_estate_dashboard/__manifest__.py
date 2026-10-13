# -*- coding: utf-8 -*-
{
    'name': 'TC Real Estate Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Live backend dashboard (OWL) for the real-estate module — '
               'properties, bookings, installments and collections',
    'description': """
Three Corners — Real Estate Dashboard
=====================================
A native Odoo (OWL) client-action dashboard that reads live data straight from
the ORM every time it is opened:

* KPI cards: total / available / sold units, bookings, contract value, collected.
* Sales-growth chart: booking value by month (last 12 months).
* Units by project and bookings by status.
* Collections by project (paid vs remaining) and a paid/remaining ring.
* Recent bookings, top available units, and upcoming installments.

Reads from: property.property, property.sale, property.sale.line, property.project.
No data is stored by this module; every figure is queried live.
    """,
    'author': 'Three Corners Developments',
    'depends': [
        'px_custom_real_estate_management',
        'web',
    ],
    'data': [
        'views/dashboard_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tc_real_estate_dashboard/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
