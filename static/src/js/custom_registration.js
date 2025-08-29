odoo.define('event_family_registration.custom_registration', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    var Dialog = require('web.Dialog');

    publicWidget.registry.CustomEventRegistration = publicWidget.Widget.extend({
        selector: '.register-btn',
        events: {
            'click': '_onRegisterClick',
        },

        start: function () {
            this._super.apply(this, arguments);

            var partner_id = $('button.register-btn').data('partner-id');
            var event_id = $('button.register-btn').data('event-id');

            if (event_id) {
                ajax.jsonRpc('/my/event/check_reservation', 'call', { event_id: event_id })
                    .then(result => {
                        if (result.has_reservation) {
                            const dialog = new Dialog(this, {
                                title: "Confirmació",
                                $content: $(`
                                    <div>
                                        ⚠️ Ja hi ha una reserva familiar feta per <b>${result.partner}</b>:
                                        <ul style="margin-top:8px; margin-bottom:8px;">
                                            ${result.tickets.map(t => `<li>${t.product} ×${t.qty}</li>`).join("")}
                                        </ul>
                                        <p>Vols substituir-la? Això la cancel·larà.</p>
                                    </div>
                                `),
                                buttons: [
                                    {
                                        text: "Ok",
                                        classes: "btn-primary",
                                        close: true,
                                        click: async () => {
                                            // 👉 Cancel·lar i recuperar línies
                                            const resp = await ajax.jsonRpc(
                                                "/my/event/replace_reservation",
                                                "call",
                                                { reservation_id: result.reservation_id }
                                            );
                                            if (resp && resp.tickets) {
                                                resp.tickets.forEach(t => {
                                                    const $input = $(`.ticket-quantity[data-ticket-id="${t.ticket_id}"]`);
                                                    if ($input.length) {
                                                        $input.val(t.qty).trigger('change');
                                                    } else {
                                                        console.warn("⚠️ No s’ha trobat input per al ticket:", t);
                                                    }
                                                });
                                                Dialog.alert(this, "✅ Reserva cancel·lada. Inicie una nova reserva.");
                                            }

                                        }
                                    },
                                    { text: "Cancel·lar", close: true }
                                ]
                            });
                            dialog.open();
                        }
                    })
                    .catch(err => console.error("Error comprovant reserva familiar:", err));
            }
        },

        _onRegisterClick: function (ev) {
            ev.preventDefault();
            var csrf_token = core.csrf_token;
            var partner_id = $(ev.currentTarget).data('partner-id');
            var event_id = $(ev.currentTarget).data('event-id');
            var order_id = $('input[name="order_id"]').val();

            var ticket_quantities = {};
            $('.ticket-quantity').each(function () {
                var ticket_id = parseInt($(this).data('ticket-id'));
                var quantity = parseInt($(this).val());
                if (quantity > 0) {
                    ticket_quantities[ticket_id] = quantity;
                }
            });

            if ($.isEmptyObject(ticket_quantities)) {
                Dialog.alert(this, "No has seleccionat cap tiquet.");
                return;
            }

            // 🔎 Nou pas: validar límits abans de registrar
            ajax.jsonRpc('/my/event/validate_limits', 'call', {
                event_id: event_id,
                ticket_quantities: ticket_quantities
            }).then(result => {
                if (!result.ok) {
                    Dialog.alert(this, "⚠️ Restriccions:\n- " + result.errors.join("\n- "));
                    return;
                }

                // ✅ Si passa validacions → registrar
                ajax.jsonRpc(`/event/${event_id}/register`, 'call', {
                    partner_id: partner_id,
                    ticket_quantities: ticket_quantities,
                    csrf_token: csrf_token,
                    order_id: order_id
                }).then(function (response) {
                    if (response.status === 'success') {
                        if (response.sale_order_id) {
                            window.location.href = `/my/orders/${response.sale_order_id}`;
                        } else {
                            Dialog.alert(this, "Registre completat.");
                        }
                    } else {
                        Dialog.alert(this, 'Error en el registre: ' + response.message);
                    }
                }.bind(this));
            });
        },
    });
});