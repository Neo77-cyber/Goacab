from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Rider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=11, unique=True, blank=True, null=True)
    date_of_birth = models.DateField()
    vehicle_type = models.CharField(max_length=50)
    vehicle_model = models.CharField(max_length=100)
    rating = models.CharField(max_length=100, blank=True, null=True)
    license_plate = models.CharField(max_length=100, blank=True, null=True)
    drivers_license = models.FileField(upload_to="documents/drivers_license/")
    vehicle_insurance = models.FileField(upload_to="documents/vehicle_insurance/")
    vehicle_registration = models.FileField(upload_to="documents/vehicle_registration/")
    roadworthiness_certificate = models.FileField(
        upload_to="documents/roadworthiness_certificate/"
    )
    national_identification_number = models.CharField(max_length=100)
    proof_of_residency = models.FileField(upload_to="documents/proof_of_residency/")
    passport_photo = models.FileField(upload_to="documents/passport_photos/")
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20, unique=True)
    account_holder_name = models.CharField(max_length=255)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    current_address = models.CharField(max_length=255, blank=True)
    location_updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_busy = models.BooleanField(default=False)
    current_ride = models.ForeignKey(
        "RideRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_driver",
    )

    def __str__(self):
        return self.user.username

    def get_location(self):
        """Return location as tuple (lat, lng)"""
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None

    def update_location(self, latitude, longitude, address=None):
        """Update driver's location"""
        self.latitude = latitude
        self.longitude = longitude
        if address:
            self.current_address = address
        self.location_updated_at = timezone.now()
        self.save()

    def can_accept_ride(self):
        """Check if driver can accept a new ride - with better logic"""
        try:
            active_rides = RideRequest.objects.filter(
                driver=self.user, status__in=["accepted", "started"]
            )
            return not active_rides.exists()
        except Exception as e:
            # If there's any error, assume driver can accept rides
            logger.error(f"Error checking driver status: {e}")
            return True

    def set_available(self):
        """Set driver as available - make it robust"""
        try:
            # If you have a busy field, update it
            if hasattr(self, "is_busy"):
                self.is_busy = False
                self.save(update_fields=["is_busy"])

            # Also clear any current_ride reference if it exists
            if hasattr(self, "current_ride"):
                self.current_ride = None
                self.save(update_fields=["current_ride"])

            logger.info(f"Driver {self.user.username} set to available")
        except Exception as e:
            logger.error(f"Error setting driver available: {e}")

    def set_busy(self, ride):
        """Set driver as busy with a ride - make it robust"""
        try:
            # If you have a busy field, update it
            if hasattr(self, "is_busy"):
                self.is_busy = True
                self.save(update_fields=["is_busy"])

            # Also set current_ride reference if it exists
            if hasattr(self, "current_ride"):
                self.current_ride = ride
                self.save(update_fields=["current_ride"])

            logger.info(f"Driver {self.user.username} set to busy with ride {ride.id}")
        except Exception as e:
            logger.error(f"Error setting driver busy: {e}")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {'Busy' if self.is_busy else 'Available'}"


class RideRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("started", "Started"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    passenger = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ride_requests"
    )
    driver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ride_requests_as_driver",
    )
    current_location = models.CharField(max_length=255)
    pickup_latitude = models.FloatField(blank=True, null=True)
    pickup_longitude = models.FloatField(blank=True, null=True)
    destination_latitude = models.FloatField(blank=True, null=True)
    destination_longitude = models.FloatField(blank=True, null=True)
    destination = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )
    payment_reference = models.CharField(max_length=255, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    distance_km = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    duration_min = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    time_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    distance_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_fare = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    surge_multiplier = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)

    def __str__(self):
        return f"Request by {self.passenger.username} from {self.current_location} to {self.destination}"

    def is_paid(self):
        return self.payment_status == "paid"

    def mark_as_paid(self, reference):
        self.payment_status = "paid"
        self.payment_reference = reference
        self.paid_at = timezone.now()
        self.save()

    def set_pickup_coordinates(self, lat, lng):
        self.pickup_latitude = lat
        self.pickup_longitude = lng
        self.save()

    @property
    def driver_earnings(self):
        if self.total_fare:
            return float(self.total_fare) * 0.8
        return 0.0

    @classmethod
    def get_available_rides_for_driver(cls, driver):
        """Get rides that this specific driver can see and accept"""
        return cls.objects.filter(status="pending", driver__isnull=True).exclude(
            # Exclude rides that other drivers are currently viewing/accepting
            id__in=RideRequest.objects.filter(
                status="pending",
                driver__isnull=True,
                # Add any other exclusion logic here
            ).values("id")
        )

    @classmethod
    def cleanup_canceled_rides(cls, days_old=7):
        """Delete canceled rides older than X days"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_old)

        deleted_count = cls.objects.filter(
            status="cancelled", requested_at__lt=cutoff_date
        ).delete()

        n = deleted_count[0]
        logger.info("Deleted %s cancelled rides older than %s days", n, days_old)
        return n


class DriverPayout(models.Model):
    PAYOUT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    ride = models.ForeignKey(RideRequest, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=PAYOUT_STATUS_CHOICES, default="pending"
    )
    paystack_reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver.full_name} - ₦{self.amount} - {self.status}"


class Trip(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("started", "Started"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trips")
    driver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trips_as_driver",
    )
    pickup_location = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    pickup_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    dropoff_location = models.CharField(max_length=255)
    dropoff_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    dropoff_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    distance_km = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    estimated_time = models.DurationField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Trip from {self.pickup_location} to {self.dropoff_location} - {self.status}"


class Fare(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name="fare")
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    per_km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    per_minute_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=10.00
    )
    total_fare = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    def calculate_fare(self, distance_km, duration_minutes):
        self.total_fare = (
            self.base_fare
            + (distance_km * self.per_km_rate)
            + (duration_minutes * self.per_minute_rate)
        )
        self.save()
        return self.total_fare


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification for {self.user.username}"
