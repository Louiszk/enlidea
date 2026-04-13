from django.urls import path
from accounts import auth_views as account_views
from accounts import settings_views
from django.contrib import admin
from decouple import config

urlpatterns = [
    # auth-api/
        #auth
            path(config('ADMIN_URL'), admin.site.urls),
            path('check-username/', account_views.check_username, name='check_username'),
            path('register/', account_views.register, name='register'),
            path('login/', account_views.login_view, name='login'),
            path('logout/', account_views.logout_view, name='logout'),
            path('password-reset/', account_views.password_reset, name='password_reset'),
            path('password-reset-confirm/<str:uidb64>/<str:token>/', account_views.password_reset_confirm, name='password_reset_confirm'),
            path('activate/<str:uidb64>/<str:token>/', account_views.activate_account, name='activate'),
            path('resend-activation/', account_views.resend_activation, name='resend_activation'),
            path('current-user/', account_views.current_user, name='current_user'),
            path('token-refresh/', account_views.token_refresh, name='token_refresh'),
        #settings
            path('settings/personal-info/', settings_views.personal_information, name='personal_info'),
            path('settings/verify-email/<str:uidb64>/<str:token>/<str:signed_email>/', settings_views.verify_email, name='verify_email'),
            path('settings/delete-account/', settings_views.delete_account, name='delete_account'),
            path('settings/profile/', settings_views.update_profile, name='update_profile'),
]
