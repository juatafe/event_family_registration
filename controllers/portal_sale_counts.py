# controllers/portal_sale_counts.py
from odoo.addons.sale.controllers.portal import CustomerPortal as SalePortal
from odoo.http import request

class CustomerPortal(SalePortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id.commercial_partner_id
        SaleOrder = request.env['sale.order'].sudo()

        # Recalcula el comptador de QUOTES excloent cancel·lades
        if 'quotation_count' in counters:
            q_domain = self._prepare_my_quotations_domain(partner) + [('state', '!=', 'cancel')]
            values['quotation_count'] = SaleOrder.search_count(q_domain)

        # (Opcional) si vols ser coherent també amb “Comandes”:
        # if 'order_count' in counters:
        #     o_domain = self._prepare_my_orders_domain(partner)
        #     values['order_count'] = SaleOrder.search_count(o_domain)

        return values
