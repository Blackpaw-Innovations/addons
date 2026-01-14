/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

const chartLib = loadJS("/web/static/lib/Chart/Chart.js");

class PayrollDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            error: null,
            filters: {
                period: "all",
                status: "all",
            },
            summary: {
                gross: 0,
                net: 0,
                deductions: 0,
                employer: 0,
                pending: 0,
            },
            earningsBreakdown: [],
            deductionsBreakdown: [],
            deductionsList: [],
            deductionsTop: { label: "", percent: 0 },
            employerBreakdown: [],
            departmentCosts: [],
            paymentReadiness: { bank: 0, mobile: 0, cash: 0, failed: 0 },
            headcount: { expiring: 0, exits: 0, newJoins: 0 },
            compliance: { paye: true, nssf: true, shif: true, pension: true },
            trendLabels: [],
            grossTrend: [],
            netTrend: [],
            earningsList: [],
            earningsTotal: 0,
            warnings: [],
            payRuns: [],
        });

        this.earningsChartRef = useRef("earningsChart");
        this.deductionsChartRef = useRef("deductionsChart");
        this.grossNetTrendRef = useRef("grossNetTrendRef");
        this.employerCostRef = useRef("employerCostRef");

        this.charts = [];

        this.openPayslips = this.openPayslips.bind(this);
        this.onPeriodChange = this.onPeriodChange.bind(this);
        this.onStatusChange = this.onStatusChange.bind(this);
        this.openWarning = this.openWarning.bind(this);
        this.openBatch = this.openBatch.bind(this);
        this.openAllBatches = this.openAllBatches.bind(this);
        this.onGeneratePayslips = this.onGeneratePayslips.bind(this);
        this.onApprovePayroll = this.onApprovePayroll.bind(this);
        this.periodOptions = [
            { value: "this_month", label: "This Month" },
            { value: "last_month", label: "Last Month" },
            { value: "last_3_months", label: "Last 3 Months" },
            { value: "this_year", label: "Year to Date" },
            { value: "all", label: "All Time" },
        ];
        this.statusOptions = [
            { value: "approved", label: "Approved (Paid)" },
            { value: "in_progress", label: "In Progress" },
            { value: "payment_ready", label: "Payment Ready" },
            { value: "pending", label: "Pending (Draft/Verify)" },
            { value: "all", label: "All Statuses" },
        ];

        onWillStart(async () => {
            await chartLib;
            await this.loadData();
        });
        onMounted(() => this.renderCharts());
        onWillUnmount(() => this.destroyCharts());
    }

    async loadData() {
        this.state.loading = true;
        try {
            const today = new Date();
            const { start, end } = this._getPeriodRange(this.state.filters.period, today);
            const statusDomain = this._getStatusDomain(this.state.filters.status);
            const payslipDomain = [
                ...this._buildDateDomain("date_to", start, end),
                ...statusDomain,
            ];

            // Summary totals
            const summaryAgg = await this.orm.readGroup(
                "hr.payslip",
                payslipDomain,
                ["total_gross:sum", "total_net:sum", "total_deduction:sum"],
                []
            );
            const summary = summaryAgg && summaryAgg[0] ? summaryAgg[0] : {};

            const employerAgg = await this.orm.readGroup(
                "hr.payslip.line",
                [
                    ...this._buildDateDomain("slip_id.date_to", start, end),
                    ...this._getStatusDomain(this.state.filters.status, "slip_id.state"),
                    ["category_id.code", "in", ["EMP", "COMP", "EMPCOST"]],
                ],
                ["total:sum"],
                []
            );

            const pending = await this.orm.searchCount("hr.payslip", [
                ...this._buildDateDomain("date_to", start, end),
                ...this._getStatusDomain(this.state.filters.status, "state"),
                ["state", "in", ["draft", "verify"]],
            ]);

            // Earnings breakdown by key codes
            const earningsAgg = await this.orm.readGroup(
                "hr.payslip.line",
                [
                    ...this._buildDateDomain("slip_id.date_to", start, end),
                    ...this._getStatusDomain(this.state.filters.status, "slip_id.state"),
                    ["category_id.code", "in", ["EARN"]],
                ],
                ["total:sum", "code"],
                ["code"]
            );
            const earningsListResult = this._buildEarningsList(earningsAgg);

            // Deductions breakdown
            const deductionsAgg = await this.orm.readGroup(
                "hr.payslip.line",
                [
                    ...this._buildDateDomain("slip_id.date_to", start, end),
                    ...this._getStatusDomain(this.state.filters.status, "slip_id.state"),
                    ["category_id.code", "in", ["STAT_DED", "DED", "RELIEFS"]],
                ],
                ["total:sum", "code", "name"],
                ["code", "name"]
            );
            const deductionsListResult = this._buildDeductionsList(deductionsAgg);

            // Employer cost breakdown - Specific Codes
            const employerCostAgg = await this.orm.readGroup(
                "hr.payslip.line",
                [
                    ...this._buildDateDomain("slip_id.date_to", start, end),
                    ...this._getStatusDomain(this.state.filters.status, "slip_id.state"),
                    ["category_id.code", "in", ["EMP"]],
                ],
                ["total:sum", "code"],
                ["code"]
            );

            // Department costs
            const deptAgg = await this.orm.readGroup(
                "hr.payslip",
                payslipDomain,
                ["total_gross:sum"],
                ["department_id"],
                { orderby: "total_gross:sum desc", limit: 6 }
            );

            // Monthly trend (last 6 months)
            const defaultWindowStart = new Date(today.getFullYear(), today.getMonth() - 5, 1);
            const startWindow = start || defaultWindowStart;
            const endWindow = end || new Date(today.getFullYear(), today.getMonth() + 1, 0);
            const trendAgg = await this.orm.readGroup(
                "hr.payslip",
                [
                    ...this._buildDateDomain("date_to", startWindow, endWindow),
                    ...statusDomain,
                ],
                ["total_gross:sum", "total_net:sum"],
                ["date_to:month"],
                { orderby: "date_to:month" }
            );
            const trendLabels = trendAgg.map((m) => this._formatMonth(m["date_to:month"]));
            const grossTrend = trendAgg.map((m) => m.total_gross || 0);
            const netTrend = trendAgg.map((m) => m.total_net || 0);

            const earningsBreakdown = earningsAgg.map((e) => ({
                label: e.code,
                value: e.total || 0,
            }));
            const deductionsBreakdown = deductionsAgg.map((d) => ({
                label: d.code,
                value: Math.abs(d.total || 0),
            }));
            // Process Employer Breakdown for List View
            const employerMap = {};
            employerCostAgg.forEach(r => {
                employerMap[r.code] = Math.abs(r.total || 0);
            });

            const totalEmployerCost = employerMap["TOTAL_EMP"] || (
                (employerMap["NSSF_EMPR"] || 0) +
                (employerMap["AHL_EMPR"] || 0) +
                (employerMap["NITA_EMPR"] || 0) +
                (employerMap["PENSION_EMPR"] || 0)
            );
            const totalGross = summary.total_gross || 0;

            const employerBreakdown = [
                { label: "Employer NSSF", value: employerMap["NSSF_EMPR"] || 0 },
                { label: "Employer Housing Levy", value: employerMap["AHL_EMPR"] || 0 },
                { label: "Employer NITA", value: employerMap["NITA_EMPR"] || 0 },
                { label: "Employer Pension", value: employerMap["PENSION_EMPR"] || 0 },
                { label: "Total Employer Cost", value: totalEmployerCost, isTotal: true },
                { label: "Total Payroll Cost", value: totalGross + totalEmployerCost, isGrandTotal: true }
            ];
            const departmentCosts = (deptAgg || []).map((d) => ({
                name: (d["department_id"] && d["department_id"][1]) || "Unassigned",
                value: d.total_gross || 0,
            }));
            const departmentCostsDecorated = this._decorateDepartments(departmentCosts);

            this.state.summary = {
                gross: summary.total_gross || 0,
                net: summary.total_net || 0,
                deductions: summary.total_deduction || 0,
                employer: employerAgg && employerAgg[0] ? Math.abs(employerAgg[0].total || 0) : 0,
                pending,
            };
            this.state.earningsBreakdown = earningsBreakdown;
            this.state.deductionsBreakdown = deductionsBreakdown;
            this.state.deductionsList = deductionsListResult.items;
            this.state.deductionsTop = deductionsListResult.top;
            this.state.employerBreakdown = employerBreakdown;
            this.state.departmentCosts = departmentCostsDecorated;
            this.state.trendLabels = trendLabels;
            this.state.grossTrend = grossTrend;
            this.state.netTrend = netTrend;
            this.state.error = null;
            this.state.earningsList = earningsListResult.items;
            this.state.earningsTotal = earningsListResult.total;

            // Extra dashboard data (warnings + batches)
            const dashboardData = await this.orm.call("bp.payroll.dashboard", "get_dashboard_data", []);
            this.state.warnings = dashboardData.warnings || [];
            this.state.payRuns = dashboardData.pay_runs || [];
        } catch (error) {
            this.state.error = error.message || error.toString();
        } finally {
            this.state.loading = false;
            this.renderCharts();
        }
    }

    destroyCharts() {
        this.charts.forEach((c) => c && c.destroy());
        this.charts = [];
    }

    renderCharts() {
        if (this.state.loading || this.state.error || !window.Chart) return;
        this.destroyCharts();

        // Earnings bar
        if (this.earningsChartRef.el) {
            const ctx = this.earningsChartRef.el.getContext("2d");
            this.charts.push(
                new Chart(ctx, {
                    type: "bar",
                    data: {
                        labels: this.state.earningsBreakdown.map((e) => e.label),
                        datasets: [
                            {
                                data: this.state.earningsBreakdown.map((e) => e.value),
                                backgroundColor: "#3b82f6",
                                borderRadius: 6,
                            },
                        ],
                    },
                    options: {
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { display: false } },
                            y: { grid: { color: "rgba(0,0,0,0.05)" } },
                        },
                    },
                })
            );
        }

        // Deductions donut
        if (this.deductionsChartRef.el) {
            const ctx = this.deductionsChartRef.el.getContext("2d");
            this.charts.push(
                new Chart(ctx, {
                    type: "doughnut",
                    data: {
                        labels: this.state.deductionsBreakdown.map((d) => d.label),
                        datasets: [
                            {
                                data: this.state.deductionsBreakdown.map((d) => d.value),
                                backgroundColor: ["#3b82f6", "#f59e0b", "#ef4444", "#10b981", "#a855f7"],
                            },
                        ],
                    },
                    options: {
                        plugins: { legend: { display: false } },
                        cutout: "65%",
                    },
                })
            );
        }

        // Gross vs Net trend
        if (this.grossNetTrendRef.el) {
            const ctx = this.grossNetTrendRef.el.getContext("2d");
            this.charts.push(
                new Chart(ctx, {
                    type: "line",
                    data: {
                        labels: this.state.trendLabels,
                        datasets: [
                            {
                                label: "Gross",
                                data: this.state.grossTrend,
                                borderColor: "#3b82f6",
                                backgroundColor: "rgba(59,130,246,0.08)",
                                fill: true,
                                tension: 0.35,
                                pointRadius: 2,
                            },
                            {
                                label: "Net",
                                data: this.state.netTrend,
                                borderColor: "#10b981",
                                backgroundColor: "rgba(16,185,129,0.1)",
                                fill: true,
                                tension: 0.35,
                                pointRadius: 2,
                            },
                        ],
                    },
                    options: {
                        plugins: { legend: { position: "bottom" } },
                        scales: {
                            x: { grid: { display: false } },
                            y: { grid: { color: "rgba(0,0,0,0.05)" } },
                        },
                    },
                })
            );
        }

        // Employer cost bar - REMOVED
        /*
        if (this.employerCostRef.el) {
            const ctx = this.employerCostRef.el.getContext("2d");
            this.charts.push(
                new Chart(ctx, {
                    type: "bar",
                    data: {
                        labels: this.state.employerBreakdown.map((e) => e.label),
                        datasets: [
                            {
                                data: this.state.employerBreakdown.map((e) => e.value),
                                backgroundColor: "#0ea5e9",
                                borderRadius: 6,
                            },
                        ],
                    },
                    options: {
                        plugins: { legend: { display: false } },
                        indexAxis: "y",
                        scales: { x: { grid: { color: "rgba(0,0,0,0.05)" } }, y: { grid: { display: false } } },
                    },
                })
            );
        }
        */

    }

    formatCurrency(amount) {
        return new Intl.NumberFormat(undefined, {
            style: "currency",
            currency: "KES",
            maximumFractionDigits: 0,
        }).format(amount || 0);
    }

    _iso(date) {
        return date ? date.toISOString().slice(0, 10) : null;
    }

    _buildDateDomain(field, start, end) {
        const domain = [];
        if (start) {
            domain.push([field, ">=", this._iso(start)]);
        }
        if (end) {
            domain.push([field, "<=", this._iso(end)]);
        }
        return domain;
    }

    _getPeriodRange(period, today = new Date()) {
        const year = today.getFullYear();
        const month = today.getMonth();
        switch (period) {
            case "this_month":
                return {
                    start: new Date(year, month, 1),
                    end: new Date(year, month + 1, 0),
                };
            case "last_month":
                return {
                    start: new Date(year, month - 1, 1),
                    end: new Date(year, month, 0),
                };
            case "last_3_months": {
                const start = new Date(year, month - 2, 1);
                const end = new Date(year, month + 1, 0);
                return { start, end };
            }
            case "this_year":
                return {
                    start: new Date(year, 0, 1),
                    end: today,
                };
            case "all":
            default:
                return { start: null, end: null };
        }
    }

    _getStatusDomain(status, fieldName = "state") {
        switch (status) {
            case "pending":
                return [[fieldName, "in", ["draft", "verify"]]];
            case "in_progress":
                return [[fieldName, "in", ["draft", "verify", "approval", "payment_ready"]]];
            case "payment_ready":
                return [[fieldName, "=", "payment_ready"]];
            case "approved":
                return [[fieldName, "in", ["done"]]];
            case "all":
            default:
                return [];
        }
    }

    async onPeriodChange(value) {
        this.state.filters.period = value;
        await this.loadData();
    }

    async onStatusChange(value) {
        this.state.filters.status = value;
        await this.loadData();
    }

    onGeneratePayslips() {
        const { start, end } = this._getPeriodRange(this.state.filters.period);
        const context = {};
        if (start) context.default_date_start = this._iso(start);
        if (end) context.default_date_end = this._iso(end);

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.payslip.run",
            views: [[false, "form"]],
            target: "current",
            name: "New Payroll Batch",
            context: context,
        });
    }

    onApprovePayroll() {
        const { start, end } = this._getPeriodRange(this.state.filters.period);
        const domain = [
            ...this._buildDateDomain("date_to", start, end),
            ["state", "in", ["draft", "verify"]],
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Approve Payslips",
            res_model: "hr.payslip",
            domain: domain,
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
        });
    }

    openWarning(warning) {
        if (!warning || !warning.action_model) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: warning.label,
            res_model: warning.action_model,
            views: [[false, "list"], [false, "form"]],
            domain: warning.action_domain || [],
            view_mode: "list,form",
        });
    }

    openBatch(runId) {
        if (!runId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.payslip.run",
            res_id: runId,
            views: [[false, "form"]],
            view_mode: "form",
        });
    }

    openAllBatches() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Payroll Batches",
            res_model: "hr.payslip.run",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
        });
    }

    _buildEarningsList(earningsAgg) {
        const palette = ["#24b9c7", "#6c5dd3", "#f6ad55", "#4ade80", "#60a5fa", "#f97316"];
        const buckets = {
            "Basic Salary": 0,
            Allowances: 0,
            Overtime: 0,
            Bonus: 0,
            "Other Earnings": 0,
        };
        const labelForCode = (code = "") => {
            const c = code.toUpperCase();
            if (c === "GROSS" || c.startsWith("SEC_")) return "IGNORE"; // Ignore Gross and Sections
            if (c.startsWith("BASIC") || c === "BASIC" || c === "BAS") return "Basic Salary";
            if (c.startsWith("ALW") || c.startsWith("ALLOW") || ["HOUSE", "FOOD", "AIRTIME", "EDUCATION", "PENSION_ALLOWANCE", "OTHER_ALLOWANCE"].includes(c)) return "Allowances";
            if (c.startsWith("OT") || c.startsWith("OVERTIME")) return "Overtime";
            if (c.startsWith("BON") || c === "COMM" || c === "COM") return "Bonus";
            return "Other Earnings";
        };
        for (const row of earningsAgg || []) {
            const value = Math.abs(row.total || 0);
            const label = labelForCode(row.code || "");
            if (label === "IGNORE") continue;
            buckets[label] = (buckets[label] || 0) + value;
        }
        const items = [];
        const order = ["Basic Salary", "Allowances", "Overtime", "Bonus", "Other Earnings"];
        let total = 0;
        order.forEach((label, idx) => {
            const value = buckets[label] || 0;
            if (value <= 0) return;
            total += value;
            items.push({
                label,
                value,
                color: palette[idx % palette.length],
            });
        });
        const maxVal = Math.max(...items.map((i) => i.value), 0);
        items.forEach((i) => {
            i.percent = maxVal ? Math.round((i.value / maxVal) * 100) : 0;
        });
        return { items, total };
    }

    _buildDeductionsList(deductionsAgg) {
        const buckets = {
            PAYE: 0,
            NSSF: 0,
            "SHIF / NHIF": 0,
            "Housing Levy": 0,
            Pension: 0,
            "Loans / Advances": 0,
            Other: 0,
        };
        const mapToLabel = (code = "", name = "") => {
            const c = code.toUpperCase();
            const n = (name || "").toUpperCase();
            if (c.startsWith("SEC_") || c === "TOTAL_DED" || c === "NET") return "IGNORE"; // Ignore Sections and Totals
            if (c.includes("PAYE") || n.includes("PAYE") || c.includes("TAX")) return "PAYE";
            if (c.includes("NSSF")) return "NSSF";
            if (c.includes("NHIF") || c.includes("SHIF") || n.includes("NHIF") || n.includes("SHIF")) return "SHIF / NHIF";
            if (c.includes("AHL") || c.includes("HOUSING LEVY")) return "Housing Levy";
            if (c.includes("PENS") || n.includes("PENSION")) return "Pension";
            if (c.includes("LOAN") || c.includes("ADV") || n.includes("LOAN") || n.includes("ADVANCE")) return "Loans / Advances";
            return "Other";
        };
        for (const row of deductionsAgg || []) {
            const value = Math.abs(row.total || 0);
            if (!value) continue;
            const label = mapToLabel(row.code || "", row.name || "");
            if (label === "IGNORE") continue;
            buckets[label] = (buckets[label] || 0) + value;
        }
        const order = ["PAYE", "NSSF", "SHIF / NHIF", "Housing Levy", "Pension", "Loans / Advances", "Other"];
        const palette = ["#1f9bbf", "#7bc2c6", "#f5aa42", "#ef4444", "#5594b6", "#e6d6a8", "#71aeb0"];
        const items = [];
        let total = 0;
        order.forEach((label, idx) => {
            const value = buckets[label] || 0;
            if (!value) return;
            total += value;
            items.push({
                label,
                value,
                color: palette[idx % palette.length],
            });
        });
        const top = items[0]
            ? { label: items[0].label, percent: total ? Math.round((items[0].value / total) * 100) : 0 }
            : { label: "", percent: 0 };
        return { items, top };
    }

    _decorateDepartments(departmentCosts) {
        const palette = ["#24b9c7", "#7bc2c6", "#6c5dd3", "#a5b4fc", "#60a5fa", "#4ade80"];
        const maxVal = Math.max(...departmentCosts.map((d) => d.value), 0);
        return departmentCosts.map((d, idx) => ({
            ...d,
            color: palette[idx % palette.length],
            percent: maxVal ? Math.round((d.value / maxVal) * 100) : 0,
        }));
    }

    _currentSlipDomain() {
        const { start, end } = this._getPeriodRange(this.state.filters.period);
        return [
            ...this._buildDateDomain("date_to", start, end),
            ...this._getStatusDomain(this.state.filters.status),
        ];
    }

    _formatMonth(monthString) {
        if (!monthString) return "";
        const parts = monthString.split("-");
        const date = new Date(Number(parts[0]), Number(parts[1]) - 1, 1);
        return date.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
    }

    openPayslips(domain, name) {
        const baseDomain = this._currentSlipDomain();
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name || "Payslips",
            res_model: "hr.payslip",
            domain: [...baseDomain, ...(domain || [])],
            views: [
                [false, "list"],
                [false, "form"],
            ],
            view_mode: "list,form",
        });
    }
}

PayrollDashboard.template = "BP_Payroll_solution.PayrollDashboard";
registry.category("actions").add("bp_payroll_dashboard", PayrollDashboard);
