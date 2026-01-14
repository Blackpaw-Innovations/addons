odoo.define('bp_barber_management.booking_slots', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    var publicWidget = require('web.public.widget');

    var _t = core._t;

    publicWidget.registry.BookingSlots = publicWidget.Widget.extend({
        selector: '#booking-form',
        events: {
            'click #check-availability': '_onCheckAvailability',
            'click .slot-button': '_onSlotSelect',
            'change .service-checkbox': '_onServiceChange',
            'change #barber_id': '_onBarberChange',
            'change #booking_date': '_onDateChange',
        },

        /**
         * @override
         */
        start: function () {
            this._resetForm();
            return this._super.apply(this, arguments);
        },

        /**
         * Handle check availability button click
         */
        _onCheckAvailability: function (ev) {
            ev.preventDefault();
            console.log('Check availability button clicked');

            var serviceIds = this._getSelectedServices();
            var barberId = this.$('#barber_id').val();
            var date = this.$('#booking_date').val();

            console.log('Form values:', { serviceIds: serviceIds, barberId: barberId, date: date });

            if (!serviceIds.length) {
                this._showAlert('Please select at least one service.', 'warning');
                return;
            }

            if (!barberId) {
                this._showAlert('Please select a barber.', 'warning');
                return;
            }

            if (!date) {
                this._showAlert('Please select a date.', 'warning');
                return;
            }

            this._loadAvailableSlots(barberId, date, serviceIds);
        },

        /**
         * Handle slot selection
         */
        _onSlotSelect: function (ev) {
            ev.preventDefault();

            // Remove selection from other slots
            this.$('.slot-button').removeClass('btn-primary').addClass('btn-outline-primary');

            // Mark this slot as selected
            var $slot = $(ev.currentTarget);
            $slot.removeClass('btn-outline-primary').addClass('btn-primary');

            // Store the selected slot
            var slotStart = $slot.data('slot-start');
            this.$('#slot_start').val(slotStart);

            // Show contact form
            this._showContactForm();
        },

        /**
         * Handle service checkbox change
         */
        _onServiceChange: function (ev) {
            this._updateServiceSelection();
            this._resetSlots();
        },

        /**
         * Handle barber change
         */
        _onBarberChange: function (ev) {
            this._resetSlots();
        },

        /**
         * Handle date change
         */
        _onDateChange: function (ev) {
            this._resetSlots();
        },

        /**
         * Load available slots from server
         */
        _loadAvailableSlots: function (barberId, date, serviceIds) {
            var self = this;

            // Show loading
            this.$('#check-availability').prop('disabled', true).html('<i class="fa fa-spinner fa-spin me-2"></i>Loading...');

            ajax.jsonRpc('/barber/booking/slots', 'call', {
                barber_id: parseInt(barberId),
                date: date,
                service_ids: serviceIds.map(function (id) { return parseInt(id); })
            }).then(function (result) {
                self.$('#check-availability').prop('disabled', false).html('<i class="fa fa-search me-2"></i>Check Available Times');

                if (result.error) {
                    self._showAlert(result.error, 'danger');
                    return;
                }

                self._displaySlots(result.slots);
            }).catch(function (error) {
                self.$('#check-availability').prop('disabled', false).html('<i class="fa fa-search me-2"></i>Check Available Times');
                console.error('Error loading slots:', error);
                self._showAlert('An error occurred while loading available times. Please try again.', 'danger');
            });
        },

        /**
         * Display available slots
         */
        _displaySlots: function (slots) {
            var $slotsList = this.$('#slots-list');
            var $slotsContainer = this.$('#slots-container');

            $slotsList.empty();

            if (!slots || slots.length === 0) {
                $slotsList.html('<div class="alert alert-info">No available time slots for the selected date. Please choose another date.</div>');
            } else {
                slots.forEach(function (slot) {
                    var $slotButton = $('<button type="button" class="btn btn-outline-primary slot-button me-2 mb-2"></button>')
                        .text(slot.display)
                        .data('slot-start', slot.start)
                        .data('slot-end', slot.end);
                    $slotsList.append($slotButton);
                });
            }

            $slotsContainer.show();
            this._hideContactForm();
        },

        /**
         * Show contact form section
         */
        _showContactForm: function () {
            this.$('#contact-section').show();
            this.$('#submit-section').show();
        },

        /**
         * Hide contact form section
         */
        _hideContactForm: function () {
            this.$('#contact-section').hide();
            this.$('#submit-section').hide();
            this.$('#slot_start').val('');
        },

        /**
         * Reset slots display
         */
        _resetSlots: function () {
            this.$('#slots-container').hide();
            this.$('#slots-list').empty();
            this._hideContactForm();
        },

        /**
         * Reset entire form
         */
        _resetForm: function () {
            this._resetSlots();
            this._updateServiceSelection();
        },

        /**
         * Get selected service IDs
         */
        _getSelectedServices: function () {
            var serviceIds = [];
            this.$('.service-checkbox:checked').each(function () {
                serviceIds.push($(this).val());
            });
            return serviceIds;
        },

        /**
         * Update hidden service_ids field
         */
        _updateServiceSelection: function () {
            var serviceIds = this._getSelectedServices();
            this.$('#service_ids').val(serviceIds.join(','));
        },

        /**
         * Show alert message
         */
        _showAlert: function (message, type) {
            // Remove existing alerts
            this.$('.temp-alert').remove();

            // Add new alert
            var $alert = $('<div class="alert alert-' + type + ' temp-alert" role="alert"></div>')
                .html('<i class="fa fa-exclamation-triangle me-2"></i>' + message);

            this.$('.card-body').prepend($alert);

            // Auto-hide after 5 seconds
            setTimeout(function () {
                $alert.fadeOut(function () {
                    $(this).remove();
                });
            }, 5000);
        }
    });

    return publicWidget.registry.BookingSlots;

});