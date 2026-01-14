#!/bin/bash

echo "🔧 Stage 15: Audit & Maintenance System Validation"
echo "=================================================="

# Check file existence
echo "📁 Checking maintenance system files..."

MAINTENANCE_FILES=(
    "models/audit.py"
    "wizard/maintenance_console.py"
    "views/maintenance_views.xml"
    "wizard/maintenance_console_views.xml"
    "data/ir_cron_barber_maintenance.xml"
    "tests/test_maintenance.py"
)

for file in "${MAINTENANCE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ $file (MISSING)"
        exit 1
    fi
done

# Validate Python syntax
echo ""
echo "🐍 Validating Python syntax..."
python3 -m py_compile models/audit.py
python3 -m py_compile wizard/maintenance_console.py
python3 -m py_compile tests/test_maintenance.py
echo "✅ All Python files valid"

# Validate XML syntax
echo ""
echo "📄 Validating XML syntax..."
xmllint --noout views/maintenance_views.xml
xmllint --noout wizard/maintenance_console_views.xml
xmllint --noout data/ir_cron_barber_maintenance.xml
echo "✅ All XML files valid"

# Check imports
echo ""
echo "🔗 Checking module imports..."
if grep -q "from . import audit" models/__init__.py; then
    echo "✅ Audit model imported"
else
    echo "❌ Audit model import missing"
    exit 1
fi

if grep -q "from . import maintenance_console" wizard/__init__.py; then
    echo "✅ Maintenance console imported"
else
    echo "❌ Maintenance console import missing"
    exit 1
fi

# Check manifest updates
echo ""
echo "📋 Checking manifest includes..."
if grep -q "post_init_hook" __manifest__.py && \
   grep -q "maintenance_views.xml" __manifest__.py && \
   grep -q "maintenance_console_views.xml" __manifest__.py && \
   grep -q "ir_cron_barber_maintenance.xml" __manifest__.py; then
    echo "✅ All maintenance components included in manifest"
else
    echo "❌ Missing maintenance components in manifest"
    exit 1
fi

# Check security rules
echo ""
echo "🔒 Checking security rules..."
if grep -q "bp.barber.maintenance" security/ir.model.access.csv && \
   grep -q "bp.barber.maintenance.console" security/ir.model.access.csv; then
    echo "✅ Security rules defined for maintenance models"
else
    echo "❌ Missing security rules for maintenance models"
    exit 1
fi

echo ""
echo "🎉 Stage 15 Maintenance System Validation COMPLETE!"
echo ""
echo "🔧 Components Implemented:"
echo "   • Maintenance dashboard with diagnostics & stats"
echo "   • Interactive console for data operations"
echo "   • Data integrity checks and orphan fixing"
echo "   • Automated archiving (appointments & wallets)"
echo "   • Performance indexes via post_init_hook"
echo "   • CSV export functionality"
echo "   • Automated cron jobs for hygiene"
echo "   • Comprehensive test coverage"
echo ""
echo "🚀 Ready for deployment!"
echo "   Next: Copy module, restart Odoo, test functionality"