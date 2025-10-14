from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import Society, User as CustomUser

class SocietyAuthBackend(BaseBackend):
    """
    社会名、ユーザー名、パスワードに基づいてユーザーを認証するカスタム認証バックエンド。
    """

    def authenticate(self, request, username=None, password=None, society_name=None, **kwargs):

        if username is None or password is None or society_name is None:
            return None # 必要な情報が不足している場合は認証を試みない
        
        try:
            # 1. まず社会を見つける
            society = Society.objects.get(name=society_name)
        except Society.DoesNotExist:
            return None # 社会が存在しない場合は認証失敗

        # 2. 指定された社会に属するユーザーを見つける
        try:
            # get() の代わりに filter().first() を使用し、MultipleObjectsReturned を回避する
            user_candidates = CustomUser.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username), 
                society=society
            )
            # 該当するユーザーがいれば最初のユーザーを取得、いなければ None
            user = user_candidates.first() 
            
            if user is None:
                return None # ユーザーが見つからなかった

        except Exception:
            # 予期せぬDBエラー (接続エラーなど) の場合は失敗
            return None

        # 3. パスワードを検証
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
