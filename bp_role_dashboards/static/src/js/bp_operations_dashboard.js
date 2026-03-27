/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

export class BpOperationsDashboard extends Component {
    static template = "bp_role_dashboards.OperationsDashboard";
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
            const data = await this.orm.call("bp.operations.dashboard", "get_dashboard_data", [], {});
            this.state.data = data;
        } catch (e) {
            this.notification.add("Could not load Operations Dashboard.", { type: "danger" });
        } finally {
            this.state.isLoading = false;
        }
    }

    fmt(val) {
        if (!val && val !== 0) return "—";
        return new Intl.NumberFormat("en-KE", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(val);
    }

    get now() { return new Date().toLocaleString("en-KE", { dateStyle: "medium", timeStyle: "short" }); }
}

registry.category("actions").add("bp_dash_operations", BpOperationsDashboard);
