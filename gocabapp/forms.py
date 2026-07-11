from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Driver, Rider
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.contrib.auth.forms import UserCreationForm
import re


class DriverRegistrationForm(forms.Form):

    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    full_name = forms.CharField(max_length=255)
    phone_number = forms.RegexField(
        regex=r"^\d{11}$",
        max_length=11,
        error_messages={"invalid": "Enter a valid 11-digit phone number."},
        widget=forms.TextInput(attrs={"maxlength": "16"}),
    )

    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    national_identification_number = forms.CharField(max_length=100)

    vehicle_type = forms.ChoiceField(choices=[("Car", "Car"), ("Bike", "Bike")])
    vehicle_model = forms.CharField(max_length=100)

    license_plate = forms.CharField(max_length=100)
    drivers_license = forms.FileField()
    vehicle_insurance = forms.FileField()
    vehicle_registration = forms.FileField()
    roadworthiness_certificate = forms.FileField()
    proof_of_residency = forms.FileField()
    passport_photo = forms.FileField()

    bank_name = forms.CharField(max_length=100)
    account_number = forms.CharField(
        max_length=10,
        validators=[
            RegexValidator(r"^\d{10}$", "Account number must be 10 digits long.")
        ],
    )
    account_holder_name = forms.CharField(max_length=255)

    latitude = forms.FloatField(required=True, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=True, widget=forms.HiddenInput())
    current_address = forms.CharField(required=True, widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        try:
            validate_password(password)
        except ValidationError as e:
            for error in e:
                self.add_error("password", error)

        if password != confirm_password:
            self.add_error("confirm_password", "Passwords don't match")

        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            if Driver.objects.filter(user__email=email).exists():
                raise ValidationError("You're already registered as a Driver")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"]
        if Driver.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("This phone number is already registered")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if not latitude or not longitude:
            raise ValidationError(
                "Location detection is required. Please detect your current location."
            )

        return cleaned_data


class RiderRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Full Name",
                "autocomplete": "name",
                "class": "form-control",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email Address",
                "autocomplete": "email",
                "class": "form-control",
            }
        ),
    )

    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Phone Number (e.g., +2348012345678)",
                "autocomplete": "tel",
                "class": "form-control",
                "pattern": "\+234[0-9]{10}",
            }
        ),
    )

    address = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Your complete residential address",
                "autocomplete": "street-address",
                "class": "form-control",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "full_name",
            "email",
            "phone_number",
            "address",
            "password1",
            "password2",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "placeholder": "Username",
                    "autocomplete": "username",
                    "autocapitalize": "none",
                    "pattern": "[a-zA-Z0-9_]+",
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize password help text
        self.fields["password1"].widget.attrs.update(
            {
                "placeholder": "Password",
                "autocomplete": "new-password",
                "class": "form-control",
                "pattern": "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "placeholder": "Confirm Password",
                "autocomplete": "new-password",
                "class": "form-control",
            }
        )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            raise forms.ValidationError(
                "Username can only contain letters, numbers, and underscores."
            )
        return username

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")

        # Validate Nigerian phone number format
        if not re.match(r"^\+234[0-9]{10}$", phone_number):
            raise forms.ValidationError("Please use format: +2348012345678")

        # Check if phone number already exists
        if Rider.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("Phone number is already registered.")

        return phone_number

    def clean_email(self):
        email = self.cleaned_data.get("email")

        # Check if email already exists in Rider model
        if Rider.objects.filter(email=email).exists():
            raise forms.ValidationError("Email is already registered.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

            # Create Rider profile
            Rider.objects.create(
                user=user,
                full_name=self.cleaned_data["full_name"],
                email=self.cleaned_data["email"],
                phone_number=self.cleaned_data["phone_number"],
                address=self.cleaned_data["address"],
            )

        return user


class UpgradeToDriverForm(forms.Form):
    username = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={"readonly": "readonly"})
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={"readonly": "readonly"}))
    phone_number = forms.RegexField(
        regex=r"^\d{11}$",
        max_length=11,
        error_messages={"invalid": "Enter a valid 11-digit phone number."},
        widget=forms.TextInput(attrs={"readonly": "readonly"}),
    )

    full_name = forms.CharField(max_length=255)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    national_identification_number = forms.CharField(max_length=100)

    vehicle_type = forms.ChoiceField(choices=[("Car", "Car"), ("Bike", "Bike")])
    vehicle_model = forms.CharField(max_length=100)

    drivers_license = forms.FileField()
    vehicle_insurance = forms.FileField()
    vehicle_registration = forms.FileField()
    roadworthiness_certificate = forms.FileField()
    proof_of_residency = forms.FileField()
    passport_photo = forms.FileField()

    bank_name = forms.CharField(max_length=100)
    account_number = forms.RegexField(
        regex=r"^\d{10}$",
        error_messages={"invalid": "Account number must be 10 digits long."},
    )
    account_holder_name = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields["username"].initial = user.username
            self.fields["email"].initial = user.email

            try:
                rider = Rider.objects.get(user=user)
                self.fields["phone_number"].initial = rider.phone_number
            except Rider.DoesNotExist:
                pass
