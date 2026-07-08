import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from erp.models import UserProfile, StudentRecord, DocumentUpload, ActivityLog, Notification, Message

class Command(BaseCommand):
    help = 'Seeds StudentTrack ERP database with initial Admin account and dummy student data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing existing data...')
        # Clear existing models (excluding default content types/migrations)
        StudentRecord.objects.all().delete()
        DocumentUpload.objects.all().delete()
        ActivityLog.objects.all().delete()
        Notification.objects.all().delete()
        Message.objects.all().delete()
        
        # Keep superusers if they exist, but clear student users
        User.objects.exclude(username='admin').delete()
        if not User.objects.filter(username='admin').exists():
            self.stdout.write('Creating primary Admin account...')
            # This triggers create_user_profile receiver which sets role='admin', is_superuser=True
            admin_user = User.objects.create_superuser('admin', 'admin@studenttrack.erp', 'admin12345')
            admin_user.first_name = "System"
            admin_user.last_name = "Administrator"
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Admin account created: admin / admin12345'))
        else:
            admin_user = User.objects.get(username='admin')

        # Mock students data
        students_raw = [
            {
                'username': 'rohan',
                'first_name': 'Rohan',
                'last_name': 'Sharma',
                'email': 'rohan@studenttrack.erp',
                'roll': 'DCS-2026-01',
                'course': 'Diploma in Computer Science',
                'phone': '+91 98765 43210',
                'bio': 'Passionate about coding, databases, and Linux administration.'
            },
            {
                'username': 'priya',
                'first_name': 'Priya',
                'last_name': 'Patel',
                'email': 'priya@studenttrack.erp',
                'roll': 'DME-2026-04',
                'course': 'Diploma in Mechanical Engineering',
                'phone': '+91 87654 32109',
                'bio': 'Fascinated by mechanical design, CAD modeling, and thermodynamics.'
            },
            {
                'username': 'arjun',
                'first_name': 'Arjun',
                'last_name': 'Varma',
                'email': 'arjun@studenttrack.erp',
                'roll': 'DEE-2026-07',
                'course': 'Diploma in Electrical Engineering',
                'phone': '+91 76543 21098',
                'bio': 'Enjoys circuit design, embedded controllers, and IoT systems.'
            }
        ]

        self.stdout.write('Creating student users and records...')
        created_students = []
        for sdata in students_raw:
            user = User.objects.create_user(sdata['username'], sdata['email'], 'student123')
            user.first_name = sdata['first_name']
            user.last_name = sdata['last_name']
            user.save()
            
            # Update created profile
            profile = user.profile
            profile.roll_number = sdata['roll']
            profile.course = sdata['course']
            profile.phone = sdata['phone']
            profile.bio = sdata['bio']
            profile.save()
            
            created_students.append(user)
            self.stdout.write(f"Student created: {user.username} (Roll: {sdata['roll']})")

        # Create Academic Records for students
        semesters = ['Semester 1', 'Semester 2', 'Semester 3']
        marks_matrix = {
            'rohan': [85, 90, 88],
            'priya': [78, 82, 80],
            'arjun': [92, 94, 95]
        }
        attendance_matrix = {
            'rohan': [88.5, 92.0, 90.0],
            'priya': [75.0, 80.5, 78.0],
            'arjun': [96.0, 98.2, 97.5]
        }

        self.stdout.write('Seeding semester grades and attendance logs...')
        for student in created_students:
            u_name = student.username
            for idx, sem in enumerate(semesters):
                StudentRecord.objects.create(
                    student=student,
                    semester=sem,
                    marks_obtained=marks_matrix[u_name][idx],
                    attendance_percentage=attendance_matrix[u_name][idx],
                    academic_status='Active',
                    created_by=admin_user
                )

        # Create a mock uploaded document file on disk so that it's clickable
        media_docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'media', 'student_docs')
        os.makedirs(media_docs_dir, exist_ok=True)
        
        # Seed mock document uploads
        self.stdout.write('Uploading dummy files...')
        doc_titles = ['Admission Form', 'Semester 1 Marksheet', 'Practical Project Report']
        for student in created_students:
            for idx, title in enumerate(doc_titles):
                mock_filename = f"{student.username}_doc_{idx}.pdf"
                mock_file_path = os.path.join(media_docs_dir, mock_filename)
                
                # Write a tiny text file representing a pdf
                with open(mock_file_path, 'w') as f:
                    f.write(f"Mock PDF document for {student.username} - Title: {title}")
                
                DocumentUpload.objects.create(
                    student=student,
                    title=title,
                    file=f"student_docs/{mock_filename}",
                    status='Pending' if idx == 2 else 'Approved',
                    feedback='Excellent presentation.' if idx == 1 else ''
                )

        # Create activity logs
        self.stdout.write('Writing initial activity logs...')
        for student in created_students:
            ActivityLog.objects.create(user=student, action="Signed Up & Logged In", ip_address="127.0.0.1")
            ActivityLog.objects.create(user=student, action=f"Uploaded document: {doc_titles[0]}", ip_address="127.0.0.1")
            ActivityLog.objects.create(user=admin_user, action=f"Created academic record for {student.username}", ip_address="127.0.0.1")
            
        # Create notifications
        self.stdout.write('Seeding system notifications...')
        for student in created_students:
            Notification.objects.create(
                recipient=student,
                title="Welcome to StudentTrack!",
                message="Your student profile has been set up successfully. Navigate to Profile to see details."
            )
            Notification.objects.create(
                recipient=student,
                title="Admission Document Reviewed",
                message="Your submitted Admission Form has been approved by the Registrar."
            )

        # Create contact messages
        self.stdout.write('Seeding contact messages...')
        Message.objects.create(
            name="Rahul Kumar",
            email="rahul@example.com",
            subject="Queries about DCS course fees",
            message="Hi Registrar, what is the semester fee details for DCS Diploma starting next term?",
            is_read=False
        )
        Message.objects.create(
            name="Sneha Rao",
            email="sneha@example.com",
            subject="Help with profile picture upload",
            message="Hello, I cannot upload my profile picture. It says format invalid. Please check.",
            is_read=True
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with complete dummy data!'))
