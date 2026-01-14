# Stock Minimum

A simple Odoo 17 module that adds minimum stock quantity tracking to product templates.

## What it does

This module adds two new fields to product templates:
- **Minimum Quantity**: A configurable threshold value
- **Below Minimum**: A boolean flag indicating when current stock is at or below the minimum

The `below_minimum` flag is automatically maintained to help you identify products that need restocking.

## How it updates

The `below_minimum` flag is updated in three ways:

1. **Instantly**: When you change the Minimum Quantity field, the flag recalculates automatically via computed dependency
2. **Automatically**: Every 10 minutes via a scheduled action that checks all products
3. **Manually**: Use the "Refresh Below Minimum" button on any product form

## Usage

### Setting up minimum quantities

1. Go to **Inventory > Products > Products**
2. Open any product
3. Set the **Minimum Quantity** field in the General Information section
4. The **Below Minimum** flag will update automatically

### Finding products below minimum

Use the search filter:
1. Go to **Inventory > Products > Products**
2. Click the search filters
3. Select **"Below Minimum"** to see only flagged products
4. Products below minimum are also highlighted in red in list views

### Manual refresh

On any product form, click the **"Refresh Below Minimum"** button to manually recalculate the flag. This is useful for immediate updates without waiting for the scheduled action.

## Prerequisites

- Requires `product` and `stock` modules (standard Odoo inventory)
- User needs product management rights to use the refresh button

## Troubleshooting

**Flag not updating automatically?**
- Check that the scheduled action "Recompute Below Minimum" is active
- Go to Settings > Technical > Automation > Scheduled Actions

**Can't see the refresh button?**
- Ensure your user has product manager rights
- Button is only visible to users in the Product Manager group

**Fields not visible?**
- Make sure the module is properly installed and updated
- Check that you're viewing a product (not a variant)

## Compatibility

- **Odoo Version**: 17.0 Community Edition and Enterprise Edition
- **Dependencies**: `product`, `stock`

## Technical Details

The module uses a computed field with `@api.depends('minimum_qty')` for instant updates and a cron job for periodic batch updates. Empty minimum quantities are treated as 0.0.

## Deployment on Odoo.sh

### 1. Upload to Repository
Push the `stock_minimum` folder to your Odoo.sh repository under the addons path:
```
your-project/
├── addons/
│   └── stock_minimum/     # Upload the entire module folder here
└── ...
```

### 2. Install Module
1. On your Odoo.sh instance, go to **Apps**
2. Click **Update Apps List** to refresh available modules
3. Search for **"Stock Minimum"**
4. Click **Install** on the Stock Minimum module

### 3. Test Functionality
1. Navigate to **Inventory → Products → Products**
2. Open any existing product or create a new one
3. Set the **Minimum Quantity** field (e.g., 10)
4. Check that the **Below Minimum** flag updates automatically
5. Verify the flag reflects whether current stock is at or below the minimum

### 4. Verify Scheduled Action
1. Go to **Settings → Technical → Automation → Scheduled Actions**
2. Search for **"Recompute Below Minimum"**
3. Confirm the action is **Active** and set to run every **10 minutes**
4. You can manually trigger it using the **Run Manually** button if needed

### 5. Test Search Filter
1. Return to **Inventory → Products → Products**
2. Click the search/filter area
3. Select the **"Below Minimum"** filter
4. Verify it shows only products where current stock is at or below the minimum quantity
5. Products below minimum should also appear highlighted in red in list views

## Author & License

- **Author**: Blackpaw Innovations
- **Website**: https://blackpawinnovations.com
- **License**: LGPL-3