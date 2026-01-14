/** @odoo-module **/
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

export class BarberAssignmentButton extends Component {
    setup() {
        super.setup();
        this.pos = usePos();
        const { popup } = this.env.services;
        this.popup = popup;
    }

    async onClick() {
        const selectedLine = this.pos.selectedOrder?.selected_orderline;
        if (!selectedLine) {
            await this.popup.add(ErrorPopup, {
                title: _t("No Product Selected"),
                body: _t("Please select a product line first.")
            });
            return;
        }

        if (!this.pos.barbers || this.pos.barbers.length === 0) {
            await this.popup.add(ErrorPopup, {
                title: _t("No Barbers Available"),
                body: _t("Please configure barbers in the system.")
            });
            return;
        }

        const barberList = this.pos.barbers.map((barber) => {
            return {
                id: barber.id,
                item: barber,
                label: barber.name,
                isSelected: selectedLine.barber_id === barber.id,
            };
        });

        const { confirmed, payload: barber } = await this.popup.add(SelectionPopup, {
            title: _t("Select Barber for ") + selectedLine.product.display_name,
            list: barberList,
        });

        if (confirmed) {
            selectedLine.barber_name = barber.name;
            selectedLine.barber_id = barber.id;
        }
    }
}

BarberAssignmentButton.template = "BarberAssignmentButton";

ProductScreen.addControlButton({
    component: BarberAssignmentButton,
    condition: function () {
        const selectedLine = this.selectedOrder?.selected_orderline;
        return this.config.enable_barber_mode &&
            selectedLine &&
            selectedLine.product &&
            selectedLine.product.requires_service_provider;
    },
});

console.log("Barber Management: POS Screen JS loaded successfully");