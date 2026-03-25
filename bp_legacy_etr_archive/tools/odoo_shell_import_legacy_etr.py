import csv
import json
from pathlib import Path

from odoo import fields


if "env" not in globals():
    raise RuntimeError("Run this script inside `odoo shell` so `env` is available.")


# Edit DEFAULT_CONFIG directly for a one-off run, or inject a LEGACY_ETR_CONFIG
# dict into the shell session before executing this script.
DEFAULT_CONFIG = {
    "source_dump_name": "rvmservice.dump.zip",
    "account_csv": r"c:\LocalHost\_tmp_rvmservice_dump\assessment\etr_account_moves_documents_only.csv",
    "stock_csv": r"c:\LocalHost\_tmp_rvmservice_dump\assessment\etr_stock_moves_flagged.csv",
    "report_dir": r"c:\LocalHost\_tmp_rvmservice_dump\assessment\odoo_import_reports",
    "company_id_map": {},
    "company_name_map": {},
    "allow_single_company_fallback": True,
    "limit": None,
    "apply_account": False,
    "apply_stock": False,
    "allow_fallback_account_apply": False,
    "allow_stock_apply_methods": ["reference_product_exact"],
    "stock_row_limit_for_apply": 250,
}


LEGACY_ETR_CONFIG = {**DEFAULT_CONFIG, **globals().get("LEGACY_ETR_CONFIG", {})}

ACCOUNT_FIELD_MAP = {
    "l10n_ke_oscu_receipt_number": "bp_legacy_oscu_receipt_number",
    "l10n_ke_oscu_invoice_number": "bp_legacy_oscu_invoice_number",
    "l10n_ke_oscu_signature": "bp_legacy_oscu_signature",
    "l10n_ke_oscu_internal_data": "bp_legacy_oscu_internal_data",
    "l10n_ke_control_unit": "bp_legacy_control_unit",
    "l10n_ke_oscu_confirmation_datetime": "bp_legacy_oscu_confirmation_datetime",
    "l10n_ke_oscu_datetime": "bp_legacy_oscu_datetime",
    "x_studio_etr": "bp_legacy_studio_etr",
    "x_studio_nakuru_etr": "bp_legacy_studio_nakuru_etr",
}

STOCK_FIELD_MAP = {
    "l10n_ke_oscu_sar_number": "bp_legacy_oscu_sar_number",
    "l10n_ke_oscu_flow_type_code": "bp_legacy_oscu_flow_type_code",
}

SAFE_ACCOUNT_APPLY_METHODS = {
    "name_exact",
    "ref_exact",
    "payment_reference_exact",
}


def clean(value):
    if value in (None, False):
        return False
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    return value or False


def parse_float(value):
    value = clean(value)
    if not value:
        return 0.0
    return float(value)


def floats_match(left, right, precision=0.0001):
    return abs((left or 0.0) - (right or 0.0)) <= precision


def read_rows(csv_path):
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    limit = LEGACY_ETR_CONFIG["limit"]
    return rows[:limit] if limit else rows


def ensure_fields(model_name, field_names):
    model = env[model_name]
    missing = sorted(field_name for field_name in field_names if field_name not in model._fields)
    if missing:
        raise ValueError(f"Missing fields on {model_name}: {missing}")


def resolve_company_id(row):
    source_company_id = clean(row.get("company_id"))
    source_company_name = clean(row.get("company_name"))
    company_model = env["res.company"].sudo().with_context(active_test=False)

    company_id_map = LEGACY_ETR_CONFIG["company_id_map"]
    if source_company_id:
        if source_company_id in company_id_map:
            return int(company_id_map[source_company_id]), "company_id_map"
        if source_company_id.isdigit() and int(source_company_id) in company_id_map:
            return int(company_id_map[int(source_company_id)]), "company_id_map"

    if source_company_name and source_company_name in LEGACY_ETR_CONFIG["company_name_map"]:
        mapped_value = LEGACY_ETR_CONFIG["company_name_map"][source_company_name]
        if isinstance(mapped_value, int):
            return mapped_value, "company_name_map"
        company = company_model.search([("name", "=", mapped_value)], limit=1)
        if company:
            return company.id, "company_name_map"

    if source_company_name:
        company = company_model.search([("name", "=", source_company_name)])
        if len(company) == 1:
            return company.id, "company_name_exact"

    companies = company_model.search([])
    if LEGACY_ETR_CONFIG["allow_single_company_fallback"] and len(companies) == 1:
        return companies.id, "single_company_fallback"

    return False, "company_unresolved"


def row_partner_tokens(row):
    tokens = {
        clean(row.get("partner_name")),
        clean(row.get("partner_ref")),
        clean(row.get("partner_vat")),
    }
    return {token for token in tokens if token}


def account_candidate_is_consistent(row, candidate):
    expected_amount_total = parse_float(row.get("amount_total"))
    date_tokens = {
        clean(row.get("date")),
        clean(row.get("invoice_date")),
    }
    date_tokens = {token for token in date_tokens if token}
    partner_tokens = row_partner_tokens(row)
    candidate_tokens = {
        clean(candidate.partner_id.name),
        clean(candidate.partner_id.ref),
        clean(candidate.partner_id.vat),
    }
    candidate_tokens = {token for token in candidate_tokens if token}

    if date_tokens:
        candidate_dates = {
            clean(str(candidate.date or "")),
            clean(str(candidate.invoice_date or "")),
        }
        candidate_dates = {token for token in candidate_dates if token}
        if not (date_tokens & candidate_dates):
            return False

    if clean(row.get("amount_total")) and not floats_match(candidate.amount_total, expected_amount_total):
        return False

    if partner_tokens and candidate_tokens and not (partner_tokens & candidate_tokens):
        return False

    return True


def narrow_account_candidates(row, candidates):
    filtered = candidates.filtered(lambda move: account_candidate_is_consistent(row, move))
    return filtered or candidates


def find_account_move(row, company_id):
    move_model = env["account.move"].sudo().with_context(active_test=False)
    move_type = clean(row.get("move_type"))
    strategies = []

    if clean(row.get("move_name")):
        strategies.append(
            (
                "name_exact",
                [
                    ("company_id", "=", company_id),
                    ("move_type", "=", move_type),
                    ("name", "=", clean(row["move_name"])),
                ],
            )
        )
    if clean(row.get("ref")):
        strategies.append(
            (
                "ref_exact",
                [
                    ("company_id", "=", company_id),
                    ("move_type", "=", move_type),
                    ("ref", "=", clean(row["ref"])),
                ],
            )
        )
    if clean(row.get("payment_reference")):
        strategies.append(
            (
                "payment_reference_exact",
                [
                    ("company_id", "=", company_id),
                    ("move_type", "=", move_type),
                    ("payment_reference", "=", clean(row["payment_reference"])),
                ],
            )
        )

    for method, domain in strategies:
        candidates = move_model.search(domain)
        narrowed = narrow_account_candidates(row, candidates)
        if len(narrowed) == 1:
            return narrowed, method, len(candidates)

    date_tokens = [token for token in (clean(row.get("invoice_date")), clean(row.get("date"))) if token]
    for date_token in date_tokens:
        candidates = move_model.search(
            [
                ("company_id", "=", company_id),
                ("move_type", "=", move_type),
                "|",
                ("invoice_date", "=", date_token),
                ("date", "=", date_token),
            ]
        )
        narrowed = narrow_account_candidates(row, candidates)
        if len(narrowed) == 1:
            return narrowed, "date_amount_partner", len(candidates)

    return move_model.browse(), "unmatched", 0


def resolve_product(row):
    product_model = env["product.product"].sudo().with_context(active_test=False)
    product_code = clean(row.get("product_default_code"))
    barcode = clean(row.get("product_barcode"))
    product_name = clean(row.get("product_name"))

    if product_code:
        products = product_model.search([("default_code", "=", product_code)])
        if len(products) == 1:
            return products, "default_code_exact"

    if barcode:
        products = product_model.search([("barcode", "=", barcode)])
        if len(products) == 1:
            return products, "barcode_exact"

    if product_name:
        products = product_model.search([("name", "=", product_name)])
        if len(products) == 1:
            return products, "name_exact"

    return product_model.browse(), "product_unresolved"


def stock_candidate_is_consistent(row, candidate):
    if clean(row.get("reference")) and clean(candidate.reference) != clean(row.get("reference")):
        return False
    if clean(row.get("origin")) and clean(candidate.origin) and clean(candidate.origin) != clean(row.get("origin")):
        return False
    if clean(row.get("date")):
        candidate_date = clean(fields.Datetime.to_string(candidate.date))
        if candidate_date and candidate_date[:10] != clean(row.get("date"))[:10]:
            return False
    if clean(row.get("product_uom_qty")) and not floats_match(candidate.product_uom_qty, parse_float(row.get("product_uom_qty"))):
        return False
    return True


def find_stock_move(row, company_id):
    move_model = env["stock.move"].sudo().with_context(active_test=False)
    product, product_method = resolve_product(row)
    if not product:
        return move_model.browse(), product_method, 0

    strategies = []
    if clean(row.get("reference")):
        strategies.append(
            (
                "reference_product_exact",
                [
                    ("company_id", "=", company_id),
                    ("reference", "=", clean(row["reference"])),
                    ("product_id", "=", product.id),
                ],
            )
        )
    if clean(row.get("picking_name")):
        strategies.append(
            (
                "picking_product_exact",
                [
                    ("company_id", "=", company_id),
                    ("picking_id.name", "=", clean(row["picking_name"])),
                    ("product_id", "=", product.id),
                ],
            )
        )
    if clean(row.get("origin")):
        strategies.append(
            (
                "origin_product_exact",
                [
                    ("company_id", "=", company_id),
                    ("origin", "=", clean(row["origin"])),
                    ("product_id", "=", product.id),
                ],
            )
        )

    for method, domain in strategies:
        candidates = move_model.search(domain)
        narrowed = candidates.filtered(lambda move: stock_candidate_is_consistent(row, move))
        if len(narrowed) == 1:
            return narrowed, method, len(candidates)

    return move_model.browse(), f"{product_method}_unmatched", 0


def account_write_vals(row, match_method):
    vals = {
        field_name: clean(row.get(csv_field)) or False
        for csv_field, field_name in ACCOUNT_FIELD_MAP.items()
    }
    vals.update(
        {
            "bp_legacy_source_dump": LEGACY_ETR_CONFIG["source_dump_name"],
            "bp_legacy_source_record_id": int(row["move_id"]),
            "bp_legacy_archive_match_method": match_method,
            "bp_legacy_archive_imported_at": fields.Datetime.now(),
            "bp_legacy_archive_imported_by": env.user.id,
            "bp_legacy_archive_note": "Imported from extracted legacy ETR CSV.",
        }
    )
    return vals


def stock_write_vals(row, match_method):
    vals = {
        field_name: clean(row.get(csv_field)) or False
        for csv_field, field_name in STOCK_FIELD_MAP.items()
    }
    vals.update(
        {
            "bp_legacy_source_dump": LEGACY_ETR_CONFIG["source_dump_name"],
            "bp_legacy_source_record_id": int(row["stock_move_id"]),
            "bp_legacy_archive_match_method": match_method,
            "bp_legacy_archive_imported_at": fields.Datetime.now(),
            "bp_legacy_archive_imported_by": env.user.id,
            "bp_legacy_archive_note": "Imported from extracted legacy stock ETR CSV.",
        }
    )
    return vals


def write_report(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        rows = [{"status": "no_rows"}]
    headers = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def process_account_rows():
    rows = read_rows(LEGACY_ETR_CONFIG["account_csv"])
    report_rows = []
    applied = 0

    for row in rows:
        company_id, company_method = resolve_company_id(row)
        if not company_id:
            report_rows.append(
                {
                    "model": "account.move",
                    "source_id": row.get("move_id"),
                    "move_name": row.get("move_name"),
                    "match_method": company_method,
                    "status": "unresolved_company",
                }
            )
            continue

        move, match_method, candidate_count = find_account_move(row, company_id)
        status = "unmatched"
        target_id = False
        target_name = False
        action = "dry_run"

        if move:
            target_id = move.id
            target_name = move.display_name
            status = "matched"
            if LEGACY_ETR_CONFIG["apply_account"]:
                can_apply = match_method in SAFE_ACCOUNT_APPLY_METHODS or LEGACY_ETR_CONFIG["allow_fallback_account_apply"]
                if can_apply:
                    move.write(account_write_vals(row, match_method))
                    applied += 1
                    action = "applied"
                else:
                    action = "needs_manual_review"

        report_rows.append(
            {
                "model": "account.move",
                "source_id": row.get("move_id"),
                "company_id_resolution": company_method,
                "company_name": row.get("company_name"),
                "move_name": row.get("move_name"),
                "move_type": row.get("move_type"),
                "target_id": target_id,
                "target_name": target_name,
                "match_method": match_method,
                "candidate_count": candidate_count,
                "status": status,
                "action": action,
            }
        )

    return report_rows, applied, len(rows)


def process_stock_rows():
    rows = read_rows(LEGACY_ETR_CONFIG["stock_csv"])
    report_rows = []
    applied = 0

    for index, row in enumerate(rows, start=1):
        company_id, company_method = resolve_company_id(row)
        if not company_id:
            report_rows.append(
                {
                    "model": "stock.move",
                    "source_id": row.get("stock_move_id"),
                    "reference": row.get("reference"),
                    "match_method": company_method,
                    "status": "unresolved_company",
                }
            )
            continue

        move, match_method, candidate_count = find_stock_move(row, company_id)
        status = "unmatched"
        target_id = False
        target_name = False
        action = "dry_run"

        if move:
            target_id = move.id
            target_name = move.reference or move.display_name
            status = "matched"
            if LEGACY_ETR_CONFIG["apply_stock"]:
                within_apply_limit = index <= LEGACY_ETR_CONFIG["stock_row_limit_for_apply"]
                can_apply = match_method in LEGACY_ETR_CONFIG["allow_stock_apply_methods"] and within_apply_limit
                if can_apply:
                    move.write(stock_write_vals(row, match_method))
                    applied += 1
                    action = "applied"
                else:
                    action = "needs_manual_review"

        report_rows.append(
            {
                "model": "stock.move",
                "source_id": row.get("stock_move_id"),
                "company_id_resolution": company_method,
                "company_name": row.get("company_name"),
                "reference": row.get("reference"),
                "product_name": row.get("product_name"),
                "match_method": match_method,
                "candidate_count": candidate_count,
                "target_id": target_id,
                "target_name": target_name,
                "status": status,
                "action": action,
            }
        )

    return report_rows, applied, len(rows)


def main():
    ensure_fields(
        "account.move",
        list(ACCOUNT_FIELD_MAP.values())
        + [
            "bp_legacy_source_dump",
            "bp_legacy_source_record_id",
            "bp_legacy_archive_match_method",
            "bp_legacy_archive_imported_at",
            "bp_legacy_archive_imported_by",
            "bp_legacy_archive_note",
        ],
    )
    ensure_fields(
        "stock.move",
        list(STOCK_FIELD_MAP.values())
        + [
            "bp_legacy_source_dump",
            "bp_legacy_source_record_id",
            "bp_legacy_archive_match_method",
            "bp_legacy_archive_imported_at",
            "bp_legacy_archive_imported_by",
            "bp_legacy_archive_note",
        ],
    )

    report_dir = Path(LEGACY_ETR_CONFIG["report_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)

    account_report_rows, account_applied, account_total = process_account_rows()
    stock_report_rows, stock_applied, stock_total = process_stock_rows()

    write_report(report_dir / "legacy_etr_account_import_report.csv", account_report_rows)
    write_report(report_dir / "legacy_etr_stock_import_report.csv", stock_report_rows)

    summary = {
        "source_dump_name": LEGACY_ETR_CONFIG["source_dump_name"],
        "report_dir": str(report_dir),
        "account_total_rows": account_total,
        "account_applied_rows": account_applied,
        "account_apply_enabled": LEGACY_ETR_CONFIG["apply_account"],
        "stock_total_rows": stock_total,
        "stock_applied_rows": stock_applied,
        "stock_apply_enabled": LEGACY_ETR_CONFIG["apply_stock"],
        "safe_account_apply_methods": sorted(SAFE_ACCOUNT_APPLY_METHODS),
        "safe_stock_apply_methods": LEGACY_ETR_CONFIG["allow_stock_apply_methods"],
    }

    with (report_dir / "legacy_etr_import_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(json.dumps(summary, indent=2))


main()
