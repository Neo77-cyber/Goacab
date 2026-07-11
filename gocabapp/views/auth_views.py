from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from ..models import Rider, Driver
from ..forms import DriverRegistrationForm, UpgradeToDriverForm, RiderRegistrationForm

import logging
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

from django.contrib import messages
from django.forms import BaseForm





def push_form_errors_to_messages(request, form: BaseForm) -> None:
    for field, errors in form.errors.items():
        field_name = field.replace("_", " ").title()
        for error in errors:
            messages.error(request, f"{field_name}: {error}")



def home(request):

    if request.user.is_authenticated:
        try:
            if hasattr(request.user, "driver"):
                return redirect("driver_dashboard")
            elif hasattr(request.user, "rider"):
                return redirect("rider_dashboard")
        except Exception as e:

            logger.error(f"Profile detection error for {request.user}: {e}")
            pass

    return render(request, "home.html")


def get_a_ride(request):
    if request.method == "POST":
        form = RiderRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    messages.success(
                        request, "Registration successful! You can now log in."
                    )
                    return redirect("signin")

            except Exception as e:
                logger.error(f"Rider registration error: {str(e)}")
                messages.error(
                    request,
                    "Registration failed due to a system error. Please try again.",
                )

        else:

            for field, errors in form.errors.items():
                field_name = field.replace("_", " ").title()
                for error in errors:
                    messages.error(request, f"{field_name}: {error}")

            messages.error(request, "Please correct the errors below.")

    else:
        form = RiderRegistrationForm()

    return render(request, "get-a-ride.html", {"form": form})


def become_a_driver(request):
    if request.method == "POST":
        form = DriverRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data["email"]

            if Rider.objects.filter(user__email=email).exists():
                messages.info(
                    request,
                    "You're already registered as a Rider. Please login and upgrade to Driver.",
                )
                return redirect("upgrade_to_driver")

            try:
                with transaction.atomic():

                    user = User.objects.create_user(
                        username=form.cleaned_data["username"],
                        email=email,
                        password=form.cleaned_data["password"],
                    )

                    driver = Driver.objects.create(
                        user=user,
                        full_name=form.cleaned_data["full_name"],
                        phone_number=form.cleaned_data["phone_number"],
                        date_of_birth=form.cleaned_data["date_of_birth"],
                        vehicle_type=form.cleaned_data["vehicle_type"],
                        vehicle_model=form.cleaned_data["vehicle_model"],
                        drivers_license=form.cleaned_data["drivers_license"],
                        license_plate=form.cleaned_data["license_plate"],
                        vehicle_insurance=form.cleaned_data["vehicle_insurance"],
                        vehicle_registration=form.cleaned_data["vehicle_registration"],
                        roadworthiness_certificate=form.cleaned_data[
                            "roadworthiness_certificate"
                        ],
                        national_identification_number=form.cleaned_data[
                            "national_identification_number"
                        ],
                        proof_of_residency=form.cleaned_data["proof_of_residency"],
                        passport_photo=form.cleaned_data["passport_photo"],
                        bank_name=form.cleaned_data["bank_name"],
                        account_number=form.cleaned_data["account_number"],
                        account_holder_name=form.cleaned_data["account_holder_name"],
                        is_approved=False,
                        latitude=form.cleaned_data.get("latitude"),
                        longitude=form.cleaned_data.get("longitude"),
                        current_address=form.cleaned_data.get("current_address", ""),
                    )

                messages.success(
                    request, "Registration successful! Awaiting admin approval."
                )
                return redirect("signin")

            except Exception as e:
                logger.error(f"Driver registration error: {str(e)}")
                messages.error(
                    request,
                    "Registration failed due to a system error. Please try again.",
                )

        else:
            push_form_errors_to_messages(request, form)
    else:
        form = DriverRegistrationForm()

    return render(request, "become-a-driver.html", {"form": form})


@csrf_exempt
def upgrade_to_driver(request):
    user = request.user
    if not user.is_authenticated:
        messages.error(request, "You must be logged in to access this page.")
        return redirect("signin")
    if request.method == "POST":
        form = UpgradeToDriverForm(request.POST, request.FILES, user=user)
    else:
        form = UpgradeToDriverForm(user=user)
    if form.is_valid():
        try:
            Driver.objects.create(
                user=user,
                full_name=form.cleaned_data["full_name"],
                phone_number=form.cleaned_data["phone_number"],
                date_of_birth=form.cleaned_data["date_of_birth"],
                vehicle_type=form.cleaned_data["vehicle_type"],
                vehicle_model=form.cleaned_data["vehicle_model"],
                drivers_license=form.cleaned_data["drivers_license"],
                vehicle_insurance=form.cleaned_data["vehicle_insurance"],
                vehicle_registration=form.cleaned_data["vehicle_registration"],
                roadworthiness_certificate=form.cleaned_data[
                    "roadworthiness_certificate"
                ],
                national_identification_number=form.cleaned_data[
                    "national_identification_number"
                ],
                proof_of_residency=form.cleaned_data["proof_of_residency"],
                passport_photo=form.cleaned_data["passport_photo"],
                bank_name=form.cleaned_data["bank_name"],
                account_number=form.cleaned_data["account_number"],
                account_holder_name=form.cleaned_data["account_holder_name"],
                is_approved=False,
            )
            messages.success(request, "Upgrade successful! Awaiting admin approval.")
            return redirect("driver_dashboard")
        except Rider.DoesNotExist:
            messages.error(request, "You are not registered as a Rider.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    return render(request, "upgrade-to-driver.html", {"form": form})


@csrf_exempt
def signin(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user:
            try:
                driver = Driver.objects.get(user=user)
                if not driver.is_approved:
                    messages.error(
                        request,
                        "Your driver account is pending approval. Please wait for admin verification.",
                    )
                    return redirect("signin")
                login(request, user)
                return redirect("driver_dashboard")

            except Driver.DoesNotExist:
                pass

            try:
                rider = Rider.objects.get(user=user)
                login(request, user)
                return redirect("rider_dashboard")
            except Rider.DoesNotExist:
                pass
            messages.error(request, "Invalid account type. Please contact support.")
        else:
            messages.error(request, "Wrong username or password.")
    return render(request, "signin.html")


def logout_view(request):
    logout(request)
    return redirect("signin")
