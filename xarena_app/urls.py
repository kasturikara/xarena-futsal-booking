from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('about/', views.about, name='about'),
    
    # auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # user
    path('dashboard/', views.dashboard_user, name='dashboard_user'),
    
    # staff
    path('staff/dashboard/', views.dashboard_staff, name='dashboard_staff'),

    # admin
    path('adm/dashboard/', views.dashboard_admin, name='dashboard_admin'),
]