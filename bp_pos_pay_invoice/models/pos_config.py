from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_invoice_payments: fields.Boolean = fields.Boolean(
        string="Allow Invoice Payments in POS",
        default=False,
        help="Enable creation of payments on customer invoices directly from POS.",
    )
    allow_partial_invoice_payments: fields.Boolean = fields.Boolean(
        string="Allow Partial Invoice Payments",
        default=False,
    )
    default_invoice_payment_mode: fields.Selection = fields.Selection(
        selection=[
            ("deposit", "Deposit"),
            ("balance", "Balance"),
            ("full", "Full"),
        ],
        string="Default Invoice Payment Mode",
        default="full",
    )

    @api.model
    def _loader_params_pos_config(self):
        """Ensure custom fields are sent to the POS frontend."""
        res = super()._loader_params_pos_config()
        fields_list = res.get("search_params", {}).setdefault("fields", [])
        extra_fields = [
            "allow_invoice_payments",
            "allow_partial_invoice_payments",
            "default_invoice_payment_mode",
        ]
        for field_name in extra_fields:
            if field_name not in fields_list:
                fields_list.append(field_name)
        return res

    @api.model
    def _get_pos_ui_pos_config(self, params):
        """Ensure extra fields are present in the POS UI payload."""
        config_data = super()._get_pos_ui_pos_config(params)
        for config in config_data:
            config.setdefault("allow_invoice_payments", False)
            config.setdefault("allow_partial_invoice_payments", False)
            config.setdefault("default_invoice_payment_mode", "full")
        return config_data
