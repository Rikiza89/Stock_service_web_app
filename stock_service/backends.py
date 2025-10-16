# stock_service/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Society, SocietyUser

User = get_user_model()


class SocietyAuthBackend(BaseBackend):
    """
    Authenticate user by username/email, password, and society name.
    """

    def authenticate(self, request, username=None, password=None, society_name=None, **kwargs):
        """
        Authenticate using username, password, and society name.
        """
        if username is None or password is None or society_name is None:
            return None

        try:
            society = Society.objects.get(name=society_name)
        except Society.DoesNotExist:
            return None

        try:
            # Find user by username or email
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            return None

        # Verify password first
        if not user.check_password(password):
            return None
        
        if not user.is_active:
            return None

        # Check if user is member of the society
        society_user = SocietyUser.objects.filter(user=user, society=society).first()
        if not society_user:
            return None

        return user

    def get_user(self, user_id):
        """
        Get user by ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None