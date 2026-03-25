from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

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
        help="Original stock.move id in the legacy dump.",
    )
    bp_legacy_archive_match_method = fields.Char(
        string="Legacy Match Method",
        readonly=True,
        copy=False,
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
    bp_legacy_oscu_sar_number = fields.Char(
        string="Legacy OSCU SAR Number",
        readonly=True,
        copy=False,
    )
    bp_legacy_oscu_flow_type_code = fields.Char(
        string="Legacy OSCU Flow Type Code",
        readonly=True,
        copy=False,
    )
    bp_legacy_etr_archive_present = fields.Boolean(
        string="Legacy ETR Archived",
        compute="_compute_bp_legacy_etr_archive_present",
        store=True,
        readonly=True,
        copy=False,
        help="Technical flag used to find stock moves carrying archived legacy ETR data.",
    )

    @api.depends(
        "bp_legacy_oscu_sar_number",
        "bp_legacy_oscu_flow_type_code",
    )
    def _compute_bp_legacy_etr_archive_present(self):
        for move in self:
            move.bp_legacy_etr_archive_present = any(
                (
                    move.bp_legacy_oscu_sar_number,
                    move.bp_legacy_oscu_flow_type_code,
                )
            )
