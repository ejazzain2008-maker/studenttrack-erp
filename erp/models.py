from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('student', 'Student User'),
    ]
    
    COURSE_CHOICES = [
        ('Diploma in Computer Science', 'Diploma in Computer Science'),
        ('Diploma in Mechanical Engineering', 'Diploma in Mechanical Engineering'),
        ('Diploma in Electrical Engineering', 'Diploma in Electrical Engineering'),
        ('Diploma in Civil Engineering', 'Diploma in Civil Engineering'),
        ('Diploma in Electronics Engineering', 'Diploma in Electronics Engineering'),
        ('Diploma in Automobile Engineering', 'Diploma in Automobile Engineering'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    roll_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    course = models.CharField(max_length=100, choices=COURSE_CHOICES, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.get_role_display()})"

# Automatic Profile Creation for standard users
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Check if it's the first user created, make it Admin, else Student
        if User.objects.count() == 1:
            UserProfile.objects.create(user=instance, role='admin')
            instance.is_superuser = True
            instance.is_staff = True
            post_save.disconnect(create_user_profile, sender=User)
            instance.save()
            post_save.connect(create_user_profile, sender=User)
        else:
            UserProfile.objects.create(user=instance, role='student')

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        post_save.disconnect(save_user_profile, sender=User)
        instance.profile.save()
        post_save.connect(save_user_profile, sender=User)

@receiver(post_save, sender=User)
def enforce_single_admin(sender, instance, **kwargs):
    # Only allow exactly one admin user.
    # The first created user is the Admin.
    first_admin_profile = UserProfile.objects.filter(role='admin').order_by('id').first()
    if first_admin_profile:
        primary_admin = first_admin_profile.user
    else:
        primary_admin = User.objects.order_by('id').first()

    if primary_admin and instance != primary_admin:
        needs_user_save = False
        needs_profile_save = False

        if instance.is_superuser or instance.is_staff:
            instance.is_superuser = False
            instance.is_staff = False
            needs_user_save = True

        if hasattr(instance, 'profile') and instance.profile.role != 'student':
            instance.profile.role = 'student'
            needs_profile_save = True

        if needs_user_save:
            post_save.disconnect(create_user_profile, sender=User)
            post_save.disconnect(enforce_single_admin, sender=User)
            instance.save()
            post_save.connect(create_user_profile, sender=User)
            post_save.connect(enforce_single_admin, sender=User)

        if needs_profile_save:
            instance.profile.save()



class StudentRecord(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
        ('Graduated', 'Graduated'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records')
    semester = models.CharField(max_length=20)
    marks_obtained = models.IntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    academic_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='created_records')

    def __str__(self):
        return f"Record: {self.student.username} - Semester {self.semester}"


class DocumentUpload(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='student_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    feedback = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} - Uploaded by {self.student.username}"


class ActivityLog(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='activity_logs')
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{username} - {self.action} at {self.timestamp}"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username} - {self.title}"


class Message(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='sent_messages')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"
