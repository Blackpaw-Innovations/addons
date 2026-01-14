/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

/**
 * Optical Test Popup
 * 
 * Full-featured popup for capturing optical test data with OD/OS fields.
 * Collects sphere, cylinder, axis, prism, add, VA, and PD for both eyes,
 * plus notes and optional validity date.
 */
export class OpticalTestPopup extends AbstractAwaitablePopup {
    static template = "BP_Optical_solution.OpticalTestPopup";
    static defaultProps = {
        title: _t("Optical Test"),
        customer: null,
    };

    setup() {
        super.setup();
        this.popup = useService("popup");
        this.orm = useService("orm");

        // Calculate age from date of birth
        const calculatedAge = this.calculateAge(this.props.customer?.date_of_birth);
        
        // Get patient branch or fallback to POS config branch
        const branchId = this.props.customer?.patient_branch_id?.[0] || 
                        this.env.services.pos.config.optical_branch_id?.[0] || 
                        false;

        // Initialize state with all form fields
        this.state = useState({
            // Patient Info
            phone_number: this.props.customer?.phone || this.props.customer?.mobile || "",
            age: calculatedAge || "",
            branch_id: branchId,
            optician_id: false,

            // Right Eye (OD) fields
            sphere_od: "",
            cylinder_od: "",
            axis_od: "",
            prism_od: "",
            add_od: "",
            va_od: "",
            pd_od: "",
            height_od: "",

            // Left Eye (OS) fields
            sphere_os: "",
            cylinder_os: "",
            axis_os: "",
            prism_os: "",
            add_os: "",
            va_os: "",
            pd_os: "",
            height_os: "",

            // Previous RX - Right Eye (OD)
            prev_sphere_od: "",
            prev_cylinder_od: "",
            prev_axis_od: "",
            prev_prism_od: "",
            prev_add_od: "",
            prev_va_od: "",
            prev_pd_od: "",
            prev_height_od: "",

            // Previous RX - Left Eye (OS)
            prev_sphere_os: "",
            prev_cylinder_os: "",
            prev_axis_os: "",
            prev_prism_os: "",
            prev_add_os: "",
            prev_va_os: "",
            prev_pd_os: "",
            prev_height_os: "",

            // Lens & Frame
            needs_new_lens: false,
            needs_new_frame: false,
            lens_type_id: false,
            coating_id: false,
            index_id: false,
            material_id: false,
            frame_id: false,

            // Symptoms
            symptom_ids: [],

            // Other
            workshop_order_number: "",
            follow_up_required: false,
            follow_up_date: "",
            notes: "",
            valid_until: "",

            // Active Tab
            activeTab: "current",
        });

        // Load dropdown options
        this.lensTypes = [];
        this.coatings = [];
        this.indexes = [];
        this.materials = [];
        this.frames = [];
        this.branches = [];
        this.opticians = [];
        this.symptoms = [];

        this.loadOptions();
    }

    async loadOptions() {
        try {
            // Load lens types
            this.lensTypes = await this.orm.searchRead(
                "optical.lens.type",
                [],
                ["id", "name"],
                { order: "name" }
            );

            // Load coatings
            this.coatings = await this.orm.searchRead(
                "optical.coating",
                [],
                ["id", "name"],
                { order: "name" }
            );

            // Load indexes
            this.indexes = await this.orm.searchRead(
                "optical.index",
                [],
                ["id", "name"],
                { order: "name" }
            );

            // Load materials
            this.materials = await this.orm.searchRead(
                "optical.material",
                [],
                ["id", "name"],
                { order: "name" }
            );

            // Load frames (products with Frame category)
            this.frames = await this.orm.searchRead(
                "product.product",
                [["categ_id.name", "=", "Frame"]],
                ["id", "name"],
                { order: "name", limit: 100 }
            );

            // Load branches
            this.branches = await this.orm.searchRead(
                "optical.branch",
                [["active", "=", true]],
                ["id", "name"],
                { order: "name" }
            );

            // Load opticians
            this.opticians = await this.orm.searchRead(
                "optical.optician",
                [["active", "=", true]],
                ["id", "name"],
                { order: "name" }
            );

            // Load symptoms
            this.symptoms = await this.orm.searchRead(
                "optical.symptom",
                [["active", "=", true]],
                ["id", "name"],
                { order: "name" }
            );
        } catch (error) {
            console.error("Error loading options:", error);
        }
    }

    /**
     * Validate and collect form data
     */
    getPayload() {
        const payload = {
            // Patient Info
            phone_number: this.state.phone_number?.trim() || "",
            age: this._parseInt(this.state.age),
            branch_id: this.state.branch_id || false,
            optician_id: this.state.optician_id || false,

            // Right Eye (OD)
            sphere_od: this._parseFloat(this.state.sphere_od),
            cylinder_od: this._parseFloat(this.state.cylinder_od),
            axis_od: this._parseInt(this.state.axis_od),
            prism_od: this._parseFloat(this.state.prism_od),
            add_od: this._parseFloat(this.state.add_od),
            va_od: this.state.va_od?.trim() || "",
            pd_od: this._parseFloat(this.state.pd_od),
            height_od: this._parseFloat(this.state.height_od),

            // Left Eye (OS)
            sphere_os: this._parseFloat(this.state.sphere_os),
            cylinder_os: this._parseFloat(this.state.cylinder_os),
            axis_os: this._parseInt(this.state.axis_os),
            prism_os: this._parseFloat(this.state.prism_os),
            add_os: this._parseFloat(this.state.add_os),
            va_os: this.state.va_os?.trim() || "",
            pd_os: this._parseFloat(this.state.pd_os),
            height_os: this._parseFloat(this.state.height_os),

            // Previous RX - Right Eye (OD)
            prev_sphere_od: this._parseFloat(this.state.prev_sphere_od),
            prev_cylinder_od: this._parseFloat(this.state.prev_cylinder_od),
            prev_axis_od: this._parseInt(this.state.prev_axis_od),
            prev_prism_od: this._parseFloat(this.state.prev_prism_od),
            prev_add_od: this._parseFloat(this.state.prev_add_od),
            prev_va_od: this.state.prev_va_od?.trim() || "",
            prev_pd_od: this._parseFloat(this.state.prev_pd_od),
            prev_height_od: this._parseFloat(this.state.prev_height_od),

            // Previous RX - Left Eye (OS)
            prev_sphere_os: this._parseFloat(this.state.prev_sphere_os),
            prev_cylinder_os: this._parseFloat(this.state.prev_cylinder_os),
            prev_axis_os: this._parseInt(this.state.prev_axis_os),
            prev_prism_os: this._parseFloat(this.state.prev_prism_os),
            prev_add_os: this._parseFloat(this.state.prev_add_os),
            prev_va_os: this.state.prev_va_os?.trim() || "",
            prev_pd_os: this._parseFloat(this.state.prev_pd_os),
            prev_height_os: this._parseFloat(this.state.prev_height_os),

            // Lens & Frame
            needs_new_lens: this.state.needs_new_lens || false,
            needs_new_frame: this.state.needs_new_frame || false,
            lens_type_id: this.state.lens_type_id || false,
            coating_id: this.state.coating_id || false,
            index_id: this.state.index_id || false,
            material_id: this.state.material_id || false,
            frame_id: this.state.frame_id || false,

            // Symptoms
            symptom_ids: this.state.symptom_ids || [],

            // Other
            workshop_order_number: this.state.workshop_order_number?.trim() || "",
            follow_up_required: this.state.follow_up_required || false,
            follow_up_date: this.state.follow_up_date || false,
            notes: this.state.notes?.trim() || "",
            valid_until: this.state.valid_until || false,
        };

        return payload;
    }

    /**
     * Parse float value, return false if empty/invalid
     */
    _parseFloat(value) {
        if (value === "" || value === null || value === undefined) {
            return false;
        }
        const parsed = parseFloat(value);
        return isNaN(parsed) ? false : parsed;
    }

    /**
     * Parse integer value, return false if empty/invalid
     */
    _parseInt(value) {
        if (value === "" || value === null || value === undefined) {
            return false;
        }
        const parsed = parseInt(value, 10);
        return isNaN(parsed) ? false : parsed;
    }

    /**
     * Switch between tabs
     */
    setActiveTab(tabName) {
        this.state.activeTab = tabName;
    }

    /**
     * Toggle symptom selection
     */
    toggleSymptom(symptomId) {
        const index = this.state.symptom_ids.indexOf(symptomId);
        if (index > -1) {
            this.state.symptom_ids.splice(index, 1);
        } else {
            this.state.symptom_ids.push(symptomId);
        }
    }

    /**
     * Check if symptom is selected
     */
    isSymptomSelected(symptomId) {
        return this.state.symptom_ids.includes(symptomId);
    }

    /**
     * Calculate total PD for current RX
     */
    get currentPdTotal() {
        const od = parseFloat(this.state.pd_od) || 0;
        const os = parseFloat(this.state.pd_os) || 0;
        return (od + os).toFixed(1);
    }

    /**
     * Calculate total PD for previous RX
     */
    get previousPdTotal() {
        const od = parseFloat(this.state.prev_pd_od) || 0;
        const os = parseFloat(this.state.prev_pd_os) || 0;
        return (od + os).toFixed(1);
    }

    /**
     * Check if lens info section should be shown
     */
    get showLensInfo() {
        return this.state.needs_new_lens;
    }

    /**
     * Check if frame info section should be shown
     */
    get showFrameInfo() {
        return this.state.needs_new_frame;
    }

    /**
     * Calculate age from date of birth
     */
    calculateAge(dateOfBirth) {
        if (!dateOfBirth) return null;
        
        try {
            const dob = new Date(dateOfBirth);
            const today = new Date();
            let age = today.getFullYear() - dob.getFullYear();
            const monthDiff = today.getMonth() - dob.getMonth();
            
            // Adjust age if birthday hasn't occurred this year
            if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
                age--;
            }
            
            return age >= 0 ? age : null;
        } catch (e) {
            return null;
        }
    }

    /**
     * Validate input - basic validation
     * For optical tests, we allow all fields to be optional since
     * different test scenarios may only require certain measurements
     */
    validate() {
        // Check if at least one measurement field is filled
        const hasODData = this.state.sphere_od || this.state.cylinder_od ||
            this.state.axis_od || this.state.va_od;
        const hasOSData = this.state.sphere_os || this.state.cylinder_os ||
            this.state.axis_os || this.state.va_os;

        if (!hasODData && !hasOSData) {
            return {
                valid: false,
                message: _t("Please enter at least one measurement for OD or OS.")
            };
        }

        // Validate axis range if provided
        if (this.state.axis_od && (this.state.axis_od < 0 || this.state.axis_od > 180)) {
            return {
                valid: false,
                message: _t("OD Axis must be between 0 and 180.")
            };
        }

        if (this.state.axis_os && (this.state.axis_os < 0 || this.state.axis_os > 180)) {
            return {
                valid: false,
                message: _t("OS Axis must be between 0 and 180.")
            };
        }

        return { valid: true };
    }

    /**
     * Handle confirm button click
     */
    async confirm() {
        const validation = this.validate();

        if (!validation.valid) {
            await this.popup.add(ErrorPopup, {
                title: _t("Validation Error"),
                body: validation.message,
            });
            return;
        }

        const payload = this.getPayload();
        this.props.close({ confirmed: true, payload });
    }

    /**
     * Handle cancel button click
     */
    cancel() {
        this.props.close({ confirmed: false, payload: null });
    }
}

// Register the popup in the POS popups registry
registry.category("popups").add("OpticalTestPopup", OpticalTestPopup);
