#!/bin/bash

echo "=========================================="
echo "BP Optical Solution Deployment Script"
echo "=========================================="

# Step 1: Copy all files to Odoo addons directory
echo ""
echo "Step 1: Copying BP_Optical_solution to /opt/odoo/addons..."
sudo cp -r /home/blackpaw/blackpaw_addons/BP_Optical_solution /opt/odoo/addons/
if [ $? -eq 0 ]; then
    echo "✓ Files copied successfully"
else
    echo "✗ Failed to copy files"
    exit 1
fi

# Clean up __pycache__ directories in the destination
echo ""
echo "Cleaning up __pycache__ directories in /opt/odoo/addons/BP_Optical_solution..."
sudo find /opt/odoo/addons/BP_Optical_solution -type d -name "__pycache__" -exec rm -r {} +
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
echo "Step 3: Upgrading BP_Optical_solution module..."
sudo -u odoo /opt/odoo/odoo-bin -c /etc/odoo.conf -d SeawellTest -u BP_Optical_solution --stop-after-init
if [ $? -eq 0 ]; then
    echo "✓ Module upgrade completed"
else
    echo "✗ Module upgrade failed"
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
