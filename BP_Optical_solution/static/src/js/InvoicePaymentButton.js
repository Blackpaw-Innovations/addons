/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { InvoicePaymentPopup } from "@BP_Optical_solution/js/InvoicePaymentPopup";

export class InvoicePaymentButton extends Component {
    static template = "BP_Optical_solution.InvoicePaymentButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.state = useState({ hasOpenInvoices: false, lastPartnerId: null });
    }

    get shouldShow() {
        if (!this.pos.config.allow_invoice_payments) {
            return false;
        }
        const order = this.pos.get_order();
        const partner = order?.get_partner();
        if (!partner) {
            return false;
        }
        // Trigger async check if partner changed
        if (this.state.lastPartnerId !== partner.id) {
            this._checkOpenInvoices(partner.id);
        }
        return this.state.hasOpenInvoices;
    }

    async _checkOpenInvoices(partnerId) {
        this.state.lastPartnerId = partnerId;
        try {
            const count = await this.orm.call(
                "account.move",
                "search_count",
                [[
                    ["partner_id", "=", partnerId],
                    ["move_type", "=", "out_invoice"],
                    ["payment_state", "in", ["not_paid", "partial"]],
                    ["state", "=", "posted"],
                ]]
            );
            this.state.hasOpenInvoices = count > 0;
        } catch (e) {
            console.error("[InvoicePaymentButton] Error checking open invoices", e);
            this.state.hasOpenInvoices = false;
        }
    }

    async onClick() {
        console.log('[InvoicePaymentButton] Click detected');
        const order = this.pos.get_order();
        const partner = order?.get_partner();

        const popup = this.env.services.popup;

        if (!partner) {
            console.warn('[InvoicePaymentButton] No customer selected');
            await popup.add("ErrorPopup", {
                title: _t("Customer Required"),
                body: _t("Please select a customer before paying an invoice."),
            });
            return;
        }

        let confirmed, payload;
        try {
            console.log('[InvoicePaymentButton] Opening InvoicePaymentPopup for customer', partner.id);
            ({ confirmed, payload } = await popup.add(InvoicePaymentPopup, {
                partner: partner,
                allowPartialPayments: !!this.pos.config.allow_partial_invoice_payments,
            }));
            console.log('[InvoicePaymentButton] Popup closed - confirmed:', confirmed, 'payload:', payload);
        } catch (e) {
            console.error('[InvoicePaymentButton] Failed to open popup', e);
            await popup.add("ErrorPopup", {
                title: _t("Popup Error"),
                body: _t("Failed to open Invoice Payment popup."),
            });
            return;
        }

        if (confirmed && payload) {
            console.log('[InvoicePaymentButton] Invoice confirmed, adding to order', payload);

            // Set invoice payment metadata on order
            order.setInvoicePaymentData({
                invoice_id: payload.invoice_id,
                payment_amount: payload.invoice_payment_amount,
                payment_mode: payload.invoice_payment_mode,
                invoice_name: payload.invoice_name,
                invoice_residual_after: payload.invoice_residual_after,
            });

            // Find or use the first available product as a placeholder
            let invoicePaymentProduct = null;
            for (const product of Object.values(this.pos.db.product_by_id)) {
                if (product.default_code === 'INVOICE_PAYMENT') {
                    invoicePaymentProduct = product;
                    break;
                }
            }

            // If product not found, use any available product (we'll override its details)
            if (!invoicePaymentProduct) {
                console.warn('[InvoicePaymentButton] Invoice payment product not found, using fallback');
                const products = Object.values(this.pos.db.product_by_id);
                if (products.length > 0) {
                    invoicePaymentProduct = products[0];
                } else {
                    await popup.add("ErrorPopup", {
                        title: _t("Configuration Error"),
                        body: _t("No products available. Please configure your POS."),
                    });
                    return;
                }
            }

            console.log('[InvoicePaymentButton] Using product for invoice payment', invoicePaymentProduct);

            // Add the product to the order with custom price and description
            await order.add_product(invoicePaymentProduct, {
                price: payload.invoice_payment_amount,
                quantity: 1,
                merge: false,
            });

            // Update the last added line to reflect invoice payment details
            const lastLine = order.get_last_orderline();
            if (lastLine) {
                lastLine.set_unit_price(payload.invoice_payment_amount);
                lastLine.product.display_name = `Balance Payment: ${payload.invoice_name}`;
                lastLine.full_product_name = `Balance Payment: ${payload.invoice_name}`;
            }

            console.log('[InvoicePaymentButton] Invoice payment line added to order');
        }
    }
}

ProductScreen.addControlButton({
    component: InvoicePaymentButton,
});
