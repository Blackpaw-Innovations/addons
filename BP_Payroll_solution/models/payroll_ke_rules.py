import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _bp_ke_get_config(self):
        """Return active Kenya config for this payslip company, or fallback defaults."""
        self.ensure_one()
        config = self._get_ke_config()
        if config:
            return config
        _logger.warning(
            "Kenya payroll config missing for company %s; using fallback defaults.",
            self.company_id.display_name if self.company_id else "n/a",
        )
        defaults = self.env["bp.payroll.ke.config"].new({})
        defaults.company_id = self.company_id or self.env.company
        return defaults

    def _bp_ke_compute_paye(self, taxable_income, config, insurance_premium=0.0):
        gross_paye = self._bp_ke_compute_gross_paye(taxable_income, config)
        
        # Reliefs
        personal_relief = config.personal_relief or 0.0
        insurance_relief = 0.0
        if insurance_premium > 0:
            # Cap removed to match user requirement for full 15% relief
            insurance_relief = insurance_premium * 0.15
            
        total_relief = personal_relief + insurance_relief + (config.paye_additional_relief or 0.0)
        return max(gross_paye - total_relief, 0.0)

    def _bp_ke_compute_paye_band(self, taxable_income, config, band_index):
        """Compute tax for a specific band (1-5)."""
        if taxable_income <= 0:
            return 0.0
            
        bands = [
            (config.paye_band_1_limit, config.paye_band_1_rate),
            (config.paye_band_2_limit, config.paye_band_2_rate),
            (config.paye_band_3_limit, config.paye_band_3_rate),
            (config.paye_band_4_limit, config.paye_band_4_rate),
        ]
        
        previous_limit = 0.0
        
        for i, (limit, rate) in enumerate(bands):
            current_band_index = i + 1
            if current_band_index == band_index:
                amount_in_band = max(0.0, min(taxable_income, limit) - previous_limit)
                return amount_in_band * (rate / 100.0)
            previous_limit = limit
            
        if band_index == 5:
            amount_in_band = max(0.0, taxable_income - previous_limit)
            return amount_in_band * (config.paye_band_5_rate / 100.0)
            
        return 0.0

    def _bp_ke_compute_gross_paye(self, taxable_income, config):
        if taxable_income <= 0:
            return 0.0
        bands = [
            (config.paye_band_1_limit, config.paye_band_1_rate),
            (config.paye_band_2_limit, config.paye_band_2_rate),
            (config.paye_band_3_limit, config.paye_band_3_rate),
            (config.paye_band_4_limit, config.paye_band_4_rate),
        ]
        remaining = taxable_income
        tax_total = 0.0
        lower = 0.0
        for upper, rate in bands:
            band_amount = min(remaining, max(upper - lower, 0.0))
            tax_total += band_amount * rate / 100.0
            remaining -= band_amount
            lower = upper
            if remaining <= 0:
                break
        if remaining > 0:
            tax_total += remaining * (config.paye_band_5_rate / 100.0)
        return tax_total

    def _bp_ke_compute_nssf(self, gross, config, employer=False):
        if gross <= 0:
            return 0.0
        pensionable = max(config.nssf_lower_earnings_limit, min(gross, config.nssf_upper_earnings_limit))
        rate = config.nssf_rate_employer if employer else config.nssf_rate_employee
        return pensionable * (rate / 100.0)

    def _bp_ke_compute_shif(self, gross, config):
        if gross <= 0:
            return 0.0
        value = gross * (config.shif_rate / 100.0)
        return max(value, config.shif_min_contribution)

    def _bp_ke_compute_housing_levy(self, base_values, config):
        """Compute housing levy using configured base and rate."""
        if not config or not config.housing_levy_rate:
            return 0.0
        base = 0.0
        if config.housing_levy_base == "basic":
            base = base_values.get("BASIC", 0.0)
        elif config.housing_levy_base == "taxable":
            base = self._bp_ke_get_taxable_income(
                {
                    "GROSS": base_values.get("GROSS", 0.0),
                    "NSSF_T1_EMP": base_values.get("NSSF_T1_EMP", 0.0),
                    "NSSF_T2_EMP": base_values.get("NSSF_T2_EMP", 0.0),
                    "SHIF": base_values.get("SHIF", 0.0),
                    "AHL_EMP": 0.0,
                },
                config,
            )
        else:
            base = base_values.get("GROSS", 0.0)
        return max(base * (config.housing_levy_rate / 100.0), 0.0)

    def _bp_ke_is_applicable(self):
        self.ensure_one()
        country = self.company_id.country_id
        return country and country.code == "KE" or self.payroll_country_code == "KE"

    def _bp_ke_get_taxable_income(self, lines_dict, config):
        gross = lines_dict.get("GROSS", 0.0)
        taxable = gross
        deduct_nssf = getattr(config, "paye_deduct_nssf", False)
        deduct_shif = getattr(config, "paye_deduct_shif", False)
        deduct_ahl = getattr(config, "paye_deduct_housing_levy", False)
        
        try:
            with open('/tmp/debug_payroll.txt', 'a') as f:
                f.write(f"DEBUG: Taxable Income Calc - Gross: {gross}\n")
                f.write(f"DEBUG: Config - NSSF: {deduct_nssf}, SHIF: {deduct_shif}, AHL: {deduct_ahl}\n")
                f.write(f"DEBUG: Lines - NSSF T1: {lines_dict.get('NSSF_T1_EMP')}, NSSF T2: {lines_dict.get('NSSF_T2_EMP')}, SHIF: {lines_dict.get('SHIF')}, AHL: {lines_dict.get('AHL_EMP')}\n")
        except Exception:
            pass
        
        if deduct_nssf:
            taxable -= lines_dict.get("NSSF_T1_EMP", 0.0)
            taxable -= lines_dict.get("NSSF_T2_EMP", 0.0)
        if deduct_shif:
            taxable -= lines_dict.get("SHIF", 0.0)
        if deduct_ahl:
            taxable -= lines_dict.get("AHL_EMP", 0.0)
            
        # Allowable Deductions (Pension & Mortgage)
        # Pension: Approved pension fund contributions, up to a limit of KSh 30,000 per month.
        pension = lines_dict.get("PENSION", 0.0)
        if pension > 0:
            taxable -= min(pension, 30000.0)
            
        # Mortgage: Mortgage interest for owner-occupied residential premises, up to KSh 30,000 per month.
        mortgage = lines_dict.get("MORTGAGE", 0.0)
        if mortgage > 0:
            taxable -= min(mortgage, 30000.0)
            
        return max(taxable, 0.0)

    def _bp_ke_compute_nssf_tiers(self, gross, config):
        """Return dict with tier1 and tier2 amounts for employee and employer."""
        if gross <= 0:
            return {
                "tier1_emp": 0.0,
                "tier2_emp": 0.0,
                "tier1_empr": 0.0,
                "tier2_empr": 0.0,
            }
        lower = config.nssf_lower_earnings_limit
        upper = config.nssf_upper_earnings_limit
        rate_emp = config.nssf_rate_employee / 100.0
        rate_empr = config.nssf_rate_employer / 100.0

        tier1_base = min(gross, lower)
        tier2_base = 0.0
        if gross > lower:
            tier2_base = min(gross - lower, max(upper - lower, 0.0))

        return {
            "tier1_emp": tier1_base * rate_emp,
            "tier2_emp": tier2_base * rate_emp,
            "tier1_empr": tier1_base * rate_empr,
            "tier2_empr": tier2_base * rate_empr,
        }
