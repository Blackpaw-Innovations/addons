/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/store/models";

// Patching Orderline to add barber functionality
patch(Orderline.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        if (options.json) {
            this.barber_name = this.barber_name;
            this.barber_id = this.barber_id;
        }
    },

    export_as_JSON() {
        var json = super.export_as_JSON.call(this);
        json.barber_name = this.barber_name || false;
        json.barber_id = this.barber_id || false;
        return json;
    },

    // Set the barber from the JSON data
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.barber_name = json.barber_name;
        this.barber_id = json.barber_id;
    },

    get_barber() {
        return {
            name: this.barber_name,
            id: this.barber_id
        };
    },

    getDisplayData() {
        return {
            ...super.getDisplayData(),
            barber_name: this.barber_name,
            barber_id: this.barber_id,
            requires_service_provider: this.product.requires_service_provider,
        };
    },

    // Check if this line requires a barber
    requiresBarber() {
        return this.product && this.product.requires_service_provider;
    },

    // Check if barber is assigned
    hasBarberAssigned() {
        return Boolean(this.barber_id);
    },
});