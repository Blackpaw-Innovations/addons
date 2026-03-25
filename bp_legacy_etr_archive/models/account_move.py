from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    bp_legacy_source_dump = fields.Char(
        string="Legacy Source Dump",
        readonly=True,
        copy=False,
        help="Dump or extract bundle used to archive these legacy values.",
    )
    bp_legacy_source_record_id = fields.Integer(
        string="Legacy Source Record ID",
        readonly=True,
        copy=False,
        index=True,
        help="Original account.move id in the legacy dump.",
    )
    bp_legacy_archive_match_method = fields.Char(
        string="Legacy Match Method",
        readonly=True,
        copy=False,
        help="Matching strategy used during the archive import.",
    )
    bp_legacy_archive_imported_at = fields.Datetime(
        string="Legacy Imported At",
        readonly=True,
        copy=False,
    )
    bp_legacy_archive_imported_by = fields.Many2one(
        "res.users",
        string="Legacy Imported By",
        readonly=True,
        copy=False,
    )
    bp_legacy_archive_note = fields.Text(
        string="Legacy Archive Note",
        readonly=True,
        copy=False,
    )
    bp_legacy_oscu_receipt_number = fields.Char(
        string="Legacy OSCU Receipt Number",
        readonly=True,
        copy=False,
    )
    bp_legacy_oscu_invoice_number = fields.Char(
        string="Legacy OSCU Invoice Number",
        readonly=True,
        copy=False,
    )
    bp_legacy_oscu_signature = fields.Text(
        string="Legacy OSCU Signature",
        readonly=True,
        copy=False,
    )
    bp_legacy_oscu_internal_data = fields.Text(
        string="Legacy OSCU Internal Data",
        readonly=True,
        copy=False,
    )
    bp_legacy_control_unit = fields.Char(
        string="Legacy Control Unit",
        readonly=True,
        copy=False,
    )
    bp_legacy_oscu_confirmation_datetime = fields.Datetime(
        string="Legacy OSCU Confirmation Datetime",
        readonly=True,
        copy=False,
    )
    bp_legacy_oscu_datetime = fields.Datetime(
        string="Legacy OSCU Datetime",
        readonly=True,
        copy=False,
    )
    bp_legacy_studio_etr = fields.Char(
        string="Legacy Studio ETR",
        readonly=True,
        copy=False,
    )
    bp_legacy_studio_nakuru_etr = fields.Char(
        string="Legacy Studio Nakuru ETR",
        readonly=True,
        copy=False,
    )
    bp_legacy_etr_archive_present = fields.Boolean(
        string="Legacy ETR Archived",
        compute="_compute_bp_legacy_etr_archive_present",
        store=True,
        readonly=True,
        copy=False,
        help="Technical flag used to find records carrying archived legacy ETR data.",
    )

    @api.depends(
        "bp_legacy_oscu_receipt_number",
        "bp_legacy_oscu_invoice_number",
        "bp_legacy_oscu_signature",
        "bp_legacy_oscu_internal_data",
        "bp_legacy_control_unit",
        "bp_legacy_oscu_confirmation_datetime",
        "bp_legacy_oscu_datetime",
        "bp_legacy_studio_etr",
        "bp_legacy_studio_nakuru_etr",
    )
    def _compute_bp_legacy_etr_archive_present(self):
        for move in self:
            move.bp_legacy_etr_archive_present = any(
                (
                    move.bp_legacy_oscu_receipt_number,
                    move.bp_legacy_oscu_invoice_number,
                    move.bp_legacy_oscu_signature,
                    move.bp_legacy_oscu_internal_data,
                    move.bp_legacy_control_unit,
                    move.bp_legacy_oscu_confirmation_datetime,
                    move.bp_legacy_oscu_datetime,
                    move.bp_legacy_studio_etr,
                    move.bp_legacy_studio_nakuru_etr,
                )
            )
