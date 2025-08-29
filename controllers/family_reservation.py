from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class FamilyReservationController(http.Controller):

    @http.route(['/my/event/check_reservation'], type='json', auth="user")
    def check_reservation(self, event_id):
        """Comprova si hi ha un pressupost familiar obert per a aquest event"""
        partner = request.env.user.partner_id
        miembro = request.env['familia.miembro'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )
        if not miembro:
            return {'has_reservation': False}

        familia = miembro.familia_id
        SaleOrder = request.env['sale.order'].sudo()

        existing = SaleOrder.search([
            ('partner_id', 'in', familia.miembros_ids.mapped('partner_id').ids),
            ('event_id', '=', int(event_id)),
            ('state', 'in', ['draft', 'sent']),
        ], limit=1)

        if not existing:
            return {'has_reservation': False}

        order = existing[0]
        tickets_info = [
            {
                'product': l.product_id.display_name,
                'ticket_id': l.product_id.id,   # 🔑 per poder reomplir inputs JS
                'qty': l.product_uom_qty
            }
            for l in order.order_line
        ]

        return {
            'has_reservation': True,
            'partner': order.partner_id.name,
            'tickets': tickets_info,
            'reservation_id': order.id,
        }

    @http.route(['/my/event/replace_reservation'], type='json', auth="user")
    def replace_reservation(self, reservation_id):
        """Cancel·la el pressupost existent i retorna les línies per reomplir el formulari"""
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order'].sudo()

        order = SaleOrder.browse(int(reservation_id))
        if not order.exists():
            raise AccessError("Pressupost inexistent")

        # 🔹 Buscar la família del partner actual
        miembro = request.env['familia.miembro'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not miembro or not miembro.familia_id:
            raise AccessError("Aquest usuari no pertany a cap família")

        familia = miembro.familia_id
        event = order.event_id

        # Cancel·lar tots els pressupostos familiars d'aquest event
        family_ids = familia.miembros_ids.mapped('partner_id').ids
        SaleOrder.search([
            ('partner_id', 'in', family_ids),
            ('event_id', '=', event.id),
            ('state', 'in', ['draft', 'sent']),
        ]).write({'state': 'cancel'})

        tickets_info = []
        for l in order.order_line:
            ticket = l.product_id.event_ticket_ids[:1]  # agafem el ticket relacionat
            tickets_info.append({
                'product': l.product_id.display_name,
                'qty': l.product_uom_qty,
                'ticket_id': ticket.id if ticket else l.product_id.id,
            })

        return {
            'tickets': tickets_info,
        }


    @http.route(['/my/event/validate_limits'], type='json', auth="user")
    def validate_limits(self, event_id, ticket_quantities):
        partner = request.env.user.partner_id
        miembro = request.env['familia.miembro'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not miembro or not miembro.familia_id:
            return {'ok': False, 'errors': ["Aquest usuari no pertany a cap família."]}

        familia = miembro.familia_id
        SaleOrder = request.env['sale.order'].sudo()

        # --------------------------
        # 1️⃣ Max faller (família completa, totes les comandes de l'event)
        # --------------------------
        family_lines = SaleOrder.search([
            ('partner_id', 'in', familia.miembros_ids.mapped('partner_id').ids),
            ('event_id', '=', int(event_id)),
            ('state', 'in', ['draft', 'sent', 'sale']),
        ]).mapped('order_line')

        totals_per_ticket = {}
        for l in family_lines:
            totals_per_ticket[l.product_id.id] = totals_per_ticket.get(l.product_id.id, 0) + l.product_uom_qty

        errors = []
        for ticket_id, qty in ticket_quantities.items():
            ticket = request.env['event.event.ticket'].sudo().browse(int(ticket_id))
            qty_total = totals_per_ticket.get(int(ticket_id), 0) + qty

            if ticket.seats_max and qty_total > ticket.seats_max:
                errors.append(
                    f"No es poden reservar més de {ticket.seats_max} unitats de {ticket.name} per família."
                )

        # --------------------------
        # 2️⃣ Límits individuals de despesa (només aquest membre, només hui)
        # --------------------------
        if miembro.tiene_limite:
            today = datetime.now().date()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())

            member_lines_today = SaleOrder.search([
                ('partner_id', '=', partner.id),
                ('event_id', '=', int(event_id)),
                ('state', 'in', ['draft', 'sent', 'sale']),
                ('create_date', '>=', start_of_day),
                ('create_date', '<=', end_of_day),
            ]).mapped('order_line')

            total_today = sum(member_lines_today.mapped(lambda l: l.price_unit * l.product_uom_qty))
            
            EventTicket = request.env['event.event.ticket'].sudo()
            new_total = sum(
                EventTicket.browse(int(ticket_id)).price * qty
                for ticket_id, qty in ticket_quantities.items()
            )

            if total_today + new_total > miembro.limite_gasto:
                errors.append(
                    f"Has superat el límit de despesa diari ({miembro.limite_gasto:.2f} €).\n\n"
                    f"👉 Ja portes gastats hui: {total_today:.2f} €\n"
                    f"👉 Intentes afegir: {new_total:.2f} €\n"
                    f"👉 Total resultaria: {total_today + new_total:.2f} €"
                )


        return {'ok': not errors, 'errors': errors}
