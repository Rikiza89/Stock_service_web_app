# stock_service/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import Society, User as CustomUser # あなたのUserモデルのエイリアス


class SocietyAuthBackend(BaseBackend):
    """
    社会名、ユーザー名、パスワードに基づいてユーザーを認証するカスタム認証バックエンド。
    """

    def authenticate(self, request, username=None, password=None, society_name=None, **kwargs):
        """
        与えられた資格情報（ユーザー名、パスワード、社会名）を使用してユーザーを認証します。
        """
        if username is None or password is None or society_name is None:
            return None # 必要な情報が不足している場合は認証を試みない

        try:
            # まず社会を見つける
            society = Society.objects.get(name=society_name)
        except Society.DoesNotExist:
            # 社会が存在しない場合は認証失敗
            return None

        try:
            # 指定された社会に属するユーザーを見つける
            # username__iexact: 大文字小文字を区別しないユーザー名検索
            user = CustomUser.objects.get(Q(username__iexact=username) | Q(email__iexact=username), society=society)

        except CustomUser.DoesNotExist:
            # ユーザーが存在しない場合は認証失敗
            return None
        except CustomUser.MultipleObjectsReturned:
            # 複数のユーザーが見つかった場合は認証失敗 (ユニーク制約が守られていない可能性)
            # これは通常、usernameがsociety内でuniqueであることを確認することで回避できます。
            return None

        # パスワードを検証
        if user.check_password(password):
            return user # 認証成功
        return None # パスワードが一致しない場合は認証失敗

    def get_user(self, user_id):
        """
        ユーザーIDに基づいてUserオブジェクトを取得します。
        Djangoの認証システムによって使用されます。
        """
        try:
            # ここではCustomUserを使用しているため、CustomUser.objects.getを使う
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None

