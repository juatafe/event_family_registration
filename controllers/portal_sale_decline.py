# controllers/portal_sale_decline.py
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo import http
from odoo.http import request
from werkzeug.utils import redirect
import logging
_logger = logging.getLogger(__name__)

class PortalSaleDeclineSafe(CustomerPortal):

    @http.route(['/my/orders/<int:order_id>/decline'], type='http', auth='public',
                methods=['POST'], website=True, csrf=False)
    def portal_decline_order(self, order_id, access_token=None, **kw):
        """Declina de forma segura: mai propaga excepcions → mai 500."""
        try:
            # Accés al document (amb token) igual que fa el portal
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token
            )
        except Exception:
            _logger.exception("Accés denegat o token invàlid en decline")
            return redirect('/my/orders')

        try:
            ok = order_sudo.sudo().action_reject_quotation()
            if ok:
                # ja està cancel·lat + arxivat en el teu mètode
                return redirect(f'/my/orders/{order_id}?msg=declined')
            else:
                return redirect(f'/my/orders/{order_id}?msg=cannot_decline')
        except Exception:
            _logger.exception("Error inesperat en decline")
            return redirect(f'/my/orders/{order_id}?msg=error')
