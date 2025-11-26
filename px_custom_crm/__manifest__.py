{
    'name': 'Unique CRM',
    'version': '1.0',
    'summary': 'Making The CRM Unique',
    'description': 'Making The CRM Unique.',
    'author': 'Mohamed Hamed',
    'depends': ['base', 'crm','contacts','real_estate_management'],
    'data': [
        "data/cron.xml",
        'views/views.xml',
        'security/record_rule.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}