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
    path('lapangan/', views.LapanganListView.as_view(), name='list_lapangan'),
    path('lapangan/<int:lapangan_id>/', views.DetailLapanganView.as_view(), name='detail_lapangan'),
    
    path('pesan/<int:jadwal_id>/', views.PemesananCreateView.as_view(), name='pesan_lapangan'),
    path('konfirmasi-pemesanan/<int:jadwal_id>/', views.PemesananCreateView.as_view(), name='konfirmasi_pemesanan'),
    path('pemesanan/cancel/<int:pemesanan_id>/', views.cancel_pemesanan, name='cancel_pemesanan'),
    
    # staff
    path('staff/dashboard/', views.dashboard_staff, name='dashboard_staff'),

    # admin
    path('adm/dashboard/', views.dashboard_admin, name='dashboard_admin'),
]