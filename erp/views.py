import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.http import HttpResponse, Http404
from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa

from .models import UserProfile, StudentRecord, DocumentUpload, ActivityLog, Notification, Message
from .forms import SignupForm, UserEditForm, DocumentUploadForm, StudentRecordForm, ContactForm, FeedbackForm
from .decorators import admin_required, student_required

# Helper to log user activity
def log_activity(user, action, request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    ActivityLog.objects.create(user=user, action=action, ip_address=ip)

# Helper to render PDF
def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

# ==================== GENERAL / INFORMATIONAL VIEWS ====================

def home(request):
    # Retrieve some basic metrics to show on landing page
    context = {
        'total_students': UserProfile.objects.filter(role='student').count(),
        'total_courses': len(UserProfile.COURSE_CHOICES),
    }
    return render(request, 'erp/home.html', context)

def about(request):
    return render(request, 'erp/about.html')

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            if request.user.is_authenticated:
                msg.user = request.user
            msg.save()
            
            # Send notification to Admin (the first user usually, or all admins)
            admins = User.objects.filter(profile__role='admin')
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    title="New Support Message Received",
                    message=f"A contact query was submitted by {msg.name} ({msg.email}): '{msg.subject}'"
                )
                
            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email
            }
        form = ContactForm(initial=initial_data)
        
    return render(request, 'erp/contact.html', {'form': form})

@login_required
def help_center(request):
    return render(request, 'erp/help_center.html')

# ==================== AUTHENTICATION VIEWS ====================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            log_activity(user, "Logged In", request)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'erp/login.html')

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_activity(user, "Signed Up & Logged In", request)
            login(request, user)
            messages.success(request, "Account created successfully! Welcome to StudentTrack ERP.")
            
            # Notify admins of a new signup
            admins = User.objects.filter(profile__role='admin')
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    title="New Student Registered",
                    message=f"Student {user.username} (Roll: {user.profile.roll_number}) signed up for {user.profile.course}."
                )
                
            return redirect('dashboard')
        else:
            messages.error(request, "Error in signup form. Please correct below.")
    else:
        form = SignupForm()
        
    return render(request, 'erp/signup.html', {'form': form})

@login_required
def logout_view(request):
    log_activity(request.user, "Logged Out", request)
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return render(request, 'erp/logout_confirm.html')

@login_required
def change_password(request):
    if request.method == 'POST':
        old_pass = request.POST.get('old_password')
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')
        
        # Verify old password
        user = authenticate(request, username=request.user.username, password=old_pass)
        if user is None:
            messages.error(request, "Incorrect current password.")
        elif new_pass != confirm_pass:
            messages.error(request, "New passwords do not match.")
        elif len(new_pass) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        else:
            request.user.set_password(new_pass)
            request.user.save()
            update_session_auth_hash(request, request.user) # Maintain login session
            log_activity(request.user, "Changed Password", request)
            messages.success(request, "Password updated successfully!")
            return redirect('profile')
            
    return render(request, 'erp/change_password.html')

# ==================== DASHBOARD VIEWS ====================

@login_required
def dashboard(request):
    # Dynamic redirect based on role
    if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
        return redirect('admin_dashboard')
    return redirect('user_dashboard')

@login_required
@student_required
def user_dashboard(request):
    user = request.user
    profile = user.profile
    records = user.records.all().order_index_by = '-updated_at'
    
    # Calculate stats
    avg_marks = user.records.all().aggregate(Avg('marks_obtained'))['marks_obtained__avg'] or 0
    avg_attendance = user.records.all().aggregate(Avg('attendance_percentage'))['attendance_percentage__avg'] or 0
    recent_docs = user.documents.all().order_by('-uploaded_at')[:5]
    notifications = user.notifications.filter(is_read=False).order_by('-created_at')[:5]
    
    context = {
        'profile': profile,
        'records': records,
        'avg_marks': round(avg_marks, 2),
        'avg_attendance': round(avg_attendance, 2),
        'recent_docs': recent_docs,
        'unread_notifications_count': user.notifications.filter(is_read=False).count(),
        'notifications': notifications
    }
    return render(request, 'erp/dashboard_user.html', context)

@login_required
@admin_required
def admin_dashboard(request):
    # Stats counts
    total_students = UserProfile.objects.filter(role='student').count()
    total_uploads = DocumentUpload.objects.count()
    pending_uploads = DocumentUpload.objects.filter(status='Pending').count()
    total_messages = Message.objects.filter(is_read=False).count()
    
    # Aggregate student stats
    all_records = StudentRecord.objects.all()
    avg_marks = all_records.aggregate(Avg('marks_obtained'))['marks_obtained__avg'] or 0
    avg_attendance = all_records.aggregate(Avg('attendance_percentage'))['attendance_percentage__avg'] or 0
    
    # Lists
    recent_students = User.objects.filter(profile__role='student').order_by('-date_joined')[:5]
    recent_uploads = DocumentUpload.objects.order_by('-uploaded_at')[:5]
    recent_logs = ActivityLog.objects.order_by('-timestamp')[:5]
    
    context = {
        'total_students': total_students,
        'total_uploads': total_uploads,
        'pending_uploads': pending_uploads,
        'total_messages': total_messages,
        'avg_marks': round(avg_marks, 2),
        'avg_attendance': round(avg_attendance, 2),
        'recent_students': recent_students,
        'recent_uploads': recent_uploads,
        'recent_logs': recent_logs
    }
    return render(request, 'erp/dashboard_admin.html', context)

# ==================== PROFILE VIEWS ====================

@login_required
def profile_view(request):
    # Users can view their own details, and admins can view their own details.
    # Users CANNOT view admin details. If request is to view a specific admin profile, block it.
    target_user_id = request.GET.get('id')
    if target_user_id:
        target_user = get_object_or_404(User, id=target_user_id)
        # Block if a standard student tries to view an admin profile or anyone else's profile
        if request.user.profile.role != 'admin' and target_user != request.user:
            messages.error(request, "Permission denied. You cannot view other profiles.")
            return redirect('dashboard')
        # Standard students can never view admin details
        if request.user.profile.role == 'student' and target_user.profile.role == 'admin':
            messages.error(request, "Access Denied. Admin details are protected.")
            return redirect('dashboard')
    else:
        target_user = request.user
        
    return render(request, 'erp/profile.html', {'target_user': target_user})

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            log_activity(request.user, "Edited Profile Info", request)
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = UserEditForm(instance=request.user)
        
    return render(request, 'erp/profile_edit.html', {'form': form})

# ==================== NOTIFICATIONS & MESSAGES ====================

@login_required
def notifications_view(request):
    notifications = request.user.notifications.all().order_by('-created_at')
    return render(request, 'erp/notifications.html', {'notifications': notifications})

@login_required
def notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    return redirect('notifications')

@login_required
def messages_view(request):
    if request.user.profile.role == 'admin':
        msgs = Message.objects.all().order_by('-created_at')
    else:
        msgs = Message.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'erp/messages.html', {'messages': msgs})

@login_required
@admin_required
def message_read(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    msg.is_read = True
    msg.save()
    messages.success(request, "Message marked as read.")
    return redirect('messages')

@login_required
def feedback_view(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            msg = Message.objects.create(
                user=request.user,
                name=request.user.get_full_name() or request.user.username,
                email=request.user.email,
                subject=f"System Feedback: {form.cleaned_data['subject']}",
                message=form.cleaned_data['message']
            )
            
            # Notify admin
            admins = User.objects.filter(profile__role='admin')
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    title="New Feedback Submitted",
                    message=f"Feedback submitted by student {request.user.username}."
                )
                
            log_activity(request.user, "Submitted System Feedback", request)
            messages.success(request, "Thank you for your feedback!")
            return redirect('feedback')
    else:
        form = FeedbackForm()
    return render(request, 'erp/feedback.html', {'form': form})

# ==================== FILE UPLOAD SYSTEM ====================

@login_required
def upload_files(request):
    if request.user.profile.role == 'admin':
        # Admin views all uploaded files
        docs = DocumentUpload.objects.all().order_by('-uploaded_at')
    else:
        # Students view their own uploaded files
        docs = request.user.documents.all().order_by('-uploaded_at')
        
    if request.method == 'POST':
        if request.user.profile.role == 'admin':
            messages.error(request, "Administrators do not upload student forms.")
            return redirect('upload_files')
            
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.student = request.user
            doc.save()
            
            log_activity(request.user, f"Uploaded document: {doc.title}", request)
            
            # Alert admin of new document upload
            admins = User.objects.filter(profile__role='admin')
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    title="Student Document Uploaded",
                    message=f"Student {request.user.username} uploaded document: {doc.title}"
                )
                
            messages.success(request, "Document uploaded successfully! Pending review.")
            return redirect('upload_files')
    else:
        form = DocumentUploadForm()
        
    return render(request, 'erp/upload_files.html', {'form': form, 'documents': docs})

@login_required
def delete_file(request, pk):
    doc = get_object_or_404(DocumentUpload, pk=pk)
    
    # Students can delete only their own, Admin can delete any
    if request.user.profile.role != 'admin' and doc.student != request.user:
        messages.error(request, "Access denied.")
        return redirect('upload_files')
        
    title = doc.title
    # Delete local file physically
    if doc.file:
        if os.path.exists(doc.file.path):
            os.remove(doc.file.path)
            
    doc.delete()
    log_activity(request.user, f"Deleted document: {title}", request)
    messages.success(request, f"Document '{title}' has been deleted.")
    return redirect('upload_files')

@login_required
@admin_required
def update_file_status(request, pk, status_type):
    doc = get_object_or_404(DocumentUpload, pk=pk)
    feedback_text = request.POST.get('feedback', '')
    
    if status_type == 'approve':
        doc.status = 'Approved'
        msg_title = "Document Approved"
        msg_body = f"Your document '{doc.title}' has been approved by the Administrator."
    elif status_type == 'reject':
        doc.status = 'Rejected'
        msg_title = "Document Rejected"
        msg_body = f"Your document '{doc.title}' was rejected. Reason: {feedback_text}"
    else:
        messages.error(request, "Invalid status change request.")
        return redirect('upload_files')
        
    doc.feedback = feedback_text
    doc.save()
    
    # Notify student
    Notification.objects.create(
        recipient=doc.student,
        title=msg_title,
        message=msg_body
    )
    
    log_activity(request.user, f"Reviewed document: {doc.title} ({doc.status})", request)
    messages.success(request, f"Document '{doc.title}' updated to {doc.status}.")
    return redirect('upload_files')

# ==================== USER MANAGEMENT (ADMIN ONLY) ====================

@login_required
@admin_required
def user_management(request):
    users = User.objects.filter(profile__role='student').order_by('username')
    query = request.GET.get('search')
    course_filter = request.GET.get('course')
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(profile__roll_number__icontains=query)
        )
    if course_filter:
        users = users.filter(profile__course=course_filter)
        
    if request.method == 'POST':
        # Admin can add user
        form = SignupForm(request.POST)
        if form.is_valid():
            new_u = form.save()
            log_activity(request.user, f"Created user account: {new_u.username}", request)
            messages.success(request, f"Student Account for {new_u.username} created successfully!")
            return redirect('user_management')
        else:
            messages.error(request, "Error in adding user. Details below.")
    else:
        form = SignupForm()
        
    courses = [c[0] for c in UserProfile.COURSE_CHOICES]
    return render(request, 'erp/user_management.html', {
        'users': users, 
        'form': form, 
        'courses': courses,
        'search_query': query,
        'course_filter': course_filter
    })

@login_required
@admin_required
def user_edit(request, pk):
    target_user = get_object_or_404(User, pk=pk, profile__role='student')
    
    if request.method == 'POST':
        # Admin edit username/first_name/last_name/email/roll_number/course/phone
        target_user.username = request.POST.get('username')
        target_user.first_name = request.POST.get('first_name')
        target_user.last_name = request.POST.get('last_name')
        target_user.email = request.POST.get('email')
        target_user.save()
        
        profile = target_user.profile
        profile.roll_number = request.POST.get('roll_number')
        profile.course = request.POST.get('course')
        profile.phone = request.POST.get('phone')
        profile.save()
        
        log_activity(request.user, f"Edited user details: {target_user.username}", request)
        messages.success(request, f"Student profile for '{target_user.username}' updated successfully.")
        return redirect('user_management')
        
    return redirect('user_management')

@login_required
@admin_required
def user_delete(request, pk):
    target_user = get_object_or_404(User, pk=pk, profile__role='student')
    username = target_user.username
    target_user.delete()
    log_activity(request.user, f"Deleted user account: {username}", request)
    messages.success(request, f"Student '{username}' has been deleted from the database.")
    return redirect('user_management')

# ==================== DATA / ACADEMIC RECORDS (ADMIN ONLY) ====================

@login_required
@admin_required
def data_management(request):
    records = StudentRecord.objects.all().order_by('-updated_at')
    query = request.GET.get('search')
    semester_filter = request.GET.get('semester')
    
    if query:
        records = records.filter(
            Q(student__username__icontains=query) |
            Q(student__first_name__icontains=query) |
            Q(student__profile__roll_number__icontains=query)
        )
    if semester_filter:
        records = records.filter(semester__icontains=semester_filter)
        
    if request.method == 'POST':
        form = StudentRecordForm(request.POST)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.created_by = request.user
            rec.save()
            
            # Notify student
            Notification.objects.create(
                recipient=rec.student,
                title="Academic Record Created/Updated",
                message=f"Admin added an academic record for {rec.semester} with Marks: {rec.marks_obtained}%"
            )
            
            log_activity(request.user, f"Created academic record for {rec.student.username}", request)
            messages.success(request, f"Record added for {rec.student.username}!")
            return redirect('data_management')
    else:
        form = StudentRecordForm()
        
    return render(request, 'erp/data_management.html', {
        'records': records,
        'form': form,
        'search_query': query,
        'semester_filter': semester_filter
    })

@login_required
@admin_required
def record_edit(request, pk):
    print("METHOD =", request.method)
    print("POST =", request.POST)
    
    record = get_object_or_404(StudentRecord, pk=pk)
    if request.method == 'POST':
        print(request.POST)
        record.semester = request.POST.get('semester')
        record.marks_obtained = int(request.POST.get('marks_obtained', 0))
        record.attendance_percentage = float(request.POST.get('attendance_percentage', 0))
        record.academic_status = request.POST.get('academic_status', 'Active')
        record.save()
        
        # Notify student
        Notification.objects.create(
            recipient=record.student,
            title="Academic Record Modified",
            message=f"Admin updated your performance details for {record.semester}."
        )
        
        log_activity(request.user, f"Updated academic record for {record.student.username}", request)
        messages.success(request, f"Record updated for {record.student.username}.")
        return redirect('data_management')
        
    return redirect('data_management')

@login_required
@admin_required
def record_delete(request, pk):
    record = get_object_or_404(StudentRecord, pk=pk)
    student_name = record.student.username
    record.delete()
    log_activity(request.user, f"Deleted academic record of {student_name}", request)
    messages.success(request, f"Academic record for {student_name} deleted.")
    return redirect('data_management')

# ==================== REPORTS & REPORTS PDF DOWNLOAD ====================

@login_required
def reports_view(request):
    if request.user.profile.role == 'admin':
        records = StudentRecord.objects.all().order_by('-updated_at')
    else:
        records = request.user.records.all().order_by('-updated_at')
        
    context = {
        'records': records,
        'is_admin': request.user.profile.role == 'admin',
    }
    return render(request, 'erp/reports.html', context)

@login_required
def pdf_download(request):
    if request.user.profile.role == 'admin':
        records = StudentRecord.objects.all().order_by('student__username', 'semester')
        title = "StudentTrack ERP - Overall Academic System Report"
    else:
        records = request.user.records.all().order_by('semester')
        title = f"StudentTrack ERP - Academic Transcript ({request.user.profile.roll_number})"
        
    context = {
        'records': records,
        'title': title,
        'user': request.user,
        'is_admin': request.user.profile.role == 'admin',
    }
    
    pdf = render_to_pdf('erp/pdf_template.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = "StudentTrack_Report.pdf"
        content = f"inline; filename={filename}"
        response['Content-Disposition'] = content
        return response
    return HttpResponse("Error rendering PDF", status=400)

# ==================== ANALYTICS & GRAPHICS ====================

@login_required
def analytics_view(request):
    # Prepare metrics context for Chart.js
    if request.user.profile.role == 'admin':
        # Analytics by courses enrollment
        course_stats = UserProfile.objects.filter(role='student').values('course').annotate(count=Count('id'))
        # Average grade ranges
        grade_stats = StudentRecord.objects.all().values('academic_status').annotate(count=Count('id'))
        
        # Format course chart data
        course_labels = [stat['course'] or 'General' for stat in course_stats]
        course_data = [stat['count'] for stat in course_stats]
        
        # Format grade distribution chart data
        grade_labels = [stat['academic_status'] for stat in grade_stats]
        grade_data = [stat['count'] for stat in grade_stats]
        
        # Average attendance per course
        course_attendance_stats = StudentRecord.objects.all().values('student__profile__course').annotate(avg_att=Avg('attendance_percentage'))
        course_att_labels = [stat['student__profile__course'] or 'General' for stat in course_attendance_stats]
        course_att_data = [round(float(stat['avg_att'] or 0.0), 2) for stat in course_attendance_stats]
        
        context = {
            'course_labels': course_labels,
            'course_data': course_data,
            'grade_labels': grade_labels,
            'grade_data': grade_data,
            'course_att_labels': course_att_labels,
            'course_att_data': course_att_data,
            'is_admin': True,
        }
    else:
        # Student specific charts (grades over semester, attendance semester comparison)
        my_records = request.user.records.all().order_by('semester')
        semester_labels = [rec.semester for rec in my_records]
        semester_marks = [rec.marks_obtained for rec in my_records]
        semester_att = [round(float(rec.attendance_percentage), 2) for rec in my_records]
        
        context = {
            'semester_labels': semester_labels,
            'semester_marks': semester_marks,
            'semester_att': semester_att,
            'is_admin': False,
        }
        
    return render(request, 'erp/analytics.html', context)

# ==================== ADDITIONAL CORE PAGES ====================

@login_required
def activity_logs_view(request):
    if request.user.profile.role == 'admin':
        logs = ActivityLog.objects.all().order_by('-timestamp')
    else:
        logs = request.user.activity_logs.all().order_by('-timestamp')
    return render(request, 'erp/activity_logs.html', {'logs': logs})

@login_required
def history_view(request):
    if request.user.profile.role == 'admin':
        logs = ActivityLog.objects.filter(action__icontains="Created").order_by('-timestamp')
        records = StudentRecord.objects.all().order_by('-updated_at')
    else:
        logs = request.user.activity_logs.filter(action__icontains="Uploaded").order_by('-timestamp')
        records = request.user.records.all().order_by('-updated_at')
        
    return render(request, 'erp/history.html', {'logs': logs, 'records': records})

@login_required
def search_view(request):
    query = request.GET.get('q', '')
    users = []
    docs = []
    records = []
    
    if query:
        if request.user.profile.role == 'admin':
            users = UserProfile.objects.filter(
                Q(roll_number__icontains=query) |
                Q(user__username__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(course__icontains=query)
            )
            docs = DocumentUpload.objects.filter(
                Q(title__icontains=query) |
                Q(student__username__icontains=query)
            )
            records = StudentRecord.objects.filter(
                Q(student__username__icontains=query) |
                Q(semester__icontains=query)
            )
        else:
            docs = request.user.documents.filter(title__icontains=query)
            records = request.user.records.filter(semester__icontains=query)
            
    context = {
        'query': query,
        'users_results': users,
        'docs_results': docs,
        'records_results': records,
        'is_admin': request.user.profile.role == 'admin',
    }
    return render(request, 'erp/search.html', context)

@login_required
def settings_view(request):
    # Simulated system configuration page stored in settings/session
    if request.method == 'POST':
        request.session['dark_mode'] = request.POST.get('dark_mode') == 'true'
        request.session['enable_animations'] = request.POST.get('enable_animations') == 'true'
        request.session['sidebar_expanded'] = request.POST.get('sidebar_expanded') == 'true'
        messages.success(request, "Preferences saved successfully!")
        return redirect('settings')
        
    return render(request, 'erp/settings.html')
