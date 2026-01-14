/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
import { _t } from "@web/core/l10n/translation";


patch(OrderReceipt.prototype, {
    setup() {
        super.setup();
        var self= this;
        this.orm = useService("orm");
    },
    // /**
    //  * For accessibility, pressing <space> should be like clicking the product.
    //  * <enter> is not considered because it conflicts with the barcode.
    //  *
    //  * @param {KeyPressEvent} event
    //  */
   
    //  async seq_data(){
    //     var self = this;
    //     let order=self.pos.get_order();
    //     await this.orm.call(
    //         'pos.order',
    //         'create_pos_receipt_sequence',  
    //         [0,order.pos_session_id],

    //     ).then(function(seq_code) {
    //         order.set_seq_code(seq_code)
    //     })

    // },
    get sequence(){
        var self=this;
        let order=self.pos.get_order();
        return order.sequence_code

    },
});