"""Move unit types from the fixed selection to the configurable property.unit.type.

Only fills what is still empty, so the script is safe to re-run. The old
property_type / req_property_type columns are left in place as a record of the
original values.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

TYPE_XMLIDS = {
    'land': 'px_custom_real_estate_management.unit_type_admin',
    'residential': 'px_custom_real_estate_management.unit_type_residential',
    'commercial': 'px_custom_real_estate_management.unit_type_commercial',
    'industry': 'px_custom_real_estate_management.unit_type_medical',
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for key, xmlid in TYPE_XMLIDS.items():
        unit_type = env.ref(xmlid)
        cr.execute(
            "UPDATE property_property SET unit_type_id = %s "
            "WHERE property_type = %s AND unit_type_id IS NULL",
            (unit_type.id, key),
        )
        properties = cr.rowcount
        cr.execute(
            "UPDATE crm_lead SET req_unit_type_id = %s "
            "WHERE req_property_type = %s AND req_unit_type_id IS NULL",
            (unit_type.id, key),
        )
        _logger.info("Unit type %s: %s properties, %s leads", key, properties, cr.rowcount)
