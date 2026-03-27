/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

export class BpFinanceDashboard extends Component {
    static template = "bp_role_dashboards.FinanceDashboard";
    static props = ["action", "actionStack?"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ data: null, isLoading: false });
        onMounted(() => this.load());
    }

    async load() {
        this.state.isLoading = true;
        try {
            const data = await this.orm.call("bp.finance.dashboard", "get_dashboard_data", [], {});
            this.state.data = data;
        } catch (e) {
            this.notification.add("Could not load Finance Dashboard.", { type: "danger" });
        } finally {
            this.state.isLoading = false;
        }
    }

    fmt(val) {
        if (!val && val !== 0) return "—";
        return new Intl.NumberFormat("en-KE", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(val);
    }

    get now() { return new Date().toLocaleString("en-KE", { dateStyle: "medium", timeStyle: "short" }); }

    maxVal(rows, key) {
        return Math.max(...rows.map(r => r[key] || 0), 1);
    }
}

registry.category("actions").add("bp_dash_finance", BpFinanceDashboard);
