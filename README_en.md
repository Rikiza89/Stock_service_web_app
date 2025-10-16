# Stock Management System

A Django-based multi-tenant stock/inventory management system with society (organization) isolation, drawer management, and usage tracking.

## Features

### Core Features
- **Multi-tenant Architecture**: Multiple societies (organizations) with isolated data
- **User Management**: Users can belong to multiple societies with different roles
- **Stock Object Management**: Track inventory items with quantities, minimum thresholds, and locations
- **Stock Movements**: Record stock in/out operations with full audit trail
- **Drawer Management**: Optional physical drawer/cabinet organization system
- **Usage Tracking**: Monitor which users/departments consume stock items
- **Refill Prediction**: AI-powered predictions based on historical usage patterns
- **Refill Scheduler**: Schedule and manage stock replenishment

### Subscription Tiers
- **Free**: Basic inventory management, up to 2 users, 1 admin
- **Basic**: Advanced features, up to 10 users, 2 admins, drawer management
- **Premium**: Unlimited users/admins, all features, priority support

## Architecture

### Models
- **Society**: Organization/tenant entity
- **User**: Django default User model (supports multiple societies)
- **SocietyUser**: Through model linking users to societies with admin status
- **StockObjectKind**: Categories for stock items
- **StockObject**: Individual inventory items
- **Drawer**: Physical storage locations (optional)
- **StockObjectDrawerPlacement**: Links stock to drawers
- **StockMovement**: Audit log of all stock movements
- **ObjectUser**: Departments/machines/people that use stock
- **StockUsage**: Records of stock consumption by object users
- **RefillSchedule**: Planned replenishment orders

### Authentication
Custom authentication backend (`SocietyAuthBackend`) requires:
- Society name
- Username (or email)
- Password

Users can belong to multiple societies with different admin roles per society.

## Installation

### Prerequisites
- Python 3.8+
- Django 4.2+
- PostgreSQL (recommended) or SQLite for development

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd stock-management-system
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure database** (edit `settings.py`)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stock_management',
        'USER': 'your_db_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

5. **Configure authentication backend** (in `settings.py`)
```python
AUTHENTICATION_BACKENDS = [
    'stock_service.backends.SocietyAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]
```

6. **Add context processor** (in `settings.py`)
```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... other context processors
                'stock_service.context_processors.society_context',
            ],
        },
    },
]
```

7. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

8. **Create superuser** (optional)
```bash
python manage.py createsuperuser
```

9. **Run development server**
```bash
python manage.py runserver
```

10. **Access the application**
- Main app: http://localhost:8000/stock/
- Admin: http://localhost:8000/admin/
- Register new society: http://localhost:8000/stock/register/

## Usage

### First Time Setup

1. **Register a Society**
   - Navigate to the registration page
   - Enter society name, slug, and admin credentials
   - System creates society and first admin user

2. **Login**
   - Enter society name, username, and password
   - Admin users can access all management features

3. **Configure Society Settings**
   - Go to Society Settings (admin only)
   - Enable drawer management if needed
   - Upgrade subscription plan as needed

### Managing Stock

1. **Add Stock Object Kinds** (categories)
   - Navigate to "品目種類管理" (Stock Object Kinds)
   - Create categories like "Electronics", "Tools", etc.

2. **Add Stock Objects**
   - Navigate to "在庫品目" (Stock Objects)
   - Add items with quantities, units, and minimum thresholds

3. **Record Stock Movements**
   - Stock In: "在庫入庫" - Add items to inventory
   - Stock Out: "在庫出庫" - Remove items from inventory
   - All movements are logged with timestamp and user

4. **Track Usage**
   - Create Object Users (departments/machines)
   - Record usage via "利用履歴" (Usage Log)
   - System automatically reduces stock quantity

5. **Monitor Refills**
   - View predictions in "補充予測" (Refill Prediction)
   - Schedule refills in "補充スケジューラー" (Refill Scheduler)
   - Complete scheduled refills to update stock

### User Management (Admin Only)

- Add/edit/delete users in your society
- Assign admin roles per society
- Track user activity and stock operations

### Drawer Management (Premium Feature)

- Create cabinets and drawers with X/Y coordinates
- Assign stock items to specific drawers
- Track quantity per drawer location
- View drawer information in stock lists

## API Structure

### Helper Functions

```python
# Get user's primary society
from stock_service.views import get_user_society
society = get_user_society(request.user)

# Check if user is admin for a society
from stock_service.views import is_society_admin
is_admin = is_society_admin(request.user, society)
```

### Template Context

Available in all templates via context processor:
- `user_society`: User's primary society object
- `is_society_admin`: Boolean indicating admin status

## Development

### Project Structure

```
stock_service/
├── models.py           # Database models
├── views.py            # View functions and CBVs
├── forms.py            # Django forms
├── admin.py            # Admin configuration
├── backends.py         # Custom authentication backend
├── context_processors.py  # Template context processor
├── urls.py             # URL routing
├── templates/          # HTML templates
└── static/             # CSS, JS, images
```

### Key Design Patterns

- **Multi-tenancy**: Society-level data isolation
- **Many-to-Many Relationships**: Users can belong to multiple societies
- **Role-Based Access**: Per-society admin privileges
- **Audit Trail**: All stock movements logged with user and timestamp
- **Soft Deletes**: Use `is_active` flags instead of hard deletes

### Custom Mixins

- `SocietyAdminRequiredMixin`: Require society admin access
- `UserManagementMixin`: Scope users to current society
- `DrawerManagementMixin`: Check drawer feature availability
- `ObjectUserManagementMixin`: Manage object users

## Testing

```bash
# Run all tests
python manage.py test stock_service

# Run specific test
python manage.py test stock_service.tests.test_models

# Run with coverage
coverage run --source='.' manage.py test stock_service
coverage report
```

## Deployment

### Production Checklist

1. **Security Settings**
```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
SECRET_KEY = 'use-environment-variable'
SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
```

2. **Static Files**
```bash
python manage.py collectstatic
```

3. **Database**
   - Use PostgreSQL or MySQL in production
   - Configure backups
   - Set up connection pooling

4. **Email Configuration**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
```

5. **Monitoring**
   - Set up logging
   - Configure error tracking (Sentry)
   - Monitor performance

## Troubleshooting

### Common Issues

**Issue**: User can't login after society registration
- **Solution**: Verify SocietyUser record exists in admin panel
- Check authentication backend is configured in settings

**Issue**: Society admin features not showing in templates
- **Solution**: Ensure context processor is added to settings
- Verify user has `is_society_admin=True` in SocietyUser

**Issue**: Drawer management not available
- **Solution**: Check society subscription level
- Verify `can_manage_drawers=True` in Society settings

**Issue**: Stock movements failing
- **Solution**: Check stock quantity is sufficient for out operations
- Verify drawer placement quantities if using drawers

### Debug Mode

Enable debug output in Django shell:
```python
from django.conf import settings
settings.DEBUG = True

# Check user's society
from django.contrib.auth.models import User
from stock_service.models import SocietyUser

user = User.objects.get(username='username')
su = SocietyUser.objects.filter(user=user)
print(f"Societies: {[s.society.name for s in su]}")
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- Follow PEP 8
- Use meaningful variable names
- Add docstrings to functions
- Write tests for new features

## License

[Specify your license here]

## Support

For support, email support@yourcompany.com or join our Slack channel.

## Changelog

### Version 2.0.0 (Current)
- Migrated to Django default User model
- Implemented many-to-many User-Society relationship
- Added per-society admin roles
- Improved multi-tenancy isolation
- Added context processor for template variables

### Version 1.0.0
- Initial release with custom User model
- Basic inventory management
- Drawer management
- Usage tracking
- Refill prediction

## Roadmap

- [ ] REST API for mobile apps
- [ ] Barcode/QR code scanning
- [ ] Advanced reporting and analytics
- [ ] Export to Excel/PDF
- [ ] Email notifications for low stock
- [ ] Multi-language support
- [ ] Dark mode
- [ ] Mobile-responsive improvements
- [ ] Integration with accounting systems
- [ ] Batch operations for stock movements
