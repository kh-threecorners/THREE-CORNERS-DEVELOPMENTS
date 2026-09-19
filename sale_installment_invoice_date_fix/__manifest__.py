# -*- coding: utf-8 -*-
{
    'name': 'Sale Installment Invoice Date Fix',
    'version': '19.0.1.0.0',
    'category': 'Sales/Real Estate',
    'summary': 'Installment invoices use the Sale Order date as Invoice Date '
               'and the installment collection date as Due Date',
    'description': """
Sale Installment Invoice Date Fix
=================================

When installment invoices are generated from a Sales Order (the
"Create Installment Invoices" button of px_custom_real_estate_management),
this module forces every generated customer invoice to have:

* Invoice Date  (invoice_date)      = the Sales Order's Order Date (date_order)
* Due Date      (invoice_date_due)  = the installment line's Collection Date

So all installments are *dated* on the day the contract/SO was made, while each
one keeps its own future maturity (collection) date.

Implementation
--------------
* account.move.create() sets the dates at creation time (before posting),
  keyed on the invoice's ``sale_order_installment_id`` link.
* sale.order button overrides re-sync any invoice left in draft as a safety net.
* An extra server-callable helper fixes existing draft installment invoices.
    """,
    'author': 'Three Corners Developments',
    'depends': [
        'px_custom_real_estate_management',
    ],
    'data': [
        'data/fix_dates_action.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
