"""enlidea URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings
from main_api import views as main_views


urlpatterns = [
    # (Skill docs moved to frontend/public)
    path('auth-api/', include('accounts.urls')),
    # Forum
    path('api/', include('main_api.urls')),
    #Social
    path('social-api/', include('social.urls')),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
