from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.db.models import Sum, F, ExpressionWrapper, fields
from datetime import date, timedelta
from django.contrib.auth import login as auth_login
from django.contrib.auth import get_user_model
from .forms import (
    SocietyRegistrationForm, CustomAuthenticationForm, StockObjectForm,
    StockMovementForm, StockUsageForm, RefillScheduleForm,
    DrawerForm, StockObjectDrawerPlacementForm, SocietySettingsForm,
    StockObjectKindForm, ObjectUserForm,UserCreateForm,UserUpdateForm
)
from .models import (
    Society, User, StockObjectKind, StockObject, Drawer, StockObjectDrawerPlacement,
    StockMovement, ObjectUser, StockUsage, RefillSchedule
)

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

class UserManagementMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    ユーザーがログインしており、かつ society_admin であることを確認するMixin。
    また、アクションがユーザー自身の社会の範囲内であることを保証します。
    """
    login_url = reverse_lazy('stock_service:custom_login_stock_service') # ログインURL

    def test_func(self):
        # ユーザーが認証済みで社会管理者である場合にTrueを返す
        return self.request.user.is_authenticated and self.request.user.is_society_admin

    def get_queryset(self):
        # 現在の社会に属するユーザーのみをクエリ
        if self.request.user.is_authenticated and self.request.user.is_society_admin:
            return User.objects.filter(society=self.request.user.society).order_by('username')
        return User.objects.none() # 権限がない場合は空のクエリセットを返す

class UserListView(UserManagementMixin, ListView):
    model = User
    template_name = 'stock_service/user_list.html'
    context_object_name = 'users'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated and self.request.user.society:
            society = self.request.user.society
            # 現在の社会のユーザーと管理者の数を取得
            total_users_count = User.objects.filter(society=society).count()
            admin_users_count = User.objects.filter(society=society, is_society_admin=True).count()

            context['total_users_count'] = total_users_count
            context['admin_users_count'] = admin_users_count
            # 社会のプランから最大許容数を取得
            context['max_admins'] = society.get_max_admins()
            context['max_users'] = society.get_max_users()
            # 表示用に社会のサブスクリプションレベルの表示名を取得
            context['current_society_subscription_display'] = society.get_subscription_level_display()
        else:
            # フォールバック (Mixinsによって通常はここに到達しないはず)
            context['total_users_count'] = 0
            context['admin_users_count'] = 0
            context['max_admins'] = 0
            context['max_users'] = 0
            context['current_society_subscription_display'] = _("N/A")

        return context


class UserCreateView(UserManagementMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'stock_service/user_form.html'
    success_url = reverse_lazy('stock_service:user_list')

    def get_form_kwargs(self):
        # フォームに society インスタンスを渡す
        kwargs = super().get_form_kwargs()
        kwargs['society'] = self.request.user.society
        return kwargs

    def form_valid(self, form):
        # フォームから保存されるユーザーの society を自動的に設定
        new_user = form.save(commit=False)
        new_user.society = self.request.user.society
        new_user.save()
        messages.success(self.request, _("ユーザー '%(username)s' が作成されました。") % {'username': new_user.username})
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("新しいユーザーを追加")
        return context


class UserUpdateView(UserManagementMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'stock_service/user_form.html'
    success_url = reverse_lazy('stock_service:user_list')
    context_object_name = 'user_obj' # テンプレートでの変数名 (request.userとの衝突を避ける)

    def get_form_kwargs(self):
        # フォームに society インスタンスと元の is_society_admin 値を渡す
        kwargs = super().get_form_kwargs()
        kwargs['society'] = self.request.user.society
        # 更新対象のユーザーの society_admin ステータスをフォームに渡す (バリデーションで使用)
        if self.object: # self.object は現在更新中のUserインスタンス
            kwargs['original_is_society_admin'] = self.object.is_society_admin
        return kwargs

    # views.py
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ユーザーの編集")

        if self.object:
            # Only show stock usages logged by this user
            context['stock_usages'] = self.object.logged_usages.all().order_by('-start_date')[:10]
            context['show_usage_history'] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, _("ユーザー '%(username)s' が更新されました。") % {'username': form.instance.username})
        return super().form_valid(form)


class UserDeleteView(UserManagementMixin, DeleteView):
    model = User
    template_name = 'stock_service/user_confirm_delete.html'
    success_url = reverse_lazy('stock_service:user_list')
    context_object_name = 'user_obj' # テンプレートでの変数名

    def form_valid(self, form):
        # 削除前のユーザー名をメッセージに含めるため、ここで取得
        username = self.object.username
        messages.success(self.request, _("ユーザー '%(username)s' が削除されました。") % {'username': username})
        return super().form_valid(form)

def register_society_stock_service(request):
    """
    新しい社会（組織）の登録ページビュー
    """
    if request.method == 'POST':
        form = SocietyRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                society = form.save()
                messages.success(request, _('社会 "%(society_name)s" が正常に登録されました。管理者アカウントを作成してください。') % {'society_name': society.name})
                return redirect(reverse('stock_service:custom_login_stock_service')) # 登録後、ログインページへリダイレクト
        else:
            messages.error(request, _('社会の登録に失敗しました。フォームの入力内容を確認してください。'))
    else:
        form = SocietyRegistrationForm()
    return render(request, 'stock_service/register_society.html', {'form': form, 'title': _('新しい社会を登録')})

def custom_login_stock_service(request):
    """
    カスタムログインビュー。社会名、ユーザー名、パスワードを要求する。
    """
    if request.user.is_authenticated:
        return redirect(reverse('stock_service:app_home_stock_service'))

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            society_name = form.cleaned_data.get('society_name')
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # 新しいSocietyAuthBackendに社会名も渡して認証を試みる
            user = authenticate(request, username=username, password=password, society_name=society_name)

            if user is not None:
                # 【重要】: スーパーユーザーまたは is_staff フラグを持つユーザーを識別
                is_admin_or_superuser = user.is_superuser or user.is_staff
                
                # 通常ユーザーのみ society の関連付けをチェックする
                if not is_admin_or_superuser:
                    # カスタムユーザーで society が設定されていない場合はエラーとする
                    if not hasattr(user, 'society') or user.society is None:
                        messages.error(request, _('あなたのアカウントは社会に関連付けられていません。管理者にお問い合わせください。'))
                        return render(request, 'stock_service/custom_login.html', {'form': form, 'title': _('ログイン')})
                
                # ユーザーが認証されたら、ログイン処理
                login(request, user)
                messages.success(request, _('ようこそ、%(username)sさん！') % {'username': user.username})
                return redirect(reverse('stock_service:app_home_stock_service'))
            else:
                messages.error(request, _('無効なユーザー名、パスワード、または社会です。'))
        else:
            # フォームのバリデーションエラーメッセージを表示
            for field_name, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field_name].label if field_name in form.fields else field_name
                    messages.error(request, f"{label}: {error}")
    else:
        form = CustomAuthenticationForm()

    return render(request, 'stock_service/custom_login.html', {'form': form, 'title': _('ログイン')})

User = get_user_model()

@login_required(login_url='stock_service:custom_login_stock_service')
def user_profile_view(request):
    """
    Display user profile information
    """
    user = request.user

    # Get user's additional information
    context = {
        'title': 'プロフィール', # This title is still used by app_base.html
        'user': user, # The user object itself is needed for groups/permissions
        'user_info': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        }
    }

    # Add society information if available
    if hasattr(user, 'society'):
        context['society_info'] = {
            'name': user.society.name,
            'can_manage_drawers': getattr(user.society, 'can_manage_drawers', False),
            'is_society_admin': getattr(user, 'is_society_admin', False),
        }

    return render(request, 'stock_service/user_profile.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def custom_logout_stock_service(request):
    """
    カスタムログアウトビュー。
    """
    logout(request)
    messages.info(request, _('ログアウトしました。'))
    return redirect(reverse('stock_service:custom_login_stock_service'))

@login_required(login_url='stock_service:custom_login_stock_service')
def app_home_stock_service(request):
    """
    アプリケーションのホームビュー。
    ログインユーザーの社会に紐づく情報を表示するダッシュボード。
    """
    # Check if user has society attribute and it's not None
    if not hasattr(request.user, 'society') or request.user.society is None:
        messages.error(request, _("あなたのアカウントは社会に関連付けられていません。管理者にお問い合わせください。"))
        logout(request)  # Log out the user since their account is incomplete
        return redirect('stock_service:custom_login_stock_service')

    society = request.user.society

    # Rest of your existing code remains the same
    total_stock_objects = StockObject.objects.filter(society=society).count()
    low_stock_objects = StockObject.objects.filter(
        society=society,
        current_quantity__lt=F('minimum_quantity')
    ).count()
    recent_movements = StockMovement.objects.filter(society=society).order_by('-timestamp')[:5]
    upcoming_refills = RefillSchedule.objects.filter(
        society=society,
        is_completed=False,
        scheduled_date__gte=date.today()
    ).order_by('scheduled_date')[:5]

    context = {
        'society': society,
        'total_stock_objects': total_stock_objects,
        'low_stock_objects': low_stock_objects,
        'recent_movements': recent_movements,
        'upcoming_refills': upcoming_refills,
        'title': _('ダッシュボード')
    }
    return render(request, 'stock_service/app_home.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def stock_object_list_stock_service(request):
    """
    在庫品目リストを表示するビュー。
    社会が引き出し管理を有効にしている場合、引き出し情報も表示。
    """
    society = request.user.society
    stock_objects = StockObject.objects.filter(society=society).order_by('name')

    if society.can_manage_drawers and society.shows_drawers_in_list:
        # 引き出し情報も表示する場合
        # 各StockObjectに紐づく引き出し情報を取得
        for obj in stock_objects:
            obj.drawer_info = obj.drawer_placements.select_related('drawer').all()

    context = {
        'stock_objects': stock_objects,
        'society': society,
        'title': _('在庫品目リスト'),
        'can_manage_drawers': society.can_manage_drawers,
        'shows_drawers_in_list': society.shows_drawers_in_list,
    }
    return render(request, 'stock_service/stock_object_list.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def stock_object_detail_stock_service(request, pk):
    """
    個々の在庫品目の詳細を表示するビュー。
    """
    society = request.user.society
    stock_object = get_object_or_404(StockObject, pk=pk, society=society)
    movements = StockMovement.objects.filter(stock_object=stock_object).order_by('-timestamp')[:10]
    usages = StockUsage.objects.filter(stock_object=stock_object).order_by('-start_date')[:10]
    refills = RefillSchedule.objects.filter(stock_object=stock_object).order_by('scheduled_date')[:10]

    drawer_placements = None
    if society.can_manage_drawers:
        drawer_placements = StockObjectDrawerPlacement.objects.filter(stock_object=stock_object).select_related('drawer')

    context = {
        'stock_object': stock_object,
        'movements': movements,
        'usages': usages,
        'refills': refills,
        'drawer_placements': drawer_placements,
        'society': society,
        'title': _('%(object_name)s の詳細') % {'object_name': stock_object.name}
    }
    return render(request, 'stock_service/stock_object_detail.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def stock_out_stock_service(request):
    """
    在庫品目の出庫を記録するビュー。
    """
    society = request.user.society
    if request.method == 'POST':
        form = StockMovementForm(request.POST, society=society)
        if form.is_valid():
            stock_movement = form.save(commit=False)
            stock_movement.society = society
            stock_movement.movement_type = 'out'
            stock_movement.moved_by = request.user

            stock_object = stock_movement.stock_object
            quantity = stock_movement.quantity
            drawer_involved = stock_movement.drawer_involved

            if stock_object.current_quantity >= quantity:
                with transaction.atomic():
                    stock_object.current_quantity -= quantity
                    stock_object.save()

                    if society.can_manage_drawers and drawer_involved:
                        # 引き出しから数量を減らす
                        placement, created = StockObjectDrawerPlacement.objects.get_or_create(
                            stock_object=stock_object,
                            drawer=drawer_involved,
                            defaults={'quantity': 0}
                        )
                        if placement.quantity >= quantity:
                            placement.quantity -= quantity
                            placement.save()
                        else:
                            transaction.set_rollback(True)
                            messages.error(request, _('指定された引き出しには、出庫しようとしている数量の品目がありません。'))
                            return render(request, 'stock_service/stock_out.html', {'form': form, 'title': _('在庫出庫')})

                    stock_movement.save()
                    messages.success(request, _('%(quantity)s個の%(stock_object_name)sが出庫されました。') % {'quantity': quantity, 'stock_object_name': stock_object.name})
                    if society.can_manage_drawers and stock_movement.drawer_involved:
                         messages.info(request, _('引き出し: %(drawer)s から出庫されました。') % {'drawer': stock_movement.drawer_involved})
                    return redirect(reverse('stock_service:stock_movement_log_stock_service'))
            else:
                messages.error(request, _('出庫しようとしている数量は、現在の在庫数量よりも多いです。現在の在庫: %(current)s個') % {'current': stock_object.current_quantity})
        else:
            messages.error(request, _('出庫の記録に失敗しました。フォームの入力内容を確認してください。'))
    else:
        form = StockMovementForm(society=society)
    return render(request, 'stock_service/stock_out.html', {'form': form, 'title': _('在庫出庫')})

@login_required(login_url='stock_service:custom_login_stock_service')
def stock_in_stock_service(request):
    """
    在庫品目の入庫を記録するビュー。
    """
    society = request.user.society
    if request.method == 'POST':
        form = StockMovementForm(request.POST, society=society)
        if form.is_valid():
            stock_movement = form.save(commit=False)
            stock_movement.society = society
            stock_movement.movement_type = 'in'
            stock_movement.moved_by = request.user

            stock_object = stock_movement.stock_object
            quantity = stock_movement.quantity
            drawer_involved = stock_movement.drawer_involved

            with transaction.atomic():
                stock_object.current_quantity += quantity
                stock_object.save()

                if society.can_manage_drawers and drawer_involved:
                    # 引き出しに数量を追加または更新
                    placement, created = StockObjectDrawerPlacement.objects.get_or_create(
                        stock_object=stock_object,
                        drawer=drawer_involved,
                        defaults={'quantity': 0}
                    )
                    placement.quantity += quantity
                    placement.save()

                stock_movement.save()
                messages.success(request, _('%(quantity)s個の%(stock_object_name)sが入庫されました。') % {'quantity': quantity, 'stock_object_name': stock_object.name})
                if society.can_manage_drawers and stock_movement.drawer_involved:
                     messages.info(request, _('引き出し: %(drawer)s に入庫されました。') % {'drawer': stock_movement.drawer_involved})
                return redirect(reverse('stock_service:stock_movement_log_stock_service'))
        else:
            messages.error(request, _('入庫の記録に失敗しました。フォームの入力内容を確認してください。'))
    else:
        form = StockMovementForm(society=society)
    return render(request, 'stock_service/stock_in.html', {'form': form, 'title': _('在庫入庫')})

@login_required(login_url='stock_service:custom_login_stock_service')
def stock_movement_log_stock_service(request):
    """
    在庫の移動履歴を表示するビュー。
    """
    society = request.user.society
    movements = StockMovement.objects.filter(society=society).order_by('-timestamp')
    context = {
        'movements': movements,
        'title': _('在庫移動履歴'),
    }
    return render(request, 'stock_service/stock_movement_log.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def object_user_usage_log_stock_service(request):
    """
    オブジェクトユーザーによる在庫使用ログを表示するビュー。
    """
    society = request.user.society
    usages = StockUsage.objects.filter(society=society).order_by('-logged_at')
    context = {
        'usages': usages,
        'title': _('オブジェクトユーザー使用ログ'),
    }
    return render(request, 'stock_service/object_user_usage_log.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def add_stock_usage_stock_service(request):
    """
    オブジェクトユーザーによる在庫使用を記録するビュー。
    """
    society = request.user.society
    if request.method == 'POST':
        form = StockUsageForm(request.POST, society=society)
        if form.is_valid():
            stock_usage = form.save(commit=False)
            stock_usage.society = society
            stock_usage.logged_by = request.user

            with transaction.atomic():
                # StockObjectの数量を減らす
                stock_object = stock_usage.stock_object
                if stock_object.current_quantity >= stock_usage.quantity_used:
                    stock_object.current_quantity -= stock_usage.quantity_used
                    stock_object.save()
                    stock_usage.save()
                    messages.success(request, _('%(quantity)s個の%(stock_object_name)sの利用が記録されました。') % {'quantity': stock_usage.quantity_used, 'stock_object_name': stock_object.name})
                    return redirect(reverse('stock_service:object_user_usage_log_stock_service'))
                else:
                    messages.error(request, _('利用しようとしている数量は、現在の在庫数量よりも多いです。現在の在庫: %(current)s個') % {'current': stock_object.current_quantity})
        else:
            messages.error(request, _('利用履歴の記録に失敗しました。フォームの入力内容を確認してください。'))
    else:
        form = StockUsageForm(society=society)
    context = {
        'form': form,
        'title': _('利用履歴を記録'),
    }
    return render(request, 'stock_service/add_stock_usage.html', context)


@login_required(login_url='stock_service:custom_login_stock_service')
def refill_prediction_stock_service(request, stock_object_pk=None):
    """
    在庫補充のタイミングを予測するビュー。
    過去の使用データに基づき、平均消費量や補充日を概算。
    アラート機能を追加。
    """
    society = request.user.society
    predictions_list = []

    for stock_object_item in StockObject.objects.filter(society=society, is_active=True).order_by('name'):
        ninety_days_ago = date.today() - timedelta(days=90)
        total_used_in_90_days = StockUsage.objects.filter(
            society=society,
            stock_object=stock_object_item,
            logged_at__gte=ninety_days_ago
        ).aggregate(total_quantity=Sum('quantity_used'))['total_quantity'] or 0

        predicted_refill_date = _('データ不足')
        daily_usage = 0
        days_until_empty = float('inf') # Initialize as infinity, for items that won't run out soon
        alert_message = None

        if total_used_in_90_days > 0:
            daily_usage = total_used_in_90_days / 90.0

            if daily_usage > 0:
                if stock_object_item.current_quantity > 0:
                    days_until_empty = stock_object_item.current_quantity / daily_usage
                    predicted_refill_date = date.today() + timedelta(days=int(days_until_empty)) # Cast to int for timedelta

                # --- ALERT CONDITION 1: Based on calculated days_until_empty (if daily_usage > 0) ---
                if stock_object_item.current_quantity <= 0: # Explicitly check for zero or negative stock
                    predicted_refill_date = _('即時補充が必要')
                    alert_message = _('**在庫ゼロ:** 即時補充が必要です！')
                elif days_until_empty <= 7:
                    predicted_refill_date = date.today() + timedelta(days=int(days_until_empty)) # Re-calculate for display
                    alert_message = _('**緊急補充必要:** 現在の消費ペースでは%s日以内に在庫がなくなります。') % int(days_until_empty)
                elif days_until_empty <= 14:
                    predicted_refill_date = date.today() + timedelta(days=int(days_until_empty)) # Re-calculate for display
                    alert_message = _('**早期補充検討:** 現在の消費ペースでは2週間以内に在庫がなくなります。')
                # No 'else' needed here for alert_message, as it defaults to None

            else: # daily_usage is 0 despite total_used_in_90_days > 0 (usage stopped or negligible)
                predicted_refill_date = _('利用が検出されません (消費停止)')
                # If usage detected previously but now zero, and stock is low
                if stock_object_item.current_quantity <= stock_object_item.minimum_quantity:
                    alert_message = _('**低在庫:** 使用履歴はあるものの、現在の消費ペースでは補充予測できません。')

        else: # total_used_in_90_days == 0 (No usage in last 90 days)
            predicted_refill_date = _('利用が検出されません') # default for no usage

            # --- ALERT CONDITION 4: No usage, but stock is below minimum ---
            if stock_object_item.current_quantity <= stock_object_item.minimum_quantity:
                # If no usage, but current stock is below minimum, it still needs attention
                predicted_refill_date = _('最低在庫量を下回っています')
                alert_message = _('**低在庫 (利用なし):** 過去90日間の利用はありませんが、最低在庫量を下回っています。')
            # If no usage and stock is NOT low, no alert_message (remains None)

        predictions_list.append({
            'stock_object': stock_object_item,
            'current_quantity': stock_object_item.current_quantity,
            'minimum_quantity': stock_object_item.minimum_quantity,
            'total_used_in_90_days': total_used_in_90_days,
            'daily_usage': f"{daily_usage:.2f}",
            'predicted_refill_date': predicted_refill_date,
            'needs_refill': stock_object_item.current_quantity <= stock_object_item.minimum_quantity,
            'alert_message': alert_message,
        })

    # Sort predictions (put items needing immediate attention first)
    # The sorting key has been improved for better order of alerts
    predictions_list.sort(key=lambda x: (
        # 1. Critical alerts first
        x['alert_message'] is not None and ('緊急補充必要' in str(x['alert_message']) or '在庫ゼロ' in str(x['alert_message'])), # True comes first
        # 2. Other alerts next
        x['alert_message'] is not None, # True comes before False (no alert)
        # 3. Then items that are below minimum quantity (even without a specific alert message)
        x['needs_refill'] is True, # True comes before False
        # 4. For items with a predicted date, sort by date (earliest first)
        isinstance(x['predicted_refill_date'], date) and x['predicted_refill_date'] or date.max,
        # 5. Fallback sort by stock object name
        x['stock_object'].name
    ), reverse=True) # Sort in reverse to get critical items at the top

    context = {
        'predictions': predictions_list,
        'title': _('在庫補充予測'),
    }
    return render(request, 'stock_service/refill_prediction.html', context)


@login_required(login_url='stock_service:custom_login_stock_service')
def refill_scheduler_stock_service(request, stock_object_pk=None):
    """
    補充スケジューラーのビュー。
    特定の在庫品目に関連付けられた補充注文の作成・管理を可能にする。
    GET: 補充スケジュール作成フォームを表示
    POST: フォームを処理し、補充スケジュールを作成
    """
    society = request.user.society
    stock_object_from_url = None # Renamed to clearly indicate it came from the URL parameter

    # Keyword arguments to pass to the form's __init__ method
    form_init_kwargs = {'society': society}

    if stock_object_pk:
        stock_object_from_url = get_object_or_404(StockObject, pk=stock_object_pk, society=society)
        form_init_kwargs['initial_stock_object'] = stock_object_from_url # Pass this to the form

    if request.method == 'POST':
        form = RefillScheduleForm(request.POST, **form_init_kwargs)
        if form.is_valid():
            refill_schedule = form.save(commit=False)
            refill_schedule.society = society # Assign the current user's society
            refill_schedule.save()
            messages.success(request, _('補充スケジュールが正常に作成されました。'))
            # Redirect to the general refill scheduler view to see the new entry in the list
            return redirect('stock_service:refill_scheduler_stock_service_general')
        else:
            messages.error(request, _('補充スケジュールの作成に失敗しました。フォームのエラーを確認してください。'))
    else: # GET request
        form = RefillScheduleForm(**form_init_kwargs)

    # Fetch existing refill schedules for the current society for display
    # Consider pagination if you expect many schedules
    existing_schedules = RefillSchedule.objects.filter(society=society).order_by('scheduled_date', 'stock_object__name')

    context = {
        'form': form,
        'stock_object': stock_object_from_url, # Pass the specific stock_object if it came from the URL
        'existing_schedules': existing_schedules, # List of all existing schedules
        'title': _('補充スケジューラー'),
    }
    return render(request, 'stock_service/refill_scheduler.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def complete_refill_stock_service(request, pk):
    """
    補充スケジュールを完了としてマークするビュー。
    実際に在庫数量を増加させる。
    """
    society = request.user.society
    schedule = get_object_or_404(RefillSchedule, pk=pk, society=society)

    if request.method == 'POST' and not schedule.is_completed:
        with transaction.atomic():
            schedule.is_completed = True
            schedule.completed_date = date.today()
            schedule.save()

            # 在庫品目の数量を増加させる
            stock_object = schedule.stock_object
            stock_object.current_quantity += schedule.quantity_to_refill
            stock_object.save()

            # StockMovement にも記録
            StockMovement.objects.create(
                society=society,
                stock_object=stock_object,
                movement_type='in',
                quantity=schedule.quantity_to_refill,
                moved_by=request.user,
                notes=_('補充スケジュールからの自動入庫 (ID: %(schedule_id)s)') % {'schedule_id': schedule.pk}
            )
            messages.success(request, _('補充スケジュールが完了し、%(quantity)s個の%(object_name)sが在庫に追加されました。') % {'quantity': schedule.quantity_to_refill, 'object_name': stock_object.name})
    elif schedule.is_completed:
        messages.warning(request, _('この補充スケジュールは既に完了済みです。'))
    else:
        messages.error(request, _('無効なリクエストです。'))

    return redirect(reverse('stock_service:refill_scheduler_stock_service_general'))


def get_subscription_choices():
    return Society._meta.get_field('subscription_level').choices


def pricing_stock_service(request):
    """
    Display the pricing plans page.
    """
    free_features = [
        _("組み込み在庫管理"),
        _("ユーザー管理 (最大5人)"),
        _("基本レポート"),
        _("メールサポート (限定的)"),
    ]

    basic_features = [
        _("組み込み在庫管理"),
        _("ユーザー管理 (最大50人)"),
        _("高度なレポート"),
        _("メール・チャットサポート"),
        _("オブジェクトユーザー利用ログ"),
        _("補充予測"),
    ]

    premium_features = [
        _("組み込み在庫管理"),
        _("無制限のユーザー管理"),
        _("包括的なレポート"),
        _("メール・チャット・電話サポート"),
        _("オブジェクトユーザー利用ログ"),
        _("補充予測"),
        _("引き出し管理"),
        _("社会ごとの管理者アクセス"),
        _("優先サポート"),
    ]


    current_plan_code = None # Initialize as None. Anonymous users won't have a specific plan.
    if request.user.is_authenticated and hasattr(request.user, 'society') and request.user.society:
        request.user.refresh_from_db() # Ensure the user object and related society are fresh
        current_plan_code = request.user.society.subscription_level if hasattr(request.user, 'society') else 'free'
    context = {
        'free_features': free_features,
        'basic_features': basic_features,
        'premium_features': premium_features,

        'current_plan': current_plan_code, # Pass the plan code
        'SUBSCRIPTION_CHOICES_DICT': dict(get_subscription_choices()) # Pass for lookup in template if needed
    }
    return render(request, 'stock_service/pricing.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def fake_payment_view(request):
    """
    A dummy view to simulate a payment page and update society's subscription.
    Handles both upgrades and downgrades.
    """
    selected_plan = request.GET.get('plan') # Get the plan from URL parameter

    # Get valid choices directly from the model field for validation
    valid_subscription_choices = [choice[0] for choice in get_subscription_choices()]

    if selected_plan in valid_subscription_choices:
        try:
            if not hasattr(request.user, 'society') or not request.user.society:
                messages.error(request, _("ユーザーは社会に所属していません。"))
                return redirect(reverse('stock_service:pricing_stock_service'))

            society = request.user.society

            # Check if the selected plan is actually a change
            if society.subscription_level != selected_plan:
                society.subscription_level = selected_plan

                # --- Downgrade/Upgrade Feature Adjustment Logic ---
                # This ensures features are automatically disabled if the new plan doesn't support them.
                if selected_plan == 'free':
                    society.can_manage_drawers = False
                    society.shows_drawers_in_list = False
                elif selected_plan == 'basic':
                    society.shows_drawers_in_list = False

                society.save()
                messages.success(request, _("プランが %(plan)s に変更されました！") % {'plan': society.get_subscription_level_display()})
            else:
                messages.info(request, _("すでに %(plan)s プランをご利用中です。") % {'plan': society.get_subscription_level_display()})

        except Exception as e:
            messages.error(request, _("プランの変更中にエラーが発生しました: %(error)s") % {'error': str(e)})
    else:
        messages.error(request, _("無効なプランが選択されました。"))

    return redirect(reverse('stock_service:pricing_stock_service')) # Redirect will cause a fresh request and user object reload
    # Added refresh_from_db() to pricing_view directly to ensure it gets the latest data.

@login_required(login_url='stock_service:custom_login_stock_service')
def society_settings_stock_service(request):
    """
    社会ごとの設定を管理するビュー。
    特に引き出し管理オプション。
    """
    society = request.user.society
    if not request.user.is_society_admin:
        messages.error(request, _('このページにアクセスする権限がありません。'))
        return redirect(reverse('stock_service:app_home_stock_service'))

    if request.method == 'POST':
        form = SocietySettingsForm(request.POST, instance=society)
        if form.is_valid():
            form.save()
            messages.success(request, _('社会設定が正常に更新されました。'))
            return redirect(reverse('stock_service:society_settings_stock_service'))
        else:
            messages.error(request, _('社会設定の更新に失敗しました。フォームの入力内容を確認してください。'))
    else:
        form = SocietySettingsForm(instance=society)

    context = {
        'form': form,
        'title': _('社会設定'),
        'society': society,
        'current_subscription_plan': society.get_subscription_level_display(), # Human-readable plan name
        'subscription_code': society.subscription_level, # The code ('free', 'basic', 'premium')
    }
    return render(request, 'stock_service/society_settings.html', context)

class DrawerManagementMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin to ensure user is logged in and is a society admin.
    Also checks if drawer management is enabled for the society.
    Ensures actions are within their society.
    """
    login_url = reverse_lazy('stock_service:custom_login_stock_service')

    def test_func(self):
        # 社会管理者であり、かつ引き出し管理が有効な社会に属している場合にアクセスを許可
        if not self.request.user.is_authenticated or not self.request.user.is_society_admin:
            return False

        # Societyにcan_manage_drawersが設定されているか確認
        if not hasattr(self.request.user, 'society') or not self.request.user.society:
            messages.error(self.request, _("社会情報が見つかりません。"))
            return False

        if not self.request.user.society.can_manage_drawers:
            messages.warning(self.request, _('この社会では引き出し管理機能が有効になっていません。'))
            return False
        return True

    def get_queryset(self):
        # 現在の社会に属するDrawerのみをクエリ
        if self.request.user.is_authenticated and self.request.user.society:
            return Drawer.objects.filter(society=self.request.user.society).order_by('cabinet_name', 'drawer_letter_x', 'drawer_number_y')
        return Drawer.objects.none() # 権限がない場合は空のクエリセットを返す


# 既存の関数ベースビュー manage_drawers_stock_service は、リスト表示と新規作成フォームのみを扱います。
@login_required(login_url='stock_service:custom_login_stock_service')
def manage_drawers_stock_service(request):
    """
    引き出しのリストを表示し、新しい引き出しを追加するビュー。
    """
    society = request.user.society
    if not society.can_manage_drawers:
        messages.warning(request, _('この社会では引き出し管理機能が有効になっていません。'))
        return redirect(reverse('stock_service:app_home_stock_service'))

    drawers = Drawer.objects.filter(society=society).order_by('cabinet_name', 'drawer_letter_x', 'drawer_number_y')

    if request.method == 'POST':
        # フォームに society を渡す
        form = DrawerForm(request.POST, society=society)
        if form.is_valid():
            drawer = form.save(commit=False)
            drawer.society = society
            drawer.save()
            messages.success(request, _('引き出し "%(drawer_name)s" が追加されました。') % {'drawer_name': drawer.__str__()})
            return redirect(reverse('stock_service:manage_drawers_stock_service'))
        else:
            messages.error(request, _('引き出しの追加に失敗しました。フォームの入力内容を確認してください。'))
    else:
        # フォームに society を渡す
        form = DrawerForm(society=society)

    context = {
        'drawers': drawers,
        'form': form,
        'title': _('引き出しの管理'),
        'can_manage_drawers': society.can_manage_drawers,
    }
    return render(request, 'stock_service/manage_drawers.html', context)


class DrawerUpdateView(DrawerManagementMixin, UpdateView):
    model = Drawer
    form_class = DrawerForm
    template_name = 'stock_service/drawer_form.html' # 新しいフォームテンプレート
    context_object_name = 'drawer_obj' # テンプレートでの変数名
    success_url = reverse_lazy('stock_service:manage_drawers_stock_service')

    def get_form_kwargs(self):
        # フォームに society インスタンスを渡す
        kwargs = super().get_form_kwargs()
        kwargs['society'] = self.request.user.society
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("引き出しを編集")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("引き出し '%(drawer_name)s' が正常に更新されました。") % {'drawer_name': form.instance.__str__()})
        return super().form_valid(form)


class DrawerDeleteView(DrawerManagementMixin, DeleteView):
    model = Drawer
    template_name = 'stock_service/drawer_confirm_delete.html' # 新しい削除確認テンプレート
    context_object_name = 'drawer_obj' # テンプレートでの変数名
    success_url = reverse_lazy('stock_service:manage_drawers_stock_service')

    def form_valid(self, form):
        messages.success(self.request, _("引き出し '%(drawer_name)s' が正常に削除されました。") % {'drawer_name': self.object.__str__()})
        return super().form_valid(form)

@login_required(login_url='stock_service:custom_login_stock_service')
def assign_stock_to_drawer_stock_service(request):
    """
    在庫品目を引き出しに割り当てるビュー。
    """
    society = request.user.society
    if not society.can_manage_drawers:
        messages.warning(request, _('この社会では引き出し管理機能が有効になっていません。'))
        return redirect(reverse('stock_service:app_home_stock_service'))

    if request.method == 'POST':
        form = StockObjectDrawerPlacementForm(request.POST, society=society)
        if form.is_valid():
            placement = form.save(commit=False)
            placement.save() # societyはモデルに直接紐づいていないが、フォームでフィルタリングされている
            messages.success(request, _('%(stock_object)s が %(drawer)s に割り当てられました。') % {'stock_object': placement.stock_object.name, 'drawer': placement.drawer.__str__()})
            return redirect(reverse('stock_service:stock_object_detail_stock_service', args=[placement.stock_object.pk]))
        else:
            messages.error(request, _('在庫品目の引き出しへの割り当てに失敗しました。フォームの入力内容を確認してください。'))
    else:
        form = StockObjectDrawerPlacementForm(society=society)

    context = {
        'form': form,
        'title': _('引き出しに在庫を割り当てる'),
    }
    return render(request, 'stock_service/assign_stock_to_drawer.html', context)

class StockObjectKindManagementMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin to ensure user is logged in and is a society admin.
    Ensures actions are within their society.
    """
    login_url = reverse_lazy('stock_service:custom_login_stock_service')

    def test_func(self):
        # 社会管理者のみがアクセスできる
        return self.request.user.is_authenticated and self.request.user.is_society_admin

    def get_queryset(self):
        # 現在の社会に属するStockObjectKindのみをクエリ
        if self.request.user.is_authenticated and self.request.user.is_society_admin:
            return StockObjectKind.objects.filter(society=self.request.user.society).order_by('name')
        return StockObjectKind.objects.none() # 権限がない場合は空のクエリセットを返す

@login_required(login_url='stock_service:custom_login_stock_service')
def stock_object_kind_list_stock_service(request):
    """
    在庫品目の種類のリストを表示・管理するビュー。
    新しい種類の追加もここで行う。
    """
    society = request.user.society
    kinds = StockObjectKind.objects.filter(society=society).order_by('name')

    if request.method == 'POST':
        # フォームにsocietyを渡す
        form = StockObjectKindForm(request.POST, society=society)
        if form.is_valid():
            kind = form.save(commit=False)
            kind.society = society
            kind.save()
            messages.success(request, _('在庫品目の種類 "%(name)s" が追加されました。') % {'name': kind.name})
            return redirect(reverse('stock_service:stock_object_kind_list_stock_service'))
        else:
            messages.error(request, _('在庫品目の種類の追加に失敗しました。フォームの入力内容を確認してください。'))
    else:
        # フォームにsocietyを渡す
        form = StockObjectKindForm(society=society)

    context = {
        'kinds': kinds,
        'form': form,
        'title': _('在庫品目の種類の管理'),
    }
    return render(request, 'stock_service/stock_object_kind_list.html', context)

class StockObjectKindUpdateView(StockObjectKindManagementMixin, UpdateView):
    model = StockObjectKind
    form_class = StockObjectKindForm
    template_name = 'stock_service/stock_object_kind_form.html' # 新しいフォームテンプレート
    context_object_name = 'kind_obj' # テンプレートでの変数名
    success_url = reverse_lazy('stock_service:stock_object_kind_list_stock_service')

    def get_form_kwargs(self):
        # フォームに society インスタンスを渡す
        kwargs = super().get_form_kwargs()
        kwargs['society'] = self.request.user.society
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("在庫品目の種類を編集")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("在庫品目の種類 '%(name)s' が正常に更新されました。") % {'name': form.instance.name})
        return super().form_valid(form)


class StockObjectKindDeleteView(StockObjectKindManagementMixin, DeleteView):
    model = StockObjectKind
    template_name = 'stock_service/stock_object_kind_confirm_delete.html' # 新しい削除確認テンプレート
    context_object_name = 'kind_obj' # テンプレートでの変数名
    success_url = reverse_lazy('stock_service:stock_object_kind_list_stock_service')

    def form_valid(self, form):
        messages.success(self.request, _("在庫品目の種類 '%(name)s' が正常に削除されました。") % {'name': self.object.name})
        return super().form_valid(form)

@login_required(login_url='stock_service:custom_login_stock_service')
def add_stock_object_stock_service(request):
    """
    新しい在庫品目を追加するビュー。
    """
    society = request.user.society
    if request.method == 'POST':
        form = StockObjectForm(request.POST, society=society)
        if form.is_valid():
            stock_object = form.save(commit=False)
            stock_object.society = society
            stock_object.save()
            messages.success(request, _('新しい在庫品目 "%(name)s" が追加されました。') % {'name': stock_object.name})
            return redirect(reverse('stock_service:stock_object_list_stock_service'))
        else:
            messages.error(request, _('在庫品目の追加に失敗しました。フォームの入力内容を確認してください。'))
    else:
        form = StockObjectForm(society=society)

    context = {
        'form': form,
        'title': _('新しい在庫品目を追加'),
    }
    return render(request, 'stock_service/add_stock_object.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def update_stock_object_stock_service(request, pk):
    """
    既存の在庫品目を更新するビュー。
    """
    society = request.user.society
    stock_object = get_object_or_404(StockObject, pk=pk, society=society)

    if request.method == 'POST':
        form = StockObjectForm(request.POST, instance=stock_object, society=society)
        if form.is_valid():
            form.save()
            messages.success(request, _('在庫品目 "%(name)s" が更新されました。') % {'name': stock_object.name})
            return redirect(reverse('stock_service:stock_object_detail_stock_service', args=[pk]))
        else:
            messages.error(request, _('在庫品目の更新に失敗しました。フォームの入力内容を確認してください。'))
    else:
        form = StockObjectForm(instance=stock_object, society=society)

    context = {
        'form': form,
        'stock_object': stock_object,
        'title': _('%(name)s を更新') % {'name': stock_object.name},
    }
    return render(request, 'stock_service/update_stock_object.html', context)

@login_required(login_url='stock_service:custom_login_stock_service')
def delete_stock_object_stock_service(request, pk):
    """
    在庫品目を削除するビュー。
    """
    society = request.user.society
    stock_object = get_object_or_404(StockObject, pk=pk, society=society)

    if request.method == 'POST':
        stock_object.delete()
        messages.success(request, _('在庫品目 "%(name)s" が削除されました。') % {'name': stock_object.name})
        return redirect(reverse('stock_service:stock_object_list_stock_service'))

    context = {
        'stock_object': stock_object,
        'title': _('%(name)s を削除') % {'name': stock_object.name},
    }
    return render(request, 'stock_service/confirm_delete.html', context)



class ObjectUserManagementMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin to ensure user is logged in and is a society admin.
    Also ensures actions are within their society.
    """
    login_url = reverse_lazy('stock_service:custom_login_stock_service')

    def test_func(self):
        # 社会管理者のみがアクセスできる
        return self.request.user.is_authenticated and self.request.user.is_society_admin

    def get_queryset(self):
        # 現在の社会に属するObjectUserのみをクエリ
        if self.request.user.is_authenticated and self.request.user.is_society_admin:
            return ObjectUser.objects.filter(society=self.request.user.society).order_by('name')
        return ObjectUser.objects.none() # 権限がない場合は空のクエリセットを返す

class ObjectUserListView(ObjectUserManagementMixin, ListView):
    model = ObjectUser
    template_name = 'stock_service/objectuser_list.html'
    context_object_name = 'object_users'
    paginate_by = 20 # 任意でページネーションを設定


class ObjectUserCreateView(ObjectUserManagementMixin, CreateView):
    model = ObjectUser
    form_class = ObjectUserForm
    template_name = 'stock_service/objectuser_form.html'
    success_url = reverse_lazy('stock_service:objectuser_list')

    def get_form_kwargs(self):
        # フォームに society インスタンスを渡す
        kwargs = super().get_form_kwargs()
        kwargs['society'] = self.request.user.society # <-- This line is crucial and correct
        return kwargs

    def form_valid(self, form):
        # form.instance の society フィールドを自動的に設定
        form.instance.society = self.request.user.society
        messages.success(self.request, _("オブジェクトユーザー '%(name)s' が正常に作成されました。") % {'name': form.instance.name})
        return super().form_valid(form)


class ObjectUserUpdateView(ObjectUserManagementMixin, UpdateView):
    model = ObjectUser
    form_class = ObjectUserForm
    template_name = 'stock_service/objectuser_form.html'
    success_url = reverse_lazy('stock_service:objectuser_list')
    context_object_name = 'objectuser_obj' # テンプレートでの変数名

    def get_form_kwargs(self):
        # フォームに society インスタンスを渡す (更新時も必要)
        kwargs = super().get_form_kwargs()
        kwargs['society'] = self.request.user.society # <-- This line is crucial and correct
        return kwargs


class ObjectUserDeleteView(ObjectUserManagementMixin, DeleteView):
    model = ObjectUser
    template_name = 'stock_service/objectuser_confirm_delete.html'
    success_url = reverse_lazy('stock_service:objectuser_list')
    context_object_name = 'objectuser_obj'

    def form_valid(self, form):
        messages.success(self.request, _("オブジェクトユーザー '%(name)s' が正常に削除されました。") % {'name': self.object.name})

        return super().form_valid(form)
