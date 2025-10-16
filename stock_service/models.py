# stock_service/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import uuid

SUBSCRIPTION_LIMITS = {
    'free': {
        'max_admins': 1,
        'max_users': 2,
    },
    'basic': {
        'max_admins': 2,
        'max_users': 10,
    },
    'premium': {
        'max_admins': float('inf'),
        'max_users': float('inf'),
    },
}

SUBSCRIPTION_CHOICES = [
    ('free', _('Free')),
    ('basic', _('Basic')),
    ('premium', _('Premium')),
]


class Society(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Society Name"), max_length=255, unique=True)
    slug = models.SlugField(_("Society Slug"), unique=True)
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

    def __str__(self):
        return self.name

    def get_max_admins(self):
        return SUBSCRIPTION_LIMITS.get(self.subscription_level, {})['max_admins']

    def get_max_users(self):
        return SUBSCRIPTION_LIMITS.get(self.subscription_level, {})['max_users']


class SocietyUser(models.Model):
    """
    Through model for User-Society many-to-many relationship.
    Tracks if a user is an admin for a specific society.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='society_memberships')
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='user_memberships')
    is_society_admin = models.BooleanField(_("Is Society Admin"), default=False)
    
    class Meta:
        unique_together = ('user', 'society')
        verbose_name = _("Society User")
        verbose_name_plural = _("Society Users")
    
    def __str__(self):
        return f"{self.user.username} - {self.society.name} ({'Admin' if self.is_society_admin else 'User'})"


class StockObjectKind(models.Model):
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
    minimum_quantity = models.PositiveIntegerField(_("Minimum Quantity"), default=0)
    unit = models.CharField(_("Unit"), max_length=50, blank=True)
    location_description = models.CharField(_("Location Description"), max_length=255, blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Stock Object")
        verbose_name_plural = _("Stock Objects")
        unique_together = ('society', 'name')

    def __str__(self):
        return f"{self.name} ({self.society.name})"


class Drawer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='drawers',
        verbose_name=_("Society")
    )
    cabinet_name = models.CharField(_("Cabinet Name"), max_length=100, blank=True)
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
        verbose_name=_("Drawer Involved")
    )

    class Meta:
        verbose_name = _("Stock Movement")
        verbose_name_plural = _("Stock Movements")
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.movement_type.upper()} {self.quantity} of {self.stock_object.name}"


class ObjectUser(models.Model):
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
    end_date = models.DateField(_("End Date"), null=True, blank=True)
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
        return f"{self.object_user.name} used {self.quantity_used} of {self.stock_object.name}"


class RefillSchedule(models.Model):
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
        return f"Refill {self.quantity_to_refill} of {self.stock_object.name}"