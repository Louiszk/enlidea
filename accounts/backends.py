from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class AuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password):
            if not user.is_active:
                # User exists but is not active
                return user
            return user if self.user_can_authenticate(user) else None
        return None