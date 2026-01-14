/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class InvoicePaymentPopup extends Component {
    static template = "bp_pos_pay_invoice.InvoicePaymentPopup";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            invoices: [],
            selectedInvoiceId: null,
            paymentAmount: 0,
            loading: false,
        });
        onMounted(() => this.loadInvoices());
    }

    get allowPartialPayments() {
        return Boolean(this.props.allowPartialPayments);
    }

    async loadInvoices() {
        const partner = this.props.partner;
        if (!partner) {
            this.state.invoices = [];
            return;
        }
        try {
            this.state.loading = true;
            const invoices = await this.orm.call(
                "bp.pos.invoice.payment.wizard",
                "get_open_invoices_for_partner",
                [partner.id]
            );
            this.state.invoices = invoices || [];
            if (this.state.invoices.length) {
                const first = this.state.invoices[0];
                this.state.selectedInvoiceId = first.id;
                this.state.paymentAmount = first.amount_residual;
            } else {
                this.state.selectedInvoiceId = null;
                this.state.paymentAmount = 0;
            }
        } catch (error) {
            console.error("Failed to load invoices", error);
            this.notification.add(_t("Could not load invoices."), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    selectInvoice(invoice) {
        this.state.selectedInvoiceId = invoice.id;
        this.state.paymentAmount = invoice.amount_residual;
    }

    onAmountChange(ev) {
        const value = parseFloat(ev.target.value);
        this.state.paymentAmount = isNaN(value) ? 0 : value;
    }

    confirm() {
        console.log('[InvoicePaymentPopup] Confirm clicked');
        const invoice = this.state.invoices.find((inv) => inv.id === this.state.selectedInvoiceId);
        if (!invoice) {
            this.notification.add(_t("Please select an invoice."), { type: "warning" });
            return;
        }
        const amount = this.state.paymentAmount;
        if (!amount || amount <= 0) {
            this.notification.add(_t("Payment amount must be greater than zero."), { type: "warning" });
            return;
        }
        if (amount > invoice.amount_residual) {
            this.notification.add(
                _t("Payment amount cannot exceed the invoice residual."),
                { type: "warning" }
            );
            return;
        }
        const paymentMode = amount >= invoice.amount_residual ? "full" : "partial";
        const residualAfter = Math.max(invoice.amount_residual - amount, 0);

        const payload = {
            invoice_id: invoice.id,
            invoice_payment_amount: amount,
            invoice_payment_mode: paymentMode,
            invoice_name: invoice.name,
            invoice_residual_after: residualAfter,
        };

        console.log('[InvoicePaymentPopup] Closing with payload', payload);
        this.props.close({ confirmed: true, payload });
    }

    cancel() {
        console.log('[InvoicePaymentPopup] Cancel clicked');
        this.props.close({ confirmed: false, payload: null });
    }
}
