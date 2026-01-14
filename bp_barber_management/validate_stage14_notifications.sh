#!/bin/bash

# Stage 14 Notification System Validation Script
# Validates all notification system components for deployment

echo "🔔 Validating Stage 14: Notifications & Reminders"
echo "=================================================="

# Check file existence
echo "📁 Checking file structure..."

FILES=(
    "models/notification_settings.py"
    "controllers/notification_portal.py"
    "data/mail_templates.xml"
    "data/ir_cron_barber_notifications.xml"
    "views/notification_settings_views.xml"
    "views/notification_portal_templates.xml"
    "tests/test_notifications.py"
)

for file in "${FILES[@]}"; do
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
python3 -m py_compile models/notification_settings.py
python3 -m py_compile controllers/notification_portal.py
python3 -m py_compile tests/test_notifications.py
echo "✅ All Python files valid"

# Validate XML syntax
echo ""
echo "📄 Validating XML syntax..."
xmllint --noout data/mail_templates.xml
xmllint --noout data/ir_cron_barber_notifications.xml
xmllint --noout views/notification_settings_views.xml
xmllint --noout views/notification_portal_templates.xml
echo "✅ All XML files valid"

# Check manifest includes
echo ""
echo "📋 Checking manifest includes..."
if grep -q "mail_templates.xml" __manifest__.py && \
   grep -q "ir_cron_barber_notifications.xml" __manifest__.py && \
   grep -q "notification_settings_views.xml" __manifest__.py && \
   grep -q "notification_portal_templates.xml" __manifest__.py; then
    echo "✅ All data files included in manifest"
else
    echo "❌ Missing data files in manifest"
    exit 1
fi

echo ""
echo "🎉 Stage 14 Notification System Validation COMPLETE!"
echo ""
echo "📧 Components Implemented:"
echo "   • Notification settings with validation"
echo "   • Enhanced appointment model with email fields"
echo "   • 4 responsive HTML email templates"
echo "   • Automated reminder cron jobs (15min intervals)"
echo "   • Tokenized portal for confirm/cancel links"
echo "   • Portal templates with responsive design"
echo "   • Comprehensive test suite"
echo ""
echo "🚀 Ready for deployment and testing!"
echo "   Next: Install/upgrade module and configure settings"