"""
Main URL Configuration
Routes to GPS application and Django admin
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin panel
    path('admin/', admin.site.urls),
    
    # GPS application routes
    # Includes all GPS endpoints: /gps/, /history/, /history/simple/
    path('', include('apps.gps.urls')),
]
