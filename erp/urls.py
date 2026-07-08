from django.urls import path
from . import views

urlpatterns = [
    # General / Informational
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('help/', views.help_center, name='help_center'),
    
    # Auth System
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Dashboards (Dynamic & Static)
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/student/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Profile Management
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    
    # Notification & Messages
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
    path('messages/', views.messages_view, name='messages'),
    path('messages/<int:pk>/read/', views.message_read, name='message_read'),
    path('feedback/', views.feedback_view, name='feedback'),
    
    # Files Upload System
    path('upload/', views.upload_files, name='upload_files'),
    path('upload/<int:pk>/delete/', views.delete_file, name='delete_file'),
    path('upload/<int:pk>/status/<str:status_type>/', views.update_file_status, name='update_file_status'),
    
    # User Management (Admin CRUD)
    path('admin/users/', views.user_management, name='user_management'),
    path('admin/users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('admin/users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    
    # Data / Academic Record Management (Admin CRUD)
    path('admin/data/', views.data_management, name='data_management'),
    path('admin/data/<int:pk>/edit/', views.record_edit, name='record_edit'),
    path('admin/data/<int:pk>/delete/', views.record_delete, name='record_delete'),
    
    # Analytics & Reports & Audit Trail
    path('reports/', views.reports_view, name='reports'),
    path('reports/pdf/', views.pdf_download, name='pdf_download'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('activity-logs/', views.activity_logs_view, name='activity_logs'),
    path('history/', views.history_view, name='history'),
    path('search/', views.search_view, name='search'),
    path('settings/', views.settings_view, name='settings'),
]
