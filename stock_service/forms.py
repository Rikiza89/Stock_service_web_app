# stock_service/forms.py (Key excerpts for M2M)
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date

from .models import (
    Society, SocietyUser, StockObjectKind, StockObject, Drawer, StockObjectDrawerPlacement,
    StockMovement, ObjectUser, StockUsage, RefillSchedule, SUBSCRIPTION_LIMITS
)


class SocietyRegistrationForm(forms.ModelForm):
    """
    Register a new society and create an admin user.
    """
    admin_username = forms.CharField(
        label=_("Admin Username"),
        max_length=150,
        help_text=_("Username for the society administrator account.")
    )
    admin_email = forms.EmailField(
        label=_("Admin Email"),
        max_length=254,
        help_text=_("Email for the administrator account.")
    )
    admin_password = forms.CharField(
        label=_("Admin Password"),
        widget=forms.PasswordInput,
        help_text=_("Password for the administrator account.")
    )
    admin_password_confirm = forms.CharField(
        label=_("Confirm Admin Password"),
        widget=forms.PasswordInput,
        help_text=_("Re-enter the password.")
    )

    class Meta:
        model = Society
        fields = ['name', 'slug']
        labels = {
            'name': _('Society Name'),
            'slug': _('Society Slug'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})

    def clean_admin_password_confirm(self):
        password = self.cleaned_data.get('admin_password')
        password_confirm = self.cleaned_data.get('admin_password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError(_("Passwords do not match."))
        return password_confirm

    def clean_slug(self):
        slug = self.cleaned_data['slug']
        if Society.objects.filter(slug__iexact=slug).exists():
            raise forms.ValidationError(_("This slug is already in use."))
        return slug

    def clean_admin_username(self):
        username = self.cleaned_data['admin_username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("This username already exists."))
        return username

    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("This email is already registered."))
        return email

    def save(self, commit=True):
        society = super().save(commit=False)
        if commit:
            society.save()
            # Create admin user
            user = User.objects.create_user(
                username=self.cleaned_data['admin_username'],
                email=self.cleaned_data['admin_email'],
                password=self.cleaned_data['admin_password'],
                is_staff=True,
                is_active=True,
            )
            # CRITICAL: Create SocietyUser link
            SocietyUser.objects.create(
                user=user,
                society=society,
                is_society_admin=True
            )
        return society


class UserCreateForm(UserCreationForm):
    """
    Create a new user and add them to a society.
    """
    is_society_admin = forms.BooleanField(
        label=_("Society Admin"),
        required=False,
        help_text=_("Whether this user is an administrator for the society.")
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_society_admin',)
        labels = {
            'username': _('Username'),
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'email': _('Email'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)

        for field_name in ['username', 'first_name', 'last_name', 'email']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

        for field_name in ['is_society_admin']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-check-input'})

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        is_society_admin = cleaned_data.get('is_society_admin')

        if not self.society:
            raise forms.ValidationError(_("Society information not provided to the form."))

        if username and self.society:
            if SocietyUser.objects.filter(
                society=self.society,
                user__username__iexact=username
            ).exists():
                self.add_error('username', _("This username is already used in this society."))

        current_level = self.society.subscription_level
        max_admins = SUBSCRIPTION_LIMITS[current_level]['max_admins']
        max_users = SUBSCRIPTION_LIMITS[current_level]['max_users']
        current_society_users = SocietyUser.objects.filter(society=self.society)
        existing_admin_count = current_society_users.filter(is_society_admin=True).count()
        existing_total_user_count = current_society_users.count()

        if is_society_admin and existing_admin_count >= max_admins:
            self.add_error(
                'is_society_admin',
                _("Cannot add more admins for this plan. (Current: %(current)s / Max: %(max)s)") % {
                    'current': existing_admin_count,
                    'max': max_admins
                }
            )

        if existing_total_user_count >= max_users:
            self.add_error(
                None,
                _("Cannot add more users for this plan. (Current: %(current)s / Max: %(max)s)") % {
                    'current': existing_total_user_count,
                    'max': max_users
                }
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if self.society:
            SocietyUser.objects.create(
                user=user,
                society=self.society,
                is_society_admin=self.cleaned_data.get('is_society_admin', False)
            )
        return user


class UserUpdateForm(UserChangeForm):
    """
    Update user information and society admin status.
    """
    is_society_admin = forms.BooleanField(
        label=_("Society Admin"),
        required=False,
        help_text=_("Whether this user is an administrator for the society.")
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active',)
        labels = {
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'email': _('Email'),
            'is_active': _('Active'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        self.original_is_society_admin = kwargs.pop('original_is_society_admin', None)
        super().__init__(*args, **kwargs)

        for field_name in ['first_name', 'last_name', 'email']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

        if 'is_active' in self.fields:
            self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

        self.fields['is_society_admin'].widget.attrs.update({'class': 'form-check-input'})

        # Set initial value for is_society_admin
        if self.instance and self.society:
            society_user = SocietyUser.objects.filter(
                user=self.instance,
                society=self.society
            ).first()
            if society_user:
                self.fields['is_society_admin'].initial = society_user.is_society_admin
                self.original_is_society_admin = society_user.is_society_admin

        # Check if this is the last admin in a free plan
        if self.instance and self.society and self.society.subscription_level == 'free':
            other_admins_count = SocietyUser.objects.filter(
                society=self.society,
                is_society_admin=True
            ).exclude(user=self.instance).count()

            if other_admins_count == 0 and self.original_is_society_admin:
                self.fields['is_society_admin'].widget.attrs['disabled'] = True
                self.fields['is_society_admin'].help_text = _(
                    "Free plan requires at least one admin. Cannot remove admin status."
                )

    def clean(self):
        cleaned_data = super().clean()
        is_society_admin_new_state = cleaned_data.get('is_society_admin')
        is_active_new_state = cleaned_data.get('is_active')

        if not self.society:
            raise forms.ValidationError(_("Society information not provided to the form."))

        current_level = self.society.subscription_level
        max_admins = SUBSCRIPTION_LIMITS[current_level]['max_admins']
        max_users = SUBSCRIPTION_LIMITS[current_level]['max_users']

        admin_count_excluding_current = SocietyUser.objects.filter(
            society=self.society,
            is_society_admin=True
        ).exclude(user=self.instance).count()

        # Check if promoting to admin exceeds limit
        if not self.original_is_society_admin and is_society_admin_new_state:
            if (admin_count_excluding_current + 1) > max_admins:
                self.add_error(
                    'is_society_admin',
                    _("Cannot add more admins for this plan. (Current: %(current)s / Max: %(max)s)") % {
                        'current': admin_count_excluding_current,
                        'max': max_admins
                    }
                )

        # Check if activating user exceeds limit
        if not self.instance.is_active and is_active_new_state:
            total_active_users_excluding_this = SocietyUser.objects.filter(
                society=self.society,
                user__is_active=True
            ).exclude(user=self.instance).count()
            if (total_active_users_excluding_this + 1) > max_users:
                self.add_error(
                    'is_active',
                    _("Cannot add more users for this plan. (Current: %(current)s / Max: %(max)s)") % {
                        'current': total_active_users_excluding_this,
                        'max': max_users
                    }
                )

        # Check if demoting the last admin in free plan
        if self.instance.pk:
            if self.original_is_society_admin and not is_society_admin_new_state:
                if self.society and self.society.subscription_level == 'free':
                    other_admins_count_if_revoked = SocietyUser.objects.filter(
                        society=self.society,
                        is_society_admin=True
                    ).exclude(user=self.instance).count()

                    if other_admins_count_if_revoked == 0:
                        self.add_error(
                            'is_society_admin',
                            _("Free plan requires at least one admin. Cannot remove this admin.")
                        )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if self.society:
            society_user, created = SocietyUser.objects.get_or_create(
                user=user,
                society=self.society
            )
            society_user.is_society_admin = self.cleaned_data.get('is_society_admin', False)
            if commit:
                society_user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form requiring society name, username, and password.
    """
    society_name = forms.CharField(
        label=_("Society Name"),
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Your society name')}),
        help_text=_("Enter the exact name of your society."),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields['username'].label = _("Username")
        self.fields['username'].widget = forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Your username')})
        self.fields['password'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Password')})

    def clean(self):
        cleaned_data = super().clean()
        society_name = cleaned_data.get('society_name')

        if society_name:
            try:
                Society.objects.get(name=society_name)
            except Society.DoesNotExist:
                self.add_error('society_name', _("The specified society was not found."))
                if hasattr(self, 'user_cache'):
                    del self.user_cache

        return cleaned_data


class StockObjectKindForm(forms.ModelForm):
    """
    Form for adding/editing stock object kinds.
    """
    class Meta:
        model = StockObjectKind
        fields = ['name', 'description']
        labels = {
            'name': _('Kind Name'),
            'description': _('Description'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control', 'rows': 3})

    def clean_name(self):
        name = self.cleaned_data['name']
        society_context = self.instance.society if self.instance and self.instance.pk else self.society

        if not society_context:
            raise forms.ValidationError(_("Society not found. Form not properly initialized."))

        queryset = StockObjectKind.objects.filter(society=society_context, name__iexact=name)

        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(_("This kind name already exists."))
        return name


class StockObjectForm(forms.ModelForm):
    """
    Form for adding/editing stock objects.
    """
    class Meta:
        model = StockObject
        fields = ['kind', 'name', 'description', 'current_quantity', 'minimum_quantity', 'unit', 'location_description', 'is_active']
        labels = {
            'kind': _('Kind'),
            'name': _('Name'),
            'description': _('Description'),
            'current_quantity': _('Current Quantity'),
            'minimum_quantity': _('Minimum Quantity'),
            'unit': _('Unit'),
            'location_description': _('Location Description'),
            'is_active': _('Active'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        if self.society:
            self.fields['kind'].queryset = StockObjectKind.objects.filter(society=self.society)
            self.fields['kind'].empty_label = _("Select a kind")

    def clean_name(self):
        name = self.cleaned_data['name']
        if self.society and StockObject.objects.filter(society=self.society, name=name).exists():
            if self.instance and self.instance.name == name:
                pass
            else:
                raise forms.ValidationError(_("This item name already exists."))
        return name


class StockMovementForm(forms.ModelForm):
    """
    Form for recording stock movements (in/out).
    """
    class Meta:
        model = StockMovement
        fields = ['stock_object', 'quantity', 'notes', 'drawer_involved']
        labels = {
            'stock_object': _('Stock Item'),
            'quantity': _('Quantity'),
            'notes': _('Notes'),
            'drawer_involved': _('Related Drawer'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        if self.society:
            self.fields['stock_object'].queryset = StockObject.objects.filter(society=self.society)
            self.fields['drawer_involved'].queryset = Drawer.objects.filter(society=self.society)

            if not self.society.can_manage_drawers:
                self.fields['drawer_involved'].widget = forms.HiddenInput()
                self.fields['drawer_involved'].required = False
            else:
                self.fields['drawer_involved'].empty_label = _("Select a drawer (optional)")


class ObjectUserForm(forms.ModelForm):
    """
    Form for adding/editing object users (people/departments using stock).
    """
    class Meta:
        model = ObjectUser
        fields = ['name', 'contact_info', 'notes']
        labels = {
            'name': _('Name/Department'),
            'contact_info': _('Contact Information'),
            'notes': _('Notes'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['contact_info'].widget.attrs.update({'class': 'form-control'})
        self.fields['notes'].widget.attrs.update({'class': 'form-control', 'rows': 4})

    def clean_name(self):
        name = self.cleaned_data['name']
        society_for_validation = self.society

        if not society_for_validation:
            raise forms.ValidationError(_("Society not found. Form not properly initialized."))

        queryset = ObjectUser.objects.filter(society=society_for_validation, name__iexact=name)

        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(_("This object user name already exists."))
        return name


class StockUsageForm(forms.ModelForm):
    """
    Form for recording stock usage by object users.
    """
    class Meta:
        model = StockUsage
        fields = ['stock_object', 'object_user', 'quantity_used', 'start_date', 'end_date', 'notes']
        labels = {
            'stock_object': _('Stock Item'),
            'object_user': _('User/Department'),
            'quantity_used': _('Quantity Used'),
            'start_date': _('Start Date'),
            'end_date': _('End Date'),
            'notes': _('Notes'),
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        if self.society:
            self.fields['stock_object'].queryset = StockObject.objects.filter(society=self.society)
            self.fields['object_user'].queryset = ObjectUser.objects.filter(society=self.society)
            self.fields['stock_object'].empty_label = _("Select item")
            self.fields['object_user'].empty_label = _("Select user/department")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', _("End date must be after start date."))
        return cleaned_data


class RefillScheduleForm(forms.ModelForm):
    """
    Form for managing refill schedules.
    """
    class Meta:
        model = RefillSchedule
        fields = ['stock_object', 'scheduled_date', 'quantity_to_refill', 'notes']
        labels = {
            'stock_object': _('Stock Item'),
            'scheduled_date': _('Scheduled Date'),
            'quantity_to_refill': _('Quantity to Refill'),
            'notes': _('Notes'),
        }
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'quantity_to_refill': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'stock_object': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        self.initial_stock_object = kwargs.pop('initial_stock_object', None)
        super().__init__(*args, **kwargs)

        if self.society:
            self.fields['stock_object'].queryset = StockObject.objects.filter(
                society=self.society,
                is_active=True
            ).order_by('name')
        else:
            self.fields['stock_object'].queryset = StockObject.objects.none()

        self.fields['stock_object'].empty_label = _("Select item")

        if self.initial_stock_object:
            self.fields['stock_object'].initial = self.initial_stock_object
            self.fields['stock_object'].widget.attrs['disabled'] = 'disabled'

    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data['scheduled_date']
        if scheduled_date and scheduled_date < date.today():
            raise forms.ValidationError(_("Scheduled date must be today or later."))
        return scheduled_date

    def clean_stock_object(self):
        if self.fields['stock_object'].widget.attrs.get('disabled') and self.initial_stock_object:
            return self.initial_stock_object
        return self.cleaned_data['stock_object']

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.initial_stock_object and not instance.stock_object:
            instance.stock_object = self.initial_stock_object
        if commit:
            instance.save()
        return instance


class DrawerForm(forms.ModelForm):
    """
    Form for adding/editing drawers.
    """
    class Meta:
        model = Drawer
        fields = ['cabinet_name', 'drawer_letter_x', 'drawer_number_y', 'description']
        labels = {
            'cabinet_name': _('Cabinet Name'),
            'drawer_letter_x': _('Letter (X)'),
            'drawer_number_y': _('Number (Y)'),
            'description': _('Description'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        cabinet_name = cleaned_data.get('cabinet_name')
        drawer_letter_x = cleaned_data.get('drawer_letter_x')
        drawer_number_y = cleaned_data.get('drawer_number_y')

        if self.society and cabinet_name and drawer_letter_x and drawer_number_y:
            qs = Drawer.objects.filter(
                society=self.society,
                cabinet_name=cabinet_name,
                drawer_letter_x__iexact=drawer_letter_x,
                drawer_number_y=drawer_number_y
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(_("This drawer already exists."))
        return cleaned_data


class StockObjectDrawerPlacementForm(forms.ModelForm):
    """
    Form for placing stock items in drawers.
    """
    class Meta:
        model = StockObjectDrawerPlacement
        fields = ['stock_object', 'drawer', 'quantity']
        labels = {
            'stock_object': _('Stock Item'),
            'drawer': _('Drawer'),
            'quantity': _('Quantity'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        if self.society:
            self.fields['stock_object'].queryset = StockObject.objects.filter(society=self.society)
            self.fields['drawer'].queryset = Drawer.objects.filter(society=self.society)
            self.fields['stock_object'].empty_label = _("Select item")
            self.fields['drawer'].empty_label = _("Select drawer")

    def clean(self):
        cleaned_data = super().clean()
        stock_object = cleaned_data.get('stock_object')
        drawer = cleaned_data.get('drawer')
        quantity = cleaned_data.get('quantity')

        if stock_object and drawer:
            qs = StockObjectDrawerPlacement.objects.filter(
                stock_object=stock_object,
                drawer=drawer
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(_("This item is already assigned to this drawer."))

        if stock_object and quantity is not None and quantity > stock_object.current_quantity:
            self.add_error('quantity', _("Quantity cannot exceed current stock."))

        return cleaned_data


class SocietySettingsForm(forms.ModelForm):
    """
    Form for updating society settings.
    """
    class Meta:
        model = Society
        fields = ['can_manage_drawers', 'shows_drawers_in_list', 'subscription_level']
        labels = {
            'can_manage_drawers': _('Enable Drawer Management'),
            'shows_drawers_in_list': _('Show Drawers in Stock List'),
            'subscription_level': _('Subscription Level'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ['can_manage_drawers', 'shows_drawers_in_list']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-check-input'})

        if 'subscription_level' in self.fields:
            self.fields['subscription_level'].widget.attrs.update({'class': 'form-control'})

        if self.instance:
            if self.instance.subscription_level == 'free':
                if 'can_manage_drawers' in self.fields:
                    self.fields['can_manage_drawers'].widget.attrs['disabled'] = 'disabled'
                    self.fields['can_manage_drawers'].help_text += _(" (Not available in free plan)")

                if 'shows_drawers_in_list' in self.fields:
                    self.fields['shows_drawers_in_list'].widget.attrs['disabled'] = 'disabled'
                    self.fields['shows_drawers_in_list'].help_text += _(" (Not available in free plan)")

            elif self.instance.subscription_level == 'basic':
                if 'shows_drawers_in_list' in self.fields:
                    self.fields['shows_drawers_in_list'].widget.attrs['disabled'] = 'disabled'
                    self.fields['shows_drawers_in_list'].help_text += _(" (Premium plan only)")

    def clean_can_manage_drawers(self):
        can_manage_drawers = self.cleaned_data.get('can_manage_drawers')
        submitted_subscription_level = self.cleaned_data.get('subscription_level')

        if can_manage_drawers and submitted_subscription_level == 'free':
            raise forms.ValidationError(_("This feature is not available in the free plan."))
        return can_manage_drawers

    def clean_shows_drawers_in_list(self):
        shows_drawers_in_list = self.cleaned_data.get('shows_drawers_in_list')
        submitted_subscription_level = self.cleaned_data.get('subscription_level')

        if shows_drawers_in_list and submitted_subscription_level == 'free':
            raise forms.ValidationError(_("This feature is not available in the free plan."))
        if shows_drawers_in_list and submitted_subscription_level == 'basic':
            raise forms.ValidationError(_("This feature is only available in the premium plan."))
        return shows_drawers_in_list