#!/bin/bash

echo "=========================================="
echo "BP LPG Solution Deployment Script"
echo "=========================================="

# Step 1: Copy all files to Odoo addons directory
echo ""
echo "Step 1: Copying BP_LPG_Solution to /opt/odoo/addons..."
sudo rm -rf /opt/odoo/addons/BP_LPG_Solution
sudo cp -r /home/blackpaw/blackpaw_addons/blackpaw_addon/BP_LPG_Solution /opt/odoo/addons/
if [ $? -eq 0 ]; then
    echo "✓ Files copied successfully"
else
    echo "✗ Failed to copy files"
    exit 1
fi

# Clean up __pycache__ directories in the destination
echo ""
echo "Cleaning up __pycache__ directories in /opt/odoo/addons/BP_LPG_Solution..."
sudo find /opt/odoo/addons/BP_LPG_Solution -type d -name "__pycache__" -exec rm -r {} +
if [ $? -eq 0 ]; then
    echo "✓ __pycache__ directories cleaned"
else
    echo "✗ Failed to clean __pycache__ directories"
fi

# Step 2: Restart Odoo service
echo ""
echo "Step 2: Restarting Odoo service..."
sudo systemctl restart odoo
if [ $? -eq 0 ]; then
    echo "✓ Odoo service restarted"
else
    echo "✗ Failed to restart Odoo"
    exit 1
fi

# Step 3: Upgrade module via CLI
echo ""
echo "Step 3: Upgrading BP_LPG_Solution module on BlackPaw..."
sudo -u odoo /opt/odoo/odoo-bin -c /etc/odoo.conf -d BlackPaw -i BP_LPG_Solution --stop-after-init > /tmp/lpg_install.log 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Module upgrade completed"
    tail -n 20 /tmp/lpg_install.log
else
    echo "✗ Module upgrade failed with code $EXIT_CODE"
    tail -n 50 /tmp/lpg_install.log
    exit 1
fi

# Step 4: Check Odoo service status
echo ""
echo "Step 4: Checking Odoo service status..."
sudo systemctl status odoo --no-pager
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
