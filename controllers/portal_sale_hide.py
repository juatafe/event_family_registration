# controllers/portal_sale_hide.py
from odoo.addons.sale.controllers.portal import CustomerPortal as SalePortal
from odoo.http import request

class CustomerPortal(SalePortal):

    def _partner_root(self):
        # comercial per a incloure subpartners
        return request.env.user.partner_id.commercial_partner_id

    # Llistat de ORDERS (comandes confirmades)
    def _prepare_my_orders_domain(self, partner):
        partner = partner or self._partner_root()
        return [
            ('partner_id', 'child_of', [partner.id]),
            ('state', 'in', ['sale', 'done']),
            ('hide_on_portal', '=', False),
        ]

    # Llistat de QUOTATIONS (pressupostos / "Reserves")
    def _prepare_my_quotations_domain(self, partner):
        partner = partner or self._partner_root()
        return [
            ('partner_id', 'child_of', [partner.id]),
            ('state', 'in', ['draft', 'sent']),
            ('hide_on_portal', '=', False),
        ]
