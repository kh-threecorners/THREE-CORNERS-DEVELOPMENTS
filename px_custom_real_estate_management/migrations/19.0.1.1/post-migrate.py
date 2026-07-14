"""Backfill the Project / Unit / Sale Order links on records that predate them.

Written through the ORM on purpose: raw SQL would bypass dependency tracking and leave
the stored fields that hang off these links (e.g. product.property_project_id) stale.

Everything here only fills fields that are still empty, so the script is safe to re-run.
Name-based matching is used only as a last resort, and only when the name resolves to
exactly one property — an ambiguous name is logged and skipped rather than guessed, since
a wrong link would silently poison the new reports.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _backfill_sale_orders(env):
    """Sale orders created before `property_id` was written (the unit's 'Create Sale
    Order' button and the CRM quotation path only set `origin`)."""
    orders = env['sale.order'].search([('property_id', '=', False)])
    linked = 0

    for order in orders:
        # The reliable route: the order line already points at the unit's own product.
        unit = order.order_line.product_id.property_product_id[:1]

        # Fallback for orders whose product was found by the old name-search: match the
        # origin against the property name, but only when it is unambiguous.
        if not unit and order.origin:
            candidates = env['property.property'].search([('name', '=', order.origin)])
            if len(candidates) > 1:
                _logger.warning(
                    "Sale order %s: origin %r matches %s properties, skipping.",
                    order.name, order.origin, len(candidates),
                )
                continue
            unit = candidates

        if not unit:
            continue

        vals = {'property_id': unit.id}
        if not order.project_id and unit.property_project_id:
            vals['project_id'] = unit.property_project_id.id
        order.write(vals)
        linked += 1

    _logger.info("Backfill: linked %s/%s sale orders to their unit.", linked, len(orders))


def _backfill_invoices(env):
    """Invoices need `sale_order_id` first (some only carry the installment line), then
    the unit/project stamped from that order."""
    AccountMove = env['account.move']

    orphans = AccountMove.search([
        ('sale_order_id', '=', False),
        ('sale_order_installment_id', '!=', False),
    ])
    for move in orphans:
        move.sale_order_id = move.sale_order_installment_id.sale_order_id
    _logger.info("Backfill: recovered the sale order on %s invoices.", len(orphans))

    unstamped = AccountMove.search([
        ('sale_order_id', '!=', False),
        '|', ('property_id', '=', False), ('property_project_id', '=', False),
    ])
    stamped = 0
    for move in unstamped:
        order = move.sale_order_id
        vals = {}
        if not move.property_id and order.property_id:
            vals['property_id'] = order.property_id.id
        if not move.property_project_id and order.project_id:
            vals['property_project_id'] = order.project_id.id
        if vals:
            move.write(vals)
            stamped += 1

    _logger.info("Backfill: stamped unit/project on %s invoices.", stamped)

    # Rental invoices have no sale order; their unit comes from the rental itself.
    rentals = AccountMove.search([
        ('property_rental_id', '!=', False),
        ('property_id', '=', False),
    ])
    for move in rentals:
        unit = move.property_rental_id.property_id
        if not unit:
            continue
        move.write({
            'property_id': unit.id,
            'property_project_id': unit.property_project_id.id,
        })

    _logger.info("Backfill: stamped unit/project on %s rental invoices.", len(rentals))


def _backfill_products(env):
    """Service products created by the old name-search paths, never linked to their unit.

    `product.property_project_id` is a stored related on the unit, so it fills itself once
    `property_product_id` is set.
    """
    products = env['product.product'].search([
        ('property_product_id', '=', False),
        ('type', '=', 'service'),
    ])
    linked = 0

    for product in products:
        candidates = env['property.property'].search([('name', '=', product.name)])
        if not candidates:
            continue
        if len(candidates) > 1:
            _logger.warning(
                "Product %r matches %s properties by name, skipping.",
                product.name, len(candidates),
            )
            continue

        product.property_product_id = candidates.id
        product.product_tmpl_id.property_product_id = candidates.id
        if not candidates.product_id:
            candidates.product_id = product.id
        linked += 1

    _logger.info("Backfill: linked %s products to their unit.", linked)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    _backfill_sale_orders(env)
    _backfill_invoices(env)
    _backfill_products(env)
