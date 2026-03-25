from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestLegacyEtrArchive(AccountTestInvoicingCommon):
    def test_account_move_archive_flag_and_copy(self):
        move = self.init_invoice("out_invoice", amounts=[100.0], taxes=[])
        self.assertFalse(move.bp_legacy_etr_archive_present)

        move.write(
            {
                "bp_legacy_oscu_receipt_number": "25382",
                "bp_legacy_oscu_invoice_number": "25382",
                "bp_legacy_studio_etr": "25382",
            }
        )
        move.invalidate_recordset(["bp_legacy_etr_archive_present"])

        self.assertTrue(move.bp_legacy_etr_archive_present)

        duplicate_move = move.copy()
        duplicate_move.invalidate_recordset(
            [
                "bp_legacy_oscu_receipt_number",
                "bp_legacy_oscu_invoice_number",
                "bp_legacy_studio_etr",
                "bp_legacy_etr_archive_present",
            ]
        )

        self.assertFalse(duplicate_move.bp_legacy_oscu_receipt_number)
        self.assertFalse(duplicate_move.bp_legacy_oscu_invoice_number)
        self.assertFalse(duplicate_move.bp_legacy_studio_etr)
        self.assertFalse(duplicate_move.bp_legacy_etr_archive_present)

    def test_stock_move_archive_flag(self):
        move = self.env["stock.move"].new({})
        self.assertFalse(move.bp_legacy_etr_archive_present)

        move.bp_legacy_oscu_flow_type_code = "11"
        move._compute_bp_legacy_etr_archive_present()

        self.assertTrue(move.bp_legacy_etr_archive_present)
