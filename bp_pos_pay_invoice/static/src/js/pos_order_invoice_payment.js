/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.is_invoice_payment = this.is_invoice_payment || false;
        this.invoice_id = this.invoice_id || null;
        this.invoice_payment_amount = this.invoice_payment_amount || 0;
        this.invoice_payment_mode = this.invoice_payment_mode || null;
    },

    setInvoicePaymentData({ invoice_id, payment_amount, payment_mode, invoice_name, invoice_residual_after }) {
        this.is_invoice_payment = Boolean(invoice_id);
        this.invoice_id = invoice_id || null;
        this.invoice_payment_amount = payment_amount || 0;
        this.invoice_payment_mode = payment_mode || null;
        this.invoice_name = invoice_name || null;
        this.invoice_residual_after = invoice_residual_after ?? null;
        // Notify POS that order has changed
        this.pos.selectedOrder = this;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.is_invoice_payment = this.is_invoice_payment || false;
        json.invoice_id = this.invoice_id || null;
        json.invoice_payment_amount = this.invoice_payment_amount || 0;
        json.invoice_payment_mode = this.invoice_payment_mode || null;
        json.invoice_name = this.invoice_name || null;
        json.invoice_residual_after = this.invoice_residual_after ?? null;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.is_invoice_payment = json.is_invoice_payment || false;
        this.invoice_id = json.invoice_id || null;
        this.invoice_payment_amount = json.invoice_payment_amount || 0;
        this.invoice_payment_mode = json.invoice_payment_mode || null;
        this.invoice_name = json.invoice_name || null;
        this.invoice_residual_after = json.invoice_residual_after ?? null;
    },
});
