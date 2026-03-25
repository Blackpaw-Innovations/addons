BP Legacy ETR Archive
=====================

This addon provides archive-only fields for legacy Kenya ETR or OSCU values
so they can be matched and stored safely in a community database after an
enterprise-to-community migration.

It does not restore OSCU business logic, does not replace Tremol or any other
current EDI flow, and should not be used as a shortcut to write directly into
live Odoo core tables with SQL.

What It Adds
------------

* Read-only archive fields on ``account.move`` for legacy ``l10n_ke_oscu_*``
  values and related Studio ETR values.
* Read-only archive fields on ``stock.move`` for legacy stock OSCU flags.
* Search filters and form sections for admin users to review archived values.
* A dry-run Odoo shell importer for matching extracted CSV rows to live
  records before any write.

File Structure
--------------

::

    bp_legacy_etr_archive/
    |-- README.md
    |-- __init__.py
    |-- __manifest__.py
    |-- models/
    |   |-- __init__.py
    |   |-- account_move.py
    |   `-- stock_move.py
    |-- tests/
    |   |-- __init__.py
    |   `-- test_legacy_etr_archive.py
    |-- tools/
    |   `-- odoo_shell_import_legacy_etr.py
    `-- views/
        |-- account_move_views.xml
        `-- stock_move_views.xml

Safe Usage
----------

1. Install ``bp_legacy_etr_archive`` in the target database.
2. Confirm the extracted CSV files from the assessment exist and are reachable
   from the Odoo process.
3. Open ``tools/odoo_shell_import_legacy_etr.py`` and adjust
   ``DEFAULT_CONFIG`` if your CSV or report paths differ.
4. Run the script inside ``odoo shell`` and review the generated dry-run
   reports first.
5. Only set ``apply_account`` or ``apply_stock`` to ``True`` after reviewing
   the dry-run output.

Example pattern::

    odoo shell -d <database> -c <odoo.conf> < addons\bp_legacy_etr_archive\tools\odoo_shell_import_legacy_etr.py

If Odoo runs in Docker, use container-visible paths for the CSVs and report
directory. The script is safe by default because it only writes when the
config explicitly enables apply mode.

Matching Rules
--------------

Account moves
~~~~~~~~~~~~~

* Strongest matches use ``move_name``, ``move_type``, and company.
* Secondary matches use ``ref`` or ``payment_reference`` and then cross-check
  date and amount.
* Fallback matches are reported in dry-run output but are not applied unless
  you deliberately allow them.

Stock moves
~~~~~~~~~~~

* Product matching prefers default code, then barcode, then exact product
  name.
* Move matching prefers ``reference`` plus the resolved product.
* Stock application is intentionally stricter because stock rows are easier to
  mismatch after migration.

Manufacturing Note
------------------

The dump assessment recovered historical manufacturing orders and component or
output lines, but the dump did not contain BOMs, BOM lines, workcenters, or
workorders. Treat the manufacturing CSVs as audit or controlled re-entry
data, not as a complete MRP restore source.

Assessment files remain under ``c:\LocalHost\_tmp_rvmservice_dump\assessment``.
