odoo.define('sv_pos_kitchen_show.kitchen_show', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');
    var QWeb = core.qweb;

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        // Imprimir cambios de la comanda
        printChanges: async function(){
            var printers = this.pos.printers;
            let isPrintSuccessful = true;
            for(var i = 0; i < printers.length; i++){
                var changes = this.computeChanges(printers[i].config.product_categories_ids);
                if ( changes['new'].length > 0 || changes['cancelled'].length > 0){
                    var receipt = QWeb.render('OrderChangeReceipt',{changes:changes, widget:this});
                    const result = await printers[i].print_receipt(receipt);
                    if (!result.successful) {
                        isPrintSuccessful = false;
                    }
                    if (this.pos.config.is_show_kitchen === true) {
                        // Definimos el tamaño de la ventana a mostrar
                        var left = (screen.width);
                        var top = (screen.height);
                        var myWindow = window.open("", "COMANDAS", "width=450,height=300,left=" + left / 4 + ",top=" + top / 4);
                        // Renderizamos en la web la comanda
                        myWindow.document.write(receipt);
                        isPrintSuccessful = true;
                    }
                }
            }
            return isPrintSuccessful;
        },
    })
});
