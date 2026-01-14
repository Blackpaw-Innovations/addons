# Contributing to Barber Management

Thank you for your interest in contributing to the Barber Management module! This document provides guidelines for contributing code, reporting issues, and helping improve the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Message Convention](#commit-message-convention)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and professional in all interactions.

### Our Standards

- **Be Respectful**: Treat everyone with respect and kindness
- **Be Inclusive**: Welcome contributors regardless of experience level
- **Be Constructive**: Provide helpful feedback and suggestions
- **Be Patient**: Help newcomers learn and improve
- **Be Professional**: Maintain high standards in all communications

## Getting Started

### Prerequisites

- **Odoo 17**: Development environment with Odoo 17 installed
- **Python 3.8+**: Compatible Python version
- **PostgreSQL**: Database server for development
- **Git**: Version control system
- **Text Editor**: VS Code, PyCharm, or similar with Python support

### Development Environment Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Blackpaw-Innovations/bp-fuel-solution.git
   cd bp-fuel-solution
   ```

2. **Install Development Dependencies**
   ```bash
   pip install -r requirements-dev.txt  # If available
   pip install pre-commit black isort flake8 pylint-odoo
   ```

3. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

4. **Create Development Database**
   ```bash
   createdb barber_dev
   odoo -d barber_dev -i bp_barber_management --dev=all
   ```

## Development Workflow

### Branch Naming Convention

- **Feature branches**: `feature/description-of-feature`
- **Bug fixes**: `bugfix/issue-number-description`
- **Hotfixes**: `hotfix/critical-issue-description`
- **Documentation**: `docs/update-description`

### Example Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/add-sms-notifications
   ```

2. **Make Changes and Test**
   ```bash
   # Write code, add tests
   make test
   make lint
   ```

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add SMS notification system for appointments"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/add-sms-notifications
   # Create pull request on GitHub
   ```

## Coding Standards

### Python Code Style

We follow PEP 8 with some Odoo-specific conventions:

#### Formatting Tools
- **Black**: Automatic code formatting
- **isort**: Import statement organization
- **flake8**: Style guide enforcement
- **pylint-odoo**: Odoo-specific linting

#### Running Code Formatters
```bash
# Format all code
make format

# Or manually:
black bp_barber_management/
isort bp_barber_management/
```

#### Code Style Guidelines

```python
# Good: Proper class structure
class BarberAppointment(models.Model):
    _name = 'bp.barber.appointment'
    _description = 'Barber Appointment'
    _order = 'start_datetime desc'
    
    # Fields grouped logically
    partner_id = fields.Many2one('res.partner', required=True)
    barber_id = fields.Many2one('bp.barber.barber', required=True)
    
    @api.depends('service_ids')
    def _compute_total_duration(self):
        """Compute total appointment duration from services"""
        for appointment in self:
            appointment.total_duration = sum(
                service.duration_minutes for service in appointment.service_ids
            )
```

#### Naming Conventions

- **Models**: `bp.barber.model_name` (snake_case)
- **Fields**: `snake_case` (e.g., `start_datetime`, `partner_id`)
- **Methods**: `snake_case` (e.g., `action_confirm`, `_compute_total`)
- **Variables**: `snake_case`
- **Constants**: `UPPER_CASE`
- **XML IDs**: `bp_barber_model_action_name` (consistent prefixing)

### XML Code Style

#### View Structure
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <!-- Form View -->
        <record id="bp_barber_appointment_form" model="ir.ui.view">
            <field name="name">bp.barber.appointment.form</field>
            <field name="model">bp.barber.appointment</field>
            <field name="arch" type="xml">
                <form string="Appointment">
                    <sheet>
                        <group>
                            <field name="partner_id"/>
                            <field name="barber_id"/>
                        </group>
                    </sheet>
                </form>
            </field>
        </record>
    </data>
</odoo>
```

#### XML ID Conventions
- **Views**: `{module}_{model}_{view_type}` (e.g., `bp_barber_appointment_form`)
- **Actions**: `action_{module}_{model}` (e.g., `action_bp_barber_appointments`)
- **Menus**: `menu_{module}_{section}` (e.g., `menu_bp_barber_appointments`)

### JavaScript Code Style

```javascript
// Good: ES6 syntax, proper formatting
/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

export class BarberKiosk extends Component {
    setup() {
        this.state = useState({
            appointments: [],
            currentTime: new Date(),
        });
    }
    
    async loadAppointments() {
        const appointments = await this.orm.searchRead(
            "bp.barber.appointment",
            [["state", "=", "confirmed"]],
            ["name", "partner_id", "start_datetime"]
        );
        this.state.appointments = appointments;
    }
}
```

## Testing Guidelines

### Test Structure

Tests should be comprehensive and follow Odoo testing patterns:

```python
from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestBarberAppointments(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test data
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@customer.com'
        })
    
    def test_appointment_confirmation(self):
        """Test appointment confirmation workflow"""
        appointment = self.env['bp.barber.appointment'].create({
            'partner_id': self.partner.id,
            'barber_id': self.barber.id,
        })
        
        appointment.action_confirm()
        
        self.assertEqual(appointment.state, 'confirmed')
        # Test email sent, activity created, etc.
```

### Test Tags

Use appropriate test tags:
- `@tagged('post_install', '-at_install')`: For most business logic tests
- `@tagged('at_install')`: For basic installation tests
- `@tagged('-at_install', '-post_install')`: For tests that should not run during install

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
odoo --test-enable --test-tags=bp_barber_management.test_appointments --stop-after-init

# Run with coverage
coverage run --source=bp_barber_management odoo --test-enable --stop-after-init
coverage report
```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/) for consistent commit messages:

### Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples
```bash
# Feature addition
git commit -m "feat(appointments): add SMS notification system"

# Bug fix
git commit -m "fix(pos): resolve commission calculation error for packages"

# Documentation
git commit -m "docs: update installation guide with PostgreSQL setup"

# Breaking change
git commit -m "feat!: change appointment state workflow

BREAKING CHANGE: appointment states now include 'cancelled' status"
```

## Pull Request Process

### Before Submitting

1. **Ensure Tests Pass**
   ```bash
   make test
   make lint
   ```

2. **Update Documentation**
   - Update README if adding features
   - Add docstrings to new methods
   - Update CHANGELOG.md if needed

3. **Check Code Coverage**
   - Aim for >90% test coverage for new code
   - Add tests for bug fixes

### PR Description Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)  
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Added tests for new functionality
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: Maintainer reviews code quality and design
3. **Testing**: Manual testing of new features
4. **Merge**: Approved PRs are merged to main branch

## Issue Reporting

### Bug Reports

Use the bug report template and include:

- **Environment**: Odoo version, OS, browser
- **Steps to Reproduce**: Clear, numbered steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Screenshots**: If applicable
- **Error Messages**: Full error text and stack traces

### Feature Requests

Include:

- **Use Case**: Why this feature is needed
- **Proposed Solution**: How it should work
- **Alternatives**: Other solutions considered
- **Additional Context**: Screenshots, mockups, etc.

## Development Guidelines

### Database Design

- **Follow Odoo Conventions**: Use standard field types and patterns
- **Proper Relationships**: Use correct Many2one, One2many relationships
- **Constraints**: Add SQL and Python constraints for data integrity
- **Indexes**: Add database indexes for performance-critical queries

### Security Considerations

- **Access Rights**: Define proper ir.model.access rules
- **Record Rules**: Use record rules for multi-company data isolation
- **Input Validation**: Validate all user inputs
- **SQL Injection**: Never use raw SQL with user input

### Performance Guidelines

- **ORM Optimization**: Use `search_read`, batch operations
- **Database Queries**: Minimize queries in loops
- **Caching**: Use `@tools.ormcache` for expensive computations
- **Indexes**: Add indexes for frequently searched fields

## Documentation Standards

### Docstring Format

```python
def complex_calculation(self, param1, param2):
    """
    Perform complex calculation with multiple parameters.
    
    Args:
        param1 (str): Description of first parameter
        param2 (int): Description of second parameter
        
    Returns:
        dict: Dictionary containing calculation results with keys:
            - total (float): Total calculated value
            - breakdown (list): List of calculation steps
            
    Raises:
        ValueError: If param2 is negative
        UserError: If calculation fails validation
    """
```

### README Updates

When adding features, update:
- Feature list in README.md
- Configuration instructions
- Usage examples
- Screenshots (if UI changes)

## Community Guidelines

### Getting Help

- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **Professional Support**: Contact Blackpaw Innovations for paid support

### Contributing Non-Code

- **Documentation**: Improve guides, fix typos, add examples
- **Testing**: Test new releases and report issues
- **Translations**: Help translate the module (future feature)
- **Community Support**: Help other users in discussions

## Recognition

Contributors will be recognized through:
- **CHANGELOG.md**: Credits for significant contributions
- **GitHub Contributors**: Automatic recognition in repository
- **Hall of Fame**: Special recognition for major contributions (coming soon)

---

Thank you for contributing to making barbershop management better for everyone! 💈

**Questions?** Open a GitHub Discussion or contact us at dev@blackpawinnovations.com