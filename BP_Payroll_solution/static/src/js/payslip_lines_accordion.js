/** @odoo-module **/

/**
 * Lightweight accordion behavior for payslip salary computations:
 * - Click a section row (display_type = line_section) to fold/unfold its child lines.
 * - Shows debit/credit subtotals on the section row.
 * - Applies only to the payslip Salary Computations table (marked with class o_bp_payslip_lines_tree).
 *
 * This is DOM-based and re-applies when the table content changes via a MutationObserver.
 */

const SECTION_CLASS = "o_is_line_section";
const TABLE_SELECTOR = ".o_bp_payslip_lines_tree table.o_list_table";

function computeSectionTotals(sectionRow, childRows) {
    let debit = 0.0;
    let credit = 0.0;
    const parseAmount = (cell) => {
        const txt = (cell && cell.textContent || "").replace(/[, ]/g, "");
        const val = parseFloat(txt);
        return isNaN(val) ? 0.0 : val;
    };
    childRows.forEach((row) => {
        const debitCell = row.querySelector("td[data-name='debit'], td.o_data_cell[name='debit']");
        const creditCell = row.querySelector("td[data-name='credit'], td.o_data_cell[name='credit']");
        debit += parseAmount(debitCell);
        credit += parseAmount(creditCell);
    });
    return { debit, credit };
}

function toggleSection(sectionRow, childRows) {
    const collapsed = sectionRow.classList.toggle("bp-section-collapsed");
    childRows.forEach((row) => {
        row.style.display = collapsed ? "none" : "";
    });
    const icon = sectionRow.querySelector(".bp-toggle-icon");
    if (icon) {
        icon.classList.toggle("fa-caret-down", !collapsed);
        icon.classList.toggle("fa-caret-right", collapsed);
    }
}

function enhanceTable(table) {
    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    // Avoid duplicate enhancement
    if (table.dataset.bpAccordion === "1") return;
    table.dataset.bpAccordion = "1";

    const rows = Array.from(tbody.querySelectorAll("tr.o_data_row"));
    let currentSection = null;
    let buffer = [];

    rows.forEach((row, idx) => {
        const isSection = row.classList.contains(SECTION_CLASS);

        if (isSection) {
            // finalize previous section
            if (currentSection) {
                const totals = computeSectionTotals(currentSection, buffer);
                currentSection.dataset.bpChildren = buffer.map((r) => r.dataset.id || idx).join(",");
                currentSection.dataset.bpDebit = totals.debit.toString();
                currentSection.dataset.bpCredit = totals.credit.toString();
                // attach UI affordances
                const nameCell = currentSection.querySelector("td[data-name='name'], td.o_data_cell[name='name']");
                if (nameCell && !nameCell.querySelector(".bp-toggle-icon")) {
                    const icon = document.createElement("i");
                    icon.className = "fa fa-caret-down bp-toggle-icon me-1";
                    nameCell.prepend(icon);
                }
                const debitCell = currentSection.querySelector("td[data-name='debit'], td.o_data_cell[name='debit']");
                const creditCell = currentSection.querySelector("td[data-name='credit'], td.o_data_cell[name='credit']");
                if (debitCell) debitCell.textContent = totals.debit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                if (creditCell) creditCell.textContent = totals.credit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            }
            // start new section
            currentSection = row;
            buffer = [];
        } else if (currentSection) {
            buffer.push(row);
        }
    });

    // finalize last section
    if (currentSection) {
        const totals = computeSectionTotals(currentSection, buffer);
        currentSection.dataset.bpChildren = buffer.map((r) => r.dataset.id || "").join(",");
        currentSection.dataset.bpDebit = totals.debit.toString();
        currentSection.dataset.bpCredit = totals.credit.toString();
        const nameCell = currentSection.querySelector("td[data-name='name'], td.o_data_cell[name='name']");
        if (nameCell && !nameCell.querySelector(".bp-toggle-icon")) {
            const icon = document.createElement("i");
            icon.className = "fa fa-caret-down bp-toggle-icon me-1";
            nameCell.prepend(icon);
        }
        const debitCell = currentSection.querySelector("td[data-name='debit'], td.o_data_cell[name='debit']");
        const creditCell = currentSection.querySelector("td[data-name='credit'], td.o_data_cell[name='credit']");
        if (debitCell) debitCell.textContent = totals.debit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (creditCell) creditCell.textContent = totals.credit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Click handler to toggle
    tbody.addEventListener("click", (ev) => {
        const row = ev.target.closest("tr.o_data_row");
        if (!row || !row.classList.contains(SECTION_CLASS)) return;
        const childrenIds = (row.dataset.bpChildren || "").split(",").filter(Boolean);
        const childRows = childrenIds
            .map((id) => tbody.querySelector(`tr.o_data_row[data-id='${id}']`))
            .filter(Boolean);
        toggleSection(row, childRows);
    });
}

function initAccordion() {
    document.querySelectorAll(TABLE_SELECTOR).forEach(enhanceTable);
}

function observeDOM() {
    const observer = new MutationObserver(() => initAccordion());
    observer.observe(document.body, { childList: true, subtree: true });
}

// Initialize when the page is ready
if (document.readyState !== "loading") {
    initAccordion();
    observeDOM();
} else {
    document.addEventListener("DOMContentLoaded", () => {
        initAccordion();
        observeDOM();
    });
}
