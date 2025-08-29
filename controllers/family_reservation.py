from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
import logging
_logger = logging.getLogger(__name__)

class FamilyReservationController(http.Controller):

    @http.route(['/my/event/check_reservation'], type='json', auth="user")
    def check_reservation(self, event_id):
        partner = request.env.user.partner_id
        Miembro = request.env['familia.miembro'].sudo()
        miembro = Miembro.search([('partner_id', '=', partner.id)], limit=1)
        if not miembro:
            _logger.info("❌ Partner %s no és membre de cap família", partner.id)
            return {'has_reservation': False}

        familia = miembro.familia_id
        Reservation = request.env['event.registration'].sudo()
        existing = Reservation.search([
            ('partner_id', 'in', familia.miembro_ids.mapped('partner_id').ids),
            ('event_id', '=', int(event_id)),
            ('state', '!=', 'cancel'),
        ], limit=1)

        if existing:
            return {
                'has_reservation': True,
                'partner': existing.partner_id.name,
                'tickets': [
                    {'product': existing.event_ticket_id.name, 'qty': existing.nb_register}
                ],
                'reservation_id': existing.id,
            }

        return {'has_reservation': False}


    @http.route(['/my/event/replace_reservation'], type='json', auth="user")
    def replace_reservation(self, reservation_id):
        """Cancel·la la reserva existent i crea una nova per a l'usuari actual"""
        partner = request.env.user.partner_id
        Reservation = request.env['event.registration'].sudo()

        existing = Reservation.browse(int(reservation_id))
        if not existing.exists():
            raise AccessError("Reserva inexistent")

        # Cancel·lar la reserva antiga
        existing.write({'state': 'cancel'})

        # Crear nova amb les mateixes dades
        new_res = Reservation.create({
            'partner_id': partner.id,
            'event_id': existing.event_id.id,
            'event_ticket_id': existing.event_ticket_id.id,
            'nb_register': existing.nb_register,
        })
        return {
            'new_id': new_res.id,
            'tickets': [{'product': new_res.event_ticket_id.name, 'qty': new_res.nb_register}],
        }
