from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, StudentRecord, DocumentUpload, Message

class SignupForm(forms.ModelForm):
    roll_number = forms.CharField(max_length=50, required=True, label="Roll Number",
                                  widget=forms.TextInput(attrs={'placeholder': 'Enter your Roll Number'}))
    course = forms.ChoiceField(choices=UserProfile.COURSE_CHOICES, required=True, label="Diploma Course")
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Choose a password'}), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password'}), required=True)
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'placeholder': 'Enter phone number'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Choose a username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter your email'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
        }

    def clean_roll_number(self):
        roll_number = self.cleaned_data.get('roll_number')
        if UserProfile.objects.filter(roll_number=roll_number).exists():
            raise forms.ValidationError("This Roll Number is already registered.")
        return roll_number

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            profile = user.profile
            profile.roll_number = self.cleaned_data.get('roll_number')
            profile.course = self.cleaned_data.get('course')
            profile.phone = self.cleaned_data.get('phone')
            profile.save()
        return user


class UserEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    profile_pic = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['phone'].initial = self.instance.profile.phone
            self.fields['bio'].initial = self.instance.profile.bio
            self.fields['profile_pic'].initial = self.instance.profile.profile_pic

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile = user.profile
            profile.phone = self.cleaned_data.get('phone')
            profile.bio = self.cleaned_data.get('bio')
            if self.cleaned_data.get('profile_pic'):
                profile.profile_pic = self.cleaned_data.get('profile_pic')
            profile.save()
        return user


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = DocumentUpload
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Document / Form Title'}),
            'file': forms.ClearableFileInput(),
        }


class StudentRecordForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role='student'),
        label="Select Student",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = StudentRecord
        fields = ['student', 'semester', 'marks_obtained', 'attendance_percentage', 'academic_status']
        widgets = {
            'semester': forms.TextInput(attrs={'placeholder': 'e.g., Semester 1'}),
            'marks_obtained': forms.NumberInput(attrs={'min': 0, 'max': 100}),
            'attendance_percentage': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 0.01}),
            'academic_status': forms.Select(attrs={'class': 'form-select'}),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your Email'}),
            'subject': forms.TextInput(attrs={'placeholder': 'Message Subject'}),
            'message': forms.Textarea(attrs={'placeholder': 'Write your message here...', 'rows': 4}),
        }


class FeedbackForm(forms.Form):
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'placeholder': 'Feedback Subject'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Share your suggestions...', 'rows': 4}))
