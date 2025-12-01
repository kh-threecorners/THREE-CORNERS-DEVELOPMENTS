# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2023.
#    Author: Eng.Mohamed Reda Mahfouz (<mohamed.reda741@gmail.com>)
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
##################################################################################


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

SALE_ORDER_STATE = [
    ('draft', "Quotation"),
    ('sent', "Quotation Sent"),
    ('sales_manager_approve', "Sales Manager Approval"),
    ('general_manger_approve', "General Manager Approval"),
    ('sale', "Sales Order"),
    ('cancel', "Cancelled"),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    state = fields.Selection(
        selection=SALE_ORDER_STATE,
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')

    def action_confirm(self):
        for rec in self:
            # Check for very low margin (< 7%)
            if rec.margin_percent < 0.07:
                if self.env.user.has_group('px_sales_updates.general_manger_sale_manager'):
                    super(SaleOrder, rec).action_confirm()
                else:
                    rec.write({'state': 'general_manger_approve'})
                    # Get all users who have general manager group
                    general_managers = self.env.ref('px_sales_updates.general_manger_sale_manager').users
                    # Create activity for each general manager
                    for manager in general_managers:
                        rec.activity_schedule(
                            'mail.mail_activity_data_todo',
                            note=_(
                                'Quotation %(name)s with very low margin (< 7%%) requires your approval. Total amount: %(amount)s',
                                name=rec.name,
                                amount=rec.amount_total),
                            user_id=manager.id
                        )
                    return {
                        'warning': {
                            'title': _('General Manager Approval Required'),
                            'message': _(
                                'This Sale Order contains very low margin lines (< 7%). Waiting for General Manager approval.')
                        }
                    }
            # Check for low margin (< 10%)
            elif rec.margin_percent < 0.10:
                if self.env.user.has_group('sales_team.group_sale_manager'):
                    super(SaleOrder, rec).action_confirm()
                else:
                    rec.write({'state': 'sales_manager_approve'})
                    # Get all users who have sales manager group
                    sales_managers = self.env.ref('sales_team.group_sale_manager').users
                    # Create activity for each sales manager
                    for manager in sales_managers:
                        rec.activity_schedule(
                            'mail.mail_activity_data_todo',
                            note=_(
                                'Quotation %(name)s with low margin (< 10%%) requires your approval. Total amount: %(amount)s',
                                name=rec.name,
                                amount=rec.amount_total),
                            user_id=manager.id
                        )
                    return {
                        'warning': {
                            'title': _('Sales Manager Approval Required'),
                            'message': _(
                                'This Sale Order contains low margin lines (< 10%). Waiting for Sales Manager approval.')
                        }
                    }
            else:
                super(SaleOrder, rec).action_confirm()

    def action_sales_manager_approve(self):
        if self.env.user.has_group('sales_team.group_sale_manager'):
            result = super(SaleOrder, self).action_confirm()
            # Notify the salesperson that order is confirmed
            self.activity_schedule(
                'mail.mail_activity_data_warning',
                note=_('Quotation %(name)s has been confirmed by Sales Manager.',
                       name=self.name),
                user_id=self.user_id.id
            )
            return result
        else:
            # Get all users who have sales manager group
            sales_managers = self.env.ref('sales_team.group_sale_manager').users
            # Create activity for each sales manager
            for manager in sales_managers:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_(
                        'Quotation %(name)s with low margin (< 10%%) requires your approval. Total amount: %(amount)s',
                        name=self.name,
                        amount=self.amount_total),
                    user_id=manager.id
                )
            raise ValidationError(_('Only Sales Managers can approve this order.'))

    def action_general_manager_approve(self):
        if self.env.user.has_group('px_sales_updates.general_manger_sale_manager'):
            result = super(SaleOrder, self).action_confirm()
            # Notify the salesperson that order is confirmed
            self.activity_schedule(
                'mail.mail_activity_data_warning',
                note=_('Quotation %(name)s has been confirmed by General Manager.',
                       name=self.name),
                user_id=self.user_id.id
            )
            return result
        else:
            # Get all users who have general manager group
            general_managers = self.env.ref('px_sales_updates.general_manger_sale_manager').users
            # Create activity for each general manager
            for manager in general_managers:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_(
                        'Quotation %(name)s with very low margin (< 7%%) requires your approval. Total amount: %(amount)s',
                        name=self.name,
                        amount=self.amount_total),
                    user_id=manager.id
                )
            raise ValidationError(_('Only General Managers can approve this order.'))

    def _confirmation_error_message(self):
        """ Return whether order can be confirmed or not if not then returm error message. """
        self.ensure_one()
        if self.state not in {'draft', 'sent', 'general_manger_approve', 'sales_manager_approve'}:  # added new states
            return _("Some orders are not in a state requiring confirmation.")
        if any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in self.order_line
        ):
            return _("A line on these orders missing a product, you cannot confirm it.")

        return False

    def create(self, vals):
        if isinstance(vals, list):
            results = super(SaleOrder, self).create(vals)
            for result, val in zip(results, vals):
                if val.get('website_id'):
                    sales_managers = self.env.ref('sales_team.group_sale_manager').users
                    for manager in sales_managers:
                        result.activity_schedule(
                            'mail.mail_activity_data_todo',
                            note=_(
                                'New Quotation %(name)s has been created and waiting for your approval.',
                                name=result.name),
                            user_id=manager.id
                        )
            return results
        else:
            result = super(SaleOrder, self).create(vals)
            if vals.get('website_id'):
                sales_managers = self.env.ref('sales_team.group_sale_manager').users
                for manager in sales_managers:
                    result.activity_schedule(
                        'mail.mail_activity_data_todo',
                        note=_(
                            'New Quotation %(name)s has been created and waiting for your approval.',
                            name=result.name),
                        user_id=manager.id
                    )
            return result