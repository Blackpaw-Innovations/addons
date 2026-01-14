# Service Kanban View - UI/UX Documentation

## Overview
Enhanced the Service model with a comprehensive Kanban view following modern UI/UX principles including consistent spacing, typography hierarchy, and visual balance.

## Typography Hierarchy

### 1. Heading Level (Service Name)
- **Font Size**: 16px
- **Font Weight**: 600 (Semi-bold)
- **Line Height**: 1.4
- **Color**: #2F3349 (Dark blue-grey)
- **Usage**: Service title for maximum visibility

### 2. Subtitle Level (Service Code)
- **Font Size**: 13px
- **Font Weight**: 500 (Medium)
- **Color**: #6C757D (Medium grey)
- **Transform**: Uppercase with letter-spacing: 0.5px
- **Usage**: Service code identification

### 3. Body Text Level (Service Details)
- **Font Size**: 14px
- **Font Weight**: 400 (Regular)
- **Line Height**: 1.5
- **Color**: #495057 (Dark grey)
- **Usage**: General information and descriptions

## Spacing and Layout Standards

### Card Structure
- **Card Margin**: 8px between cards
- **Card Padding**: 
  - Header: 16px top/bottom, 20px left/right
  - Content: 0px top, 20px left/right, 16px bottom
  - Footer: 12px top, inherited left/right
- **Border Radius**: 8px for modern appearance
- **Box Shadow**: Subtle elevation with hover effects

### Icon Consistency
- **Icon Size**: 14px standard
- **Icon Width**: 16px fixed for alignment
- **Icon Margin**: 8px right spacing from text
- **Icon Colors**: 
  - Duration: #6C757D (Grey)
  - Price: #28A745 (Green)
  - Info: #17A2B8 (Blue)
  - POS Ready: #28A745 (Green)
  - Warning: #FFC107 (Amber)

### Row Spacing
- **Standard Row Margin**: 12px bottom
- **Content Sections**: Separated with consistent spacing
- **Footer Border**: 1px solid #E9ECEF with 12px top padding

## Interactive Elements

### Hover Effects
- **Border Color**: Changes to #007BFF (Primary blue)
- **Box Shadow**: Enhanced to 0 4px 8px rgba(0,0,0,0.15)
- **Transform**: Subtle translateY(-1px) lift effect
- **Transition**: Smooth 0.3s ease for all properties

### Status Badges
- **Font Size**: 11px
- **Font Weight**: 500 (Medium)
- **Padding**: 4px horizontal, 8px vertical
- **Border Radius**: 12px for pill appearance
- **Text Transform**: Uppercase with letter-spacing
- **Colors**:
  - Active: #28A745 background, white text
  - Archived: #6C757D background, white text

## Accessibility Features

### Focus States
- **Outline**: 2px solid #007BFF
- **Outline Offset**: 2px for clear visibility
- **Applied to**: All interactive elements

### Color Contrast
- All text combinations meet WCAG 2.1 AA standards
- Minimum contrast ratio of 4.5:1 for normal text
- Enhanced contrast for interactive elements

### Icon Tooltips
- **Positioning**: Absolute with proper z-index
- **Background**: #333 with white text
- **Padding**: 4px 8px
- **Border Radius**: 4px
- **Font Size**: 12px for readability

## Responsive Design

### Mobile Breakpoint (<768px)
- **Card Margin**: Reduced to 4px
- **Padding**: Adjusted to 16px left/right
- **Title Font Size**: Reduced to 15px
- **Maintains readability and touch targets**

## Status Indicators

### POS Integration Status
- **POS Ready**: Green shopping cart icon with "POS Ready" text
- **Setup Required**: Amber warning triangle with "Setup Required" text
- **Font Size**: 12px for secondary information
- **Consistent positioning in footer**

### Service Status
- **Active Services**: Green "Active" badge
- **Archived Services**: Grey "Archived" badge
- **Clear visual distinction for service availability**

## Implementation Benefits

1. **Consistent Visual Language**: Standardized spacing, colors, and typography
2. **Improved Scannability**: Clear hierarchy and icon usage
3. **Enhanced User Experience**: Hover effects and smooth transitions
4. **Accessibility Compliance**: Proper contrast ratios and focus states
5. **Responsive Layout**: Adapts to different screen sizes
6. **Information Density**: Optimal balance between detail and clarity

## CSS Architecture

- **Modular Approach**: Separate SCSS file for service-specific styles
- **BEM-inspired Naming**: Consistent class naming convention
- **Performance Optimized**: Minimal CSS footprint with efficient selectors
- **Maintainable Structure**: Well-organized and commented code