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
            'change .ticket-quantity': '_onTicketQuantityChange',
            'change select[name^="nb_register-"]': '_onSelectChange',
        },

        start: function () {
            this._super.apply(this, arguments);

            var partner_id = $('button.register-btn').data('partner-id');
            var event_id = $('button.register-btn').data('event-id');

            // 🆕 Comprovar reserva familiar immediatament
            if (event_id) {
                ajax.jsonRpc('/my/event/check_reservation', 'call', { event_id: event_id })
                    .then(result => {
                        if (result.has_reservation) {
                            let ticketsInfo = result.tickets.map(
                                t => `${t.product} x${t.qty}`
                            ).join(", ");
                            Dialog.confirm(this,
                                `⚠️ Ja hi ha una reserva familiar feta per <b>${result.partner}</b>: ${ticketsInfo}<br/>Vols substituir-la?`,
                                {
                                    confirm_callback: async () => {
                                        await ajax.jsonRpc("/my/event/replace_reservation", "call", { reservation_id: result.reservation_id });
                                        Dialog.alert(this, "✅ Reserva substituïda correctament. Ara pots continuar.");
                                    },
                                    cancel_callback: () => {
                                        window.location.href = `/event/${event_id}`;
                                    }
                                }
                            );
                        }
                    })
                    .catch(err => console.error("Error comprovant reserva familiar:", err));
            }

            if (partner_id && event_id) {
                // 🔵 Recuperar quantitats ja registrades
                ajax.jsonRpc('/event/registration_status', 'call', {
                    partner_id: partner_id,
                    event_id: event_id
                }).then(function (response) {
                    console.log("🎯 Dades recuperades:", response);

                    if (response.ticket_quantities) {
                        $('.ticket-quantity').each(function () {
                            var $input = $(this);
                            var ticket_id = parseInt($input.data('ticket-id'));

                            if (response.ticket_quantities[ticket_id] !== undefined) {
                                $input.val(response.ticket_quantities[ticket_id]);
                                console.log(`✔️ Assignat valor ${response.ticket_quantities[ticket_id]} a tiquet ${ticket_id}`);
                            }
                        });
                    }

                    if (response.order_id) {
                        if ($('input[name="order_id"]').length === 0) {
                            $('form.o_payment_form').append(`<input type="hidden" name="order_id" value="${response.order_id}"/>`);
                            console.log("✅ [CUSTOM REGISTRATION] Afegit hidden order_id:", response.order_id);
                        } else {
                            $('input[name="order_id"]').val(response.order_id);
                            console.log("✅ [CUSTOM REGISTRATION] Actualitzat hidden order_id:", response.order_id);
                        }
                    }
                });

                // 🔵 Recuperar límits màxims de família
                ajax.jsonRpc('/event/' + event_id + '/max_faller_limits', 'call', {
                    partner_id: partner_id
                }).then(function (limits) {
                    $('.ticket-quantity').each(function () {
                        var $input = $(this);
                        var ticket_id = $input.data('ticket-id');
                        var ticket_max = parseInt($input.data('ticket-max'));

                        var familia_limit = limits[ticket_id];
                        var final_max = ticket_max;

                        if (familia_limit !== undefined) {
                            final_max = isNaN(ticket_max) ? familia_limit : Math.min(ticket_max, familia_limit);
                        }

                        if (!isNaN(final_max)) {
                            $input.attr('max', final_max);
                            if (parseInt($input.val()) > final_max) {
                                $input.val(final_max);
                                console.log(`⚠️ S'ha ajustat a límit ${final_max} el tiquet ${ticket_id}`);
                            }
                        }
                    });
                });
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
                    console.log("Tiquet ID: ", ticket_id, "Quantitat: ", quantity);
                }
            });

            if ($.isEmptyObject(ticket_quantities)) {
                Dialog.alert(this, "No has seleccionat cap tiquet.");
                return;
            }

            ajax.jsonRpc('/event/' + event_id + '/register', 'call', {
                partner_id: partner_id,
                ticket_quantities: ticket_quantities,
                csrf_token: csrf_token,
                order_id: order_id
            }).then(function (response) {
                if (response.status === 'success') {
                    console.log("Registre completat: " + response.message);
                    Dialog.alert(this, "Registre completat.");
                    if (response.sale_order_id) {
                        window.location.href = '/my/orders/' + response.sale_order_id;
                    }
                } else {
                    Dialog.alert(this, 'Error en el registre: ' + response.message);
                }
            }.bind(this)).catch(function (error) {
                console.error("Error en la sol·licitud AJAX: ", error);
                Dialog.alert(this, 'Error en el registre.');
            }.bind(this));
        },

        _onTicketQuantityChange: function (ev) {
            var quantity = $(ev.currentTarget).val();
            console.log("Quantitat seleccionada: ", quantity);
        },

        _onSelectChange: function (ev) {
            var selectedValue = $(ev.currentTarget).val();
            console.log("Valor seleccionat en el select: ", selectedValue);
        }
    });
});
