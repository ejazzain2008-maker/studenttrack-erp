from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access this page.")
            return redirect('login')
        
        # Check if the user is an admin
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            messages.error(request, "Access denied. Admin permissions required.")
            return redirect('dashboard')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def student_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access this page.")
            return redirect('login')
            
        # Check if the user is a student
        if hasattr(request.user, 'profile') and request.user.profile.role != 'student':
            messages.error(request, "Access denied. Only students can access this page.")
            return redirect('dashboard')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view
