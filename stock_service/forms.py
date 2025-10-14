# stock_service/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date

from .models import (
    Society, User, StockObjectKind, StockObject, Drawer, StockObjectDrawerPlacement,
    StockMovement, ObjectUser, StockUsage, RefillSchedule, SUBSCRIPTION_LIMITS
)
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm

class SocietyRegistrationForm(forms.ModelForm):
    """
    新しい社会を登録するためのフォーム。
    社会管理者となるユーザーも同時に作成する。
    """
    admin_username = forms.CharField(
        label=_("管理者ユーザー名"),
        max_length=150,
        help_text=_("この社会の管理者アカウントのユーザー名を入力してください。")
    )
    admin_email = forms.EmailField(
        label=_("管理者メールアドレス"),
        max_length=254,
        help_text=_("管理者アカウントのメールアドレスを入力してください。")
    )
    admin_password = forms.CharField(
        label=_("管理者パスワード"),
        widget=forms.PasswordInput,
        help_text=_("管理者アカウントのパスワードを入力してください。")
    )
    admin_password_confirm = forms.CharField(
        label=_("管理者パスワード確認"),
        widget=forms.PasswordInput,
        help_text=_("パスワードを再入力してください。")
    )

    class Meta:
        model = Society
        fields = ['name', 'slug']
        labels = {
            'name': _('社会名'),
            'slug': _('社会スラッグ'),
        }
        help_texts = {
            'slug': _('URLに使用される、社会の一意の識別子です（例: my-company）。'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 各フィールドにBootstrapの'form-control'クラスを適用
        for field_name in self.fields:
            # パスワード入力フィールドには適用しない
            if field_name not in ['admin_password', 'admin_password_confirm']:
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

            # 特にパスワードフィールドにも'form-control'を適用したい場合
            if field_name in ['admin_password', 'admin_password_confirm']:
                 self.fields[field_name].widget.attrs.update({'class': 'form-control'})

    def clean_admin_password_confirm(self):
        password = self.cleaned_data.get('admin_password')
        password_confirm = self.cleaned_data.get('admin_password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError(_("パスワードが一致しません。"))
        return password_confirm

    def clean_slug(self):
        slug = self.cleaned_data['slug']
        if Society.objects.filter(slug__iexact=slug).exists(): # 大文字小文字を区別しないチェック
            raise forms.ValidationError(_("このスラッグは既に使用されています。別なものを選択してください。"))
        return slug

    def clean_admin_username(self):
        username = self.cleaned_data['admin_username']
        # 全社会でユーザー名が一意であることを確認
        if User.objects.filter(username__iexact=username).exists(): # 大文字小文字を区別しないチェック
            raise forms.ValidationError(_("このユーザー名は既に存在します。別のユーザー名を選択してください。"))
        return username

    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        # 全社会でメールアドレスが一意であることを確認
        if User.objects.filter(email__iexact=email).exists(): # 大文字小文字を区別しないチェック
            raise forms.ValidationError(_("このメールアドレスは既に登録されています。別のメールアドレスを使用してください。"))
        return email

    def save(self, commit=True):
        society = super().save(commit=False)
        # 新規作成される社会は、デフォルトで'free'プランに設定されるため、
        # 1管理者、2ユーザーの制限は自動的に満たされます。
        # ここでsubscription_levelを明示的に設定することもできますが、
        # モデルのデフォルト値に任せるのが一般的です。
        # society.subscription_level = 'free' # 明示的に設定する場合

        if commit:
            society.save()
            # 社会管理者ユーザーを作成
            User.objects.create_user(
                username=self.cleaned_data['admin_username'],
                email=self.cleaned_data['admin_email'],
                password=self.cleaned_data['admin_password'],
                society=society,
                is_staff=True,        # Django adminへのアクセスを許可
                is_society_admin=True, # カスタムの社会管理者フラグ
                is_active=True,       # 新規作成時は有効とする
            )
        return society

class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'is_society_admin', 'is_active',)
        labels = {
            'username': _('ユーザー名'),
            'first_name': _('名'),
            'last_name': _('姓'),
            'email': _('メールアドレス'),
            'is_society_admin': _('社会管理者'),
            'is_active': _('有効'),
        }
        help_texts = {
            'username': _('必須。150文字以下。文字、数字、@/./+/-/_のみ。'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None) # Get the society instance from kwargs
        super().__init__(*args, **kwargs)

        # Apply Bootstrap's form-control class to all text/email inputs
        for field_name in ['username', 'first_name', 'last_name', 'email']:
            if field_name in self.fields: # Check if field exists before updating attrs
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

        # Apply form-check-input to checkboxes
        for field_name in ['is_society_admin', 'is_active']:
            if field_name in self.fields: # Check if field exists before updating attrs
                self.fields[field_name].widget.attrs.update({'class': 'form-check-input'})


    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        is_society_admin = cleaned_data.get('is_society_admin') # The NEW state of is_society_admin

        if not self.society:
            # This should be caught by UserCreateView's get_form_kwargs, but as a safeguard
            raise forms.ValidationError(_("社会情報がフォームに渡されていません。"))

        # Check unique_together constraint for username within society
        if username and self.society:
            if User.objects.filter(society=self.society, username__iexact=username).exists():
                self.add_error('username', _("このユーザー名は既にこの社会で使用されています。"))

        # --- NEW: Subscription Limits Validation for Creation ---
        current_level = self.society.subscription_level
        max_admins = SUBSCRIPTION_LIMITS[current_level]['max_admins']
        max_users = SUBSCRIPTION_LIMITS[current_level]['max_users']

        # Get current counts for the society (excluding the user being created as they are not saved yet)
        current_society_users = User.objects.filter(society=self.society)
        existing_admin_count = current_society_users.filter(is_society_admin=True).count()
        existing_total_user_count = current_society_users.count()

        # Check admin limits if this new user is an admin
        if is_society_admin and existing_admin_count >= max_admins:
            self.add_error(
                'is_society_admin',
                _("現在のサブスクリプションプランでは、これ以上管理者を追加できません。(現在の管理者数: %(current)s / 最大: %(max)s)") % {
                    'current': existing_admin_count,
                    'max': max_admins
                }
            )

        # Check total user limits if this new user would exceed them
        if existing_total_user_count >= max_users:
            self.add_error(
                None, # General form error for total user count
                _("現在のサブスクリプションプランでは、これ以上ユーザーを追加できません。(現在のユーザー数: %(current)s / 最大: %(max)s)") % {
                    'current': existing_total_user_count,
                    'max': max_users
                }
            )
        # --- END NEW ---

        return cleaned_data


class UserUpdateForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_society_admin', 'is_active',) # Exclude username to prevent complexity
        labels = {
            'first_name': _('名'),
            'last_name': _('姓'),
            'email': _('メールアドレス'),
            'is_society_admin': _('社会管理者'),
            'is_active': _('有効'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        # Store the original is_society_admin value when the form is initialized
        self.original_is_society_admin = kwargs.pop('original_is_society_admin', None)
        super().__init__(*args, **kwargs)

        # Apply Bootstrap classes
        for field_name in ['first_name', 'last_name', 'email']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

        for field_name in ['is_society_admin', 'is_active']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-check-input'})

        # --- NEW: Disable 'is_society_admin' if this is the ONLY admin on a 'free' plan ---
        if self.instance and self.instance.is_society_admin and \
           self.society and self.society.subscription_level == 'free':
            # Check if this user is the only admin for their society
            # Exclude the current user instance from the count
            other_admins_count = User.objects.filter(
                society=self.society, is_society_admin=True
            ).exclude(pk=self.instance.pk).count()

            if other_admins_count == 0:
                # If no other admins, prevent deactivating this user's admin status
                self.fields['is_society_admin'].widget.attrs['disabled'] = True
                self.fields['is_society_admin'].help_text = _("無料プランでは、少なくとも1人の管理者が常に必要です。別の管理者がいる場合にのみ、このユーザーの管理者ステータスを解除できます。")
        # --- END NEW ---


    def clean(self):
        cleaned_data = super().clean()
        is_society_admin_new_state = cleaned_data.get('is_society_admin') # The NEW state from form
        is_active_new_state = cleaned_data.get('is_active') # The NEW state from form

        if not self.society:
            raise forms.ValidationError(_("社会情報がフォームに渡されていません。"))

        # --- NEW: Subscription Limits Validation for Update ---
        current_level = self.society.subscription_level
        max_admins = SUBSCRIPTION_LIMITS[current_level]['max_admins']
        max_users = SUBSCRIPTION_LIMITS[current_level]['max_users']

        # Get counts for the society, considering the user being updated
        current_society_users_queryset = User.objects.filter(society=self.society)

        # Calculate admin count *before* this user's admin status change but *after* removing this user's original status
        admin_count_excluding_current_user = current_society_users_queryset.filter(is_society_admin=True).exclude(pk=self.instance.pk).count()

        # If this user is becoming an admin (and wasn't before) AND limits apply
        if not self.original_is_society_admin and is_society_admin_new_state:
            if (admin_count_excluding_current_user + 1) > max_admins:
                self.add_error(
                    'is_society_admin',
                    _("現在のサブスクリプションプランでは、これ以上管理者を追加できません。(現在の管理者数: %(current)s / 最大: %(max)s)") % {
                        'current': admin_count_excluding_current_user, # Show count before this user is added as admin
                        'max': max_admins
                    }
                )

        # Total user count validation (only if user is being reactivated and total count would exceed limit)
        # This form's primary purpose is updating existing users. The total user count isn't *incremented* by an update.
        # However, if a user is currently inactive and is being made active, we must check.
        if not self.instance.is_active and is_active_new_state: # User was inactive, now becoming active
            total_active_users_excluding_this_user = current_society_users_queryset.filter(is_active=True).exclude(pk=self.instance.pk).count()
            if (total_active_users_excluding_this_user + 1) > max_users:
                 self.add_error(
                    'is_active',
                    _("現在のサブスクリプションプランでは、これ以上有効なユーザーを追加できません。(現在の有効ユーザー数: %(current)s / 最大: %(max)s)") % {
                        'current': total_active_users_excluding_this_user,
                        'max': max_users
                    }
                )

        # Re-check the "only admin" lockout logic on submit (backend validation)
        # This handles cases where client-side disabling might be bypassed.
        if self.instance and self.instance.pk:
            # If current user WAS an admin, and is NOW NOT an admin (i.e., revoking status)
            if self.original_is_society_admin and not is_society_admin_new_state:
                if self.society and self.society.subscription_level == 'free':
                    # Count other admins (excluding the current user, who is about to be non-admin)
                    other_admins_count_if_this_user_is_revoked = current_society_users_queryset.filter(is_society_admin=True).exclude(pk=self.instance.pk).count()

                    if other_admins_count_if_this_user_is_revoked == 0:
                        self.add_error(
                            'is_society_admin',
                            _("無料プランでは、少なくとも1人の管理者が常に必要です。このユーザーの管理者ステータスを解除するには、他の管理者がいる必要があります。")
                        )
        # --- END NEW ---

        return cleaned_data

class CustomAuthenticationForm(AuthenticationForm):
    """
    社会名、ユーザー名、パスワードを要求するカスタム認証フォーム。
    DjangoのAuthenticationFormを継承し、society_nameフィールドを追加します。
    """
    society_name = forms.CharField(
        label=_("社会名"),
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('あなたの会社の名前')}),
        help_text=_("所属する社会の正確な名前を入力してください。"),
    )

    # AuthenticationFormが既にusernameとpasswordフィールドを提供しているので、
    # ここで改めて定義する必要はありません。
    # ただし、ウィジェットやヘルプテキストをカスタマイズする場合はここで上書きできます。
    # 例:
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        # usernameフィールドのラベルを変更する場合
        self.fields['username'].label = _("ユーザー名")
        self.fields['username'].widget = forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('あなたのユーザー名')})
        self.fields['password'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('パスワード')})


    def clean(self):
        """
        カスタムバリデーションロジック。
        まずAuthenticationFormのバリデーションを実行し、その後社会名をチェックします。
        """
        # AuthenticationFormのcleanメソッドを呼び出し、usernameとpasswordを検証
        # これにより、ユーザー名とパスワードの基本的なチェックが行われます。
        cleaned_data = super().clean()

        # ここでsociety_nameを取得して、存在するかどうかをチェックします。
        # ユーザー認証はビューで行うため、ここでは社会の存在確認のみに留めます。
        society_name = cleaned_data.get('society_name')

        if society_name:
            try:
                Society.objects.get(name=society_name)
            except Society.DoesNotExist:
                # AuthenticationFormのcleaned_dataからエラーを削除し、
                # 新しいエラーを追加してフィールドに紐づける
                self.add_error('society_name', _("指定された社会が見つかりません。"))
                # AuthenticationFormがis_valid()で認証失敗と判断した場合は
                # user_cacheがNoneになるので、それをクリアして認証失敗の状態を維持
                if hasattr(self, 'user_cache'):
                    del self.user_cache

        # cleanメソッドの最後でエラーが追加されている可能性があるため、
        # ValidationErrorを再raiseしないように注意
        return cleaned_data


class StockObjectKindForm(forms.ModelForm):
    """
    在庫品目の種類を追加・編集するためのフォーム。
    """
    class Meta:
        model = StockObjectKind
        fields = ['name', 'description'] # descriptionフィールドを追加
        labels = {
            'name': _('種類名'),
            'description': _('説明'), # descriptionのラベルを追加
        }
        help_texts = {
            'name': _('在庫品目の種類を識別する一意の名前。'),
            'description': _('この品目種類の詳細な説明。'), # descriptionのヘルプテキストを追加
        }

    def __init__(self, *args, **kwargs):
        # society インスタンスをフォームに渡すためのカスタム引数
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)

        # Bootstrapクラスを適用
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control', 'rows': 3})


    def clean_name(self):
        name = self.cleaned_data['name']

        # society_context を確実に取得
        society_context = self.instance.society if self.instance and self.instance.pk else self.society

        if not society_context:
            raise forms.ValidationError(_("社会情報が見つかりません。フォームが正しく初期化されていません。"))

        # 同じ社会内で名前の重複をチェック
        queryset = StockObjectKind.objects.filter(society=society_context, name__iexact=name) # 大文字小文字を区別しない

        # 既存のオブジェクトを更新している場合、自分自身をチェック対象から除外
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(_("この種類名は既に存在します。"))
        return name


class StockObjectForm(forms.ModelForm):
    """
    在庫品目を追加・編集するためのフォーム。
    """
    class Meta:
        model = StockObject
        fields = ['kind', 'name', 'description', 'current_quantity', 'minimum_quantity', 'unit', 'location_description', 'is_active']
        labels = {
            'kind': _('種類'),
            'name': _('品目名'),
            'description': _('説明'),
            'current_quantity': _('現在の数量'),
            'minimum_quantity': _('最低在庫数量'),
            'unit': _('単位'),
            'location_description': _('一般的な保管場所'),
            'is_active': _('有効'),
        }
        help_texts = {
            'minimum_quantity': _('この数量を下回ると補充が必要と見なされます。'),
            'unit': _('例: 個、kg、メートル'),
            'location_description': _('引き出しを使用しない場合の一般的な保管場所の説明。'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        if self.society:
            # 現在の社会に紐づくStockObjectKindのみを表示
            self.fields['kind'].queryset = StockObjectKind.objects.filter(society=self.society)
            self.fields['kind'].empty_label = _("種類を選択してください")

    def clean_name(self):
        name = self.cleaned_data['name']
        if self.society and StockObject.objects.filter(society=self.society, name=name).exists():
            if self.instance and self.instance.name == name: # 既存のオブジェクト自身の場合はOK
                pass
            else:
                raise forms.ValidationError(_("この品目名は既に存在します。"))
        return name


class StockMovementForm(forms.ModelForm):
    """
    在庫の入出庫を記録するためのフォーム。
    """
    class Meta:
        model = StockMovement
        fields = ['stock_object', 'quantity', 'notes', 'drawer_involved']
        labels = {
            'stock_object': _('在庫品目'),
            'quantity': _('数量'),
            'notes': _('備考'),
            'drawer_involved': _('関連する引き出し'),
        }
        help_texts = {
            'drawer_involved': _('出庫または入庫を行った引き出しを選択してください（該当する場合）。'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        if self.society:
            self.fields['stock_object'].queryset = StockObject.objects.filter(society=self.society)
            self.fields['drawer_involved'].queryset = Drawer.objects.filter(society=self.society)

            # Societyが引き出し管理を許可していない場合、drawer_involvedフィールドを非表示にする
            if not self.society.can_manage_drawers:
                self.fields['drawer_involved'].widget = forms.HiddenInput()
                self.fields['drawer_involved'].required = False
            else:
                self.fields['drawer_involved'].empty_label = _("引き出しを選択 (オプション)")


class ObjectUserForm(forms.ModelForm):
    """
    オブジェクトユーザー（在庫品目を使用する人/部署）を追加・編集するためのフォーム。
    """
    class Meta:
        model = ObjectUser
        fields = ['name', 'contact_info', 'notes']
        labels = {
            'name': _('ユーザー名/部署名'),
            'contact_info': _('連絡先情報'),
            'notes': _('備考'),
        }
        help_texts = {
            'name': _('プロジェクト名、顧客名など、在庫を使用するエンティティの名前。'),
            'contact_info': _('このオブジェクトユーザーの連絡先情報。'),
            'notes': _('このオブジェクトユーザーに関する詳細情報やメモ。'),
        }

    def __init__(self, *args, **kwargs):
        # Viewから渡される society インスタンスを取得
        self.society = kwargs.pop('society', None) # <-- Ensure this is being popped and stored
        super().__init__(*args, **kwargs)

        # Bootstrapクラスを適用
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['contact_info'].widget.attrs.update({'class': 'form-control'})
        self.fields['notes'].widget.attrs.update({'class': 'form-control', 'rows': 4})

    def clean_name(self):
        name = self.cleaned_data['name']

        # --- CRITICAL FIX HERE ---
        # Always use the society instance passed to the form's __init__ for validation context.
        # This 'self.society' is guaranteed to be available for both create and update operations.
        society_for_validation = self.society

        if not society_for_validation:
            # This should ideally not happen if get_form_kwargs is properly implemented
            raise forms.ValidationError(_("社会情報が見つかりません。フォームが正しく初期化されていません。"))

        # 同じ society 内で name の重複をチェック
        # Use society_for_validation here
        queryset = ObjectUser.objects.filter(society=society_for_validation, name__iexact=name) # 大文字小文字を区別しない

        # 既存のオブジェクトを更新している場合、自分自身をチェック対象から除外
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(_("このオブジェクトユーザー名は既に存在します。"))
        return name



class StockUsageForm(forms.ModelForm):
    """
    オブジェクトユーザーによる在庫品目の使用を記録するためのフォーム。
    """
    class Meta:
        model = StockUsage
        fields = ['stock_object', 'object_user', 'quantity_used', 'start_date', 'end_date', 'notes']
        labels = {
            'stock_object': _('在庫品目'),
            'object_user': _('利用ユーザー/部署'),
            'quantity_used': _('利用数量'),
            'start_date': _('利用開始日'),
            'end_date': _('利用終了日'),
            'notes': _('備考'),
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
            self.fields['stock_object'].empty_label = _("在庫品目を選択")
            self.fields['object_user'].empty_label = _("利用ユーザー/部署を選択")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', _("終了日は開始日より後でなければなりません。"))
        return cleaned_data


class RefillScheduleForm(forms.ModelForm):
    """
    在庫補充スケジュールを管理するためのフォーム。
    """
    class Meta:
        model = RefillSchedule
        fields = ['stock_object', 'scheduled_date', 'quantity_to_refill', 'notes']
        labels = {
            'stock_object': _('在庫品目'),
            'scheduled_date': _('補充予定日'),
            'quantity_to_refill': _('補充数量'),
            'notes': _('備考'),
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
            self.fields['stock_object'].queryset = StockObject.objects.filter(society=self.society, is_active=True).order_by('name')
        else:
            self.fields['stock_object'].queryset = StockObject.objects.none()

        self.fields['stock_object'].empty_label = _("在庫品目を選択")

        if self.initial_stock_object:
            self.fields['stock_object'].initial = self.initial_stock_object
            self.fields['stock_object'].widget.attrs['disabled'] = 'disabled'

    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data['scheduled_date']
        if scheduled_date and scheduled_date < date.today():
            raise forms.ValidationError(_("補充予定日は今日以降の日付でなければなりません。"))
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
    引き出しを追加・編集するためのフォーム。
    """
    class Meta:
        model = Drawer
        fields = ['cabinet_name', 'drawer_letter_x', 'drawer_number_y', 'description']
        labels = {
            'cabinet_name': _('キャビネット名'),
            'drawer_letter_x': _('引き出しの文字（X座標）'),
            'drawer_number_y': _('引き出しの番号（Y座標）'),
            'description': _('説明'),
        }
        help_texts = {
            'drawer_letter_x': _('例: A, B, C'),
            'drawer_number_y': _('例: 1, 2, 3'),
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
            # 同じ社会内で、同じキャビネット名、X座標、Y座標の引き出しが既に存在しないかチェック
            qs = Drawer.objects.filter(
                society=self.society,
                cabinet_name=cabinet_name,
                drawer_letter_x__iexact=drawer_letter_x, # 大文字小文字を区別しない
                drawer_number_y=drawer_number_y
            )
            if self.instance: # 編集の場合、自分自身を除外
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(_("この引き出しは既に存在します。別の座標を入力してください。"))
        return cleaned_data


class StockObjectDrawerPlacementForm(forms.ModelForm):
    """
    在庫品目を引き出しに配置するためのフォーム。
    """
    class Meta:
        model = StockObjectDrawerPlacement
        fields = ['stock_object', 'drawer', 'quantity']
        labels = {
            'stock_object': _('在庫品目'),
            'drawer': _('引き出し'),
            'quantity': _('数量'),
        }
        help_texts = {
            'quantity': _('この引き出しに配置する在庫品目の数量。'),
        }

    def __init__(self, *args, **kwargs):
        self.society = kwargs.pop('society', None)
        super().__init__(*args, **kwargs)
        if self.society:
            self.fields['stock_object'].queryset = StockObject.objects.filter(society=self.society)
            self.fields['drawer'].queryset = Drawer.objects.filter(society=self.society)
            self.fields['stock_object'].empty_label = _("在庫品目を選択")
            self.fields['drawer'].empty_label = _("引き出しを選択")

    def clean(self):
        cleaned_data = super().clean()
        stock_object = cleaned_data.get('stock_object')
        drawer = cleaned_data.get('drawer')
        quantity = cleaned_data.get('quantity')

        if stock_object and drawer:
            # 同じ在庫品目と引き出しの組み合わせが既に存在しないかチェック
            qs = StockObjectDrawerPlacement.objects.filter(
                stock_object=stock_object,
                drawer=drawer
            )
            if self.instance: # 編集の場合、自分自身を除外
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(_("この在庫品目は、この引き出しに既に割り当てられています。既存の割り当てを編集してください。"))

        # 配置しようとする数量が在庫品の現在の数量を超えていないか（新規作成時のみの簡易チェック）
        # より厳密なチェックはビューでトランザクション内で行うべき
        if stock_object and quantity is not None and quantity > stock_object.current_quantity:
            self.add_error('quantity', _("引き出しに配置する数量は、在庫の現在の数量を超えることはできません。(現在の在庫: %(current)s個)") % {'current': stock_object.current_quantity})

        return cleaned_data


class SocietySettingsForm(forms.ModelForm):
    """
    社会ごとの設定（引き出し管理の有効化/無効化など）を更新するフォーム。
    """
    class Meta:
        model = Society
        fields = ['can_manage_drawers', 'shows_drawers_in_list', 'subscription_level']
        labels = {
            'can_manage_drawers': _('引き出し管理を有効にする'),
            'shows_drawers_in_list': _('在庫リストに引き出し情報を表示する'),
            'subscription_level': _('サブスクリプションレベル'),
        }
        help_texts = {
            'can_manage_drawers': _('このオプションを有効にすると、在庫品目を個々の引き出しに割り当てることができます。'),
            'shows_drawers_in_list': _('有効にすると、在庫リストで各品目の引き出し配置情報が表示されます。'),
            'subscription_level': _('社会の現在のサブスクリプションレベルです。管理者によってのみ変更可能です。'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply Bootstrap's form-check-input class to checkboxes
        for field_name in ['can_manage_drawers', 'shows_drawers_in_list']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-check-input'})

        # --- CHANGES for subscription_level to be editable ---
        if 'subscription_level' in self.fields:
            # Remove readonly/plaintext styling. It will now be a standard select dropdown.
            # Add a Bootstrap class for select elements
            self.fields['subscription_level'].widget.attrs.update({'class': 'form-control'})

        # Feature disabling logic in the __init__ remains based on the *instance's current* level
        # This will visually disable features if the page is loaded with a certain plan.
        # However, the `clean_` methods will enforce rules based on the *submitted* plan.
        if self.instance:
            if self.instance.subscription_level == 'free':
                if 'can_manage_drawers' in self.fields:
                    self.fields['can_manage_drawers'].widget.attrs['disabled'] = 'disabled'
                    self.fields['can_manage_drawers'].help_text += " " + _("無料プランではこの機能は利用できません。アップグレードしてください。")

                if 'shows_drawers_in_list' in self.fields:
                    self.fields['shows_drawers_in_list'].widget.attrs['disabled'] = 'disabled'
                    self.fields['shows_drawers_in_list'].help_text += " " + _("無料プランではこの機能は利用できません。アップグレードしてください。")

            elif self.instance.subscription_level == 'basic':
                 if 'shows_drawers_in_list' in self.fields:
                    self.fields['shows_drawers_in_list'].widget.attrs['disabled'] = 'disabled'
                    self.fields['shows_drawers_in_list'].help_text += " " + _("この機能はプレミアムプランでのみ利用可能です。")

    def clean_can_manage_drawers(self):
        can_manage_drawers = self.cleaned_data.get('can_manage_drawers')
        # Crucial: Check against the *submitted* (new) subscription level
        submitted_subscription_level = self.cleaned_data.get('subscription_level')

        if can_manage_drawers and submitted_subscription_level == 'free':
            raise forms.ValidationError(
                _("選択されたプランでは「引き出し管理」機能を利用できません。")
            )
        return can_manage_drawers

    def clean_shows_drawers_in_list(self):
        shows_drawers_in_list = self.cleaned_data.get('shows_drawers_in_list')
        # Crucial: Check against the *submitted* (new) subscription level
        submitted_subscription_level = self.cleaned_data.get('subscription_level')

        if shows_drawers_in_list and submitted_subscription_level == 'free':
            raise forms.ValidationError(
                _("選択されたプランでは「在庫リストに引き出し情報を表示」機能は利用できません。")
            )
        if shows_drawers_in_list and submitted_subscription_level == 'basic':
            raise forms.ValidationError(
                _("選択されたプランではこの機能はプレミアムプランでのみ利用可能です。")
            )
        return shows_drawers_in_list

    # No custom clean_subscription_level method needed if you want it to be editable and save directly.
    # Django's ModelForm will handle saving the selected choice.