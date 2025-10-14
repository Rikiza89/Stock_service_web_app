# stock_service/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
import uuid

# --- Subscription Plan Limits (NEW) ---
SUBSCRIPTION_LIMITS = {
    'free': {
        'max_admins': 1,
        'max_users': 2,  # Total users including admins
    },
    'basic': {
        'max_admins': 2,
        'max_users': 10, # Total users including admins
    },
    'premium': {
        'max_admins': float('inf'), # Use float('inf') for indefinite
        'max_users': float('inf'),  # Use float('inf') for indefinite
    },
}

# Define choices for subscription plans (ensure this is consistent with your current models.py)
SUBSCRIPTION_CHOICES = [
    ('free', _('Free')),
    ('basic', _('Basic')),
    ('premium', _('Premium')),
]


class Society(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Society Name"), max_length=255, unique=True)
    slug = models.SlugField(_("Society Slug"), unique=True, help_text=_("A unique identifier for the society in URLs."))
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subscription_level = models.CharField(
        _("Subscription Level"),
        max_length=50,
        choices=SUBSCRIPTION_CHOICES,
        default='free'
    )
    can_manage_drawers = models.BooleanField(_("Can Manage Drawers"), default=False)
    shows_drawers_in_list = models.BooleanField(_("Show Drawers in Stock List"), default=False)

    class Meta:
        verbose_name = _("社会")
        verbose_name_plural = _("社会")
        unique_together = ('slug',) # Ensure slug is unique, or remove if not desired

    def __str__(self):
        return self.name

    def get_subscription_level_display(self):
        return dict(SUBSCRIPTION_CHOICES).get(self.subscription_level, self.subscription_level)

    # --- NEW HELPER METHODS FOR LIMITS ---
    def get_max_admins(self):
        return SUBSCRIPTION_LIMITS.get(self.subscription_level, {})['max_admins']

    def get_max_users(self):
        return SUBSCRIPTION_LIMITS.get(self.subscription_level, {})['max_users']

# class User(AbstractUser):
#     """
#     Custom user model for the stock management system.
#     Each user belongs to a specific society.
#     """
#     society = models.ForeignKey(
#         'Society',
#         on_delete=models.CASCADE,
#         related_name='users',
#         verbose_name=_("Society")
#     )
#     is_society_admin = models.BooleanField(_("Is Society Admin"), default=False)

#     class Meta:
#         verbose_name = _("User")
#         verbose_name_plural = _("Users")
#         unique_together = ('username', 'society') # Ensure username is unique within a society

#     def __str__(self):
#         return f"{self.username} ({self.society.name})"

#     # Add related_name to avoid clashes with auth.User
#     # Make sure related_name for groups and user_permissions are UNIQUE
#     groups = models.ManyToManyField(
#         Group,
#         verbose_name=_('groups'),
#         blank=True,
#         help_text=_(
#             'The groups this user belongs to. A user will get all permissions '
#             'granted to each of their groups.'
#         ),
#         related_name="stock_service_user_groups", # Changed for clarity and uniqueness
#         related_query_name="stock_service_user_in_group", # Changed for clarity and uniqueness
#     )
#     user_permissions = models.ManyToManyField(
#         Permission,
#         verbose_name=_('user permissions'),
#         blank=True,
#         help_text=_('Specific permissions for this user.'),
#         related_name="stock_service_user_permissions", # <-- CRITICAL: Made this unique!
#         related_query_name="stock_service_user_has_perm", # <-- Also made this unique!
#     )

class User(AbstractUser):
    """
    Custom user model for the stock management system.
    Each user belongs to a specific society.
    """
    society = models.ForeignKey(
        'Society',
        on_delete=models.CASCADE,
        related_name='users',
        verbose_name=_("Society"),
        null=True,  # Allow NULL temporarily to handle existing users
        blank=True  # Allow blank in forms
    )
    is_society_admin = models.BooleanField(_("Is Society Admin"), default=False)

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        unique_together = ('username', 'society') # Ensure username is unique within a society

    def __str__(self):
        if self.society:
            return f"{self.username} ({self.society.name})"
        else:
            return f"{self.username} (No Society)"

    def clean(self):
        """
        Custom validation to ensure users have required fields.
        """
        from django.core.exceptions import ValidationError
        super().clean()

        # Allow superusers to exist without a Society
        if self.is_active and not self.is_superuser and not self.society:
            raise ValidationError(_("アクティブなユーザーは社会に関連付けられている必要があります。"))

    def save(self, *args, **kwargs):
        """
        Override save to run validation.
        """
        # Only run full_clean for new users or when explicitly requested
        if not self.pk or kwargs.pop('validate', False):
            self.full_clean()
        super().save(*args, **kwargs)

    # Add related_name to avoid clashes with auth.User
    # Make sure related_name for groups and user_permissions are UNIQUE
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="stock_service_user_groups", # Changed for clarity and uniqueness
        related_query_name="stock_service_user_in_group", # Changed for clarity and uniqueness
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="stock_service_user_permissions", # <-- CRITICAL: Made this unique!
        related_query_name="stock_service_user_has_perm", # <-- Also made this unique!
    )

class StockObjectKind(models.Model):
    """
    Defines the kind of stock object a society wants to manage (e.g., 'Electronics', 'Tools').
    """
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='stock_object_kinds',
        verbose_name=_("Society")
    )
    name = models.CharField(_("Kind Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Stock Object Kind")
        verbose_name_plural = _("Stock Object Kinds")
        unique_together = ('society', 'name')

    def __str__(self):
        return f"{self.name} ({self.society.name})"

class StockObject(models.Model):
    """
    Represents a specific stock item managed by a society.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='stock_objects',
        verbose_name=_("Society")
    )
    kind = models.ForeignKey(
        StockObjectKind,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Kind")
    )
    name = models.CharField(_("Stock Object Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    current_quantity = models.PositiveIntegerField(_("Current Quantity"), default=0)
    minimum_quantity = models.PositiveIntegerField(_("Minimum Quantity"), default=0, help_text=_("Threshold for refilling."))
    unit = models.CharField(_("Unit"), max_length=50, blank=True, help_text=_("e.g., 'pcs', 'kg', 'meters'"))
    location_description = models.CharField(_("Location Description"), max_length=255, blank=True, help_text=_("General location if not using drawers."))
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Stock Object")
        verbose_name_plural = _("Stock Objects")
        unique_together = ('society', 'name') # Ensures uniqueness of stock object name within a society

    def __str__(self):
        return f"{self.name} ({self.society.name})"

class Drawer(models.Model):
    """
    Represents a numbered drawer within a parts cabinet for a society.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='drawers',
        verbose_name=_("Society")
    )
    cabinet_name = models.CharField(_("Cabinet Name"), max_length=100, blank=True, help_text=_("e.g., 'Cabinet A'"))
    drawer_letter_x = models.CharField(_("Drawer Letter (X-axis)"), max_length=1)
    drawer_number_y = models.PositiveIntegerField(_("Drawer Number (Y-axis)"))
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Drawer")
        verbose_name_plural = _("Drawers")
        unique_together = ('society', 'cabinet_name', 'drawer_letter_x', 'drawer_number_y')
        ordering = ['cabinet_name', 'drawer_letter_x', 'drawer_number_y']

    def __str__(self):
        return f"{self.cabinet_name} - {self.drawer_letter_x}{self.drawer_number_y} ({self.society.name})"

class StockObjectDrawerPlacement(models.Model):
    """
    Links a StockObject to a Drawer and specifies the quantity in that drawer.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock_object = models.ForeignKey(
        StockObject,
        on_delete=models.CASCADE,
        related_name='drawer_placements',
        verbose_name=_("Stock Object")
    )
    drawer = models.ForeignKey(
        Drawer,
        on_delete=models.CASCADE,
        related_name='stock_object_contents',
        verbose_name=_("Drawer")
    )
    quantity = models.PositiveIntegerField(_("Quantity in Drawer"), default=0)

    class Meta:
        verbose_name = _("Stock Object Drawer Placement")
        verbose_name_plural = _("Stock Object Drawer Placements")
        unique_together = ('stock_object', 'drawer')

    def __str__(self):
        return f"{self.stock_object.name} in {self.drawer} (x{self.quantity})"


class StockMovement(models.Model):
    """
    Logs the in and out movements of stock objects.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name=_("Society")
    )
    stock_object = models.ForeignKey(
        StockObject,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name=_("Stock Object")
    )
    movement_type = models.CharField(
        _("Movement Type"),
        max_length=10,
        choices=[('in', _('In')), ('out', _('Out'))]
    )
    quantity = models.PositiveIntegerField(_("Quantity"))
    moved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Moved By"),
        related_name='stock_operations'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(_("Notes"), blank=True)
    drawer_involved = models.ForeignKey(
        Drawer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Drawer Involved"),
        help_text=_("Drawer from which stock was pulled out or put in.")
    )

    class Meta:
        verbose_name = _("Stock Movement")
        verbose_name_plural = _("Stock Movements")
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.movement_type.upper()} {self.quantity} of {self.stock_object.name} by {self.moved_by or 'N/A'} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class ObjectUser(models.Model):
    """
    Represents a user (e.g., an employee, a department) who uses stock objects.
    This is distinct from the system User who logs in.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='object_users',
        verbose_name=_("Society")
    )
    name = models.CharField(_("Object User Name"), max_length=255)
    contact_info = models.CharField(_("Contact Information"), max_length=255, blank=True)
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Object User")
        verbose_name_plural = _("Object Users")
        unique_together = ('society', 'name')

    def __str__(self):
        return f"{self.name} ({self.society.name})"

class StockUsage(models.Model):
    """
    Logs which ObjectUser is using how many StockObjects in what period.
    Used for predicting refill timing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='stock_usages',
        verbose_name=_("Society")
    )
    stock_object = models.ForeignKey(
        StockObject,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name=_("Stock Object")
    )
    object_user = models.ForeignKey(
        ObjectUser,
        on_delete=models.CASCADE,
        related_name='used_stock_objects',
        verbose_name=_("Object User")
    )
    quantity_used = models.PositiveIntegerField(_("Quantity Used"))
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"), null=True, blank=True) # Can be ongoing
    notes = models.TextField(_("Notes"), blank=True)
    logged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Logged By"),
        related_name='logged_usages'
    )
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Stock Usage")
        verbose_name_plural = _("Stock Usages")
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.object_user.name} used {self.quantity_used} of {self.stock_object.name} from {self.start_date} to {self.end_date or 'Now'}"

class RefillSchedule(models.Model):
    """
    Manages scheduled refills for stock objects.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='refill_schedules',
        verbose_name=_("Society")
    )
    stock_object = models.ForeignKey(
        StockObject,
        on_delete=models.CASCADE,
        related_name='refill_schedules',
        verbose_name=_("Stock Object")
    )
    scheduled_date = models.DateField(_("Scheduled Refill Date"))
    quantity_to_refill = models.PositiveIntegerField(_("Quantity to Refill"))
    is_completed = models.BooleanField(_("Is Completed"), default=False)
    completed_date = models.DateField(_("Completed Date"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Refill Schedule")
        verbose_name_plural = _("Refill Schedules")
        ordering = ['scheduled_date', 'stock_object__name']

    def __str__(self):
        status = "Completed" if self.is_completed else "Pending"
        return f"Refill {self.quantity_to_refill} of {self.stock_object.name} on {self.scheduled_date} ({status})"
