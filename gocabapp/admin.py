from django.contrib import admin
from .models import *
from django.contrib import admin
from django.utils.html import format_html


# Register your models here.


admin.site.register(Rider)
admin.site.register(Notification)
admin.site.register(DriverPayout)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ["user", "is_busy", "current_ride", "is_approved", "vehicle_model"]
    list_filter = ["is_busy", "is_approved", "vehicle_type"]
    readonly_fields = ["is_busy", "current_ride"]  
    actions = ["make_available"]

    def make_available(self, request, queryset):
        """Admin action to force set drivers as available"""
        updated = 0
        for driver in queryset:
            try:
                driver.is_busy = False
                driver.current_ride = None
                driver.save()
                updated += 1
            except Exception as e:
                self.message_user(
                    request, f"Error updating driver {driver}: {e}", level="error"
                )

        self.message_user(request, f"Successfully made {updated} drivers available.")

    make_available.short_description = "Mark selected drivers as available"

    def get_queryset(self, request):
        
        return super().get_queryset(request).select_related("user", "current_ride")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        
        if db_field.name == "current_ride":
            kwargs["queryset"] = RideRequest.objects.filter(
                status__in=["accepted", "started"]
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(RideRequest)
class RideRequestAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        qs = qs.select_related("passenger", "driver")
        return qs.using('default')
    
    list_display = [
        "id",
        "passenger_info",
        "driver_info",
        "current_location_short",
        "destination_short",
        "status_badge",
        "payment_status_badge",
        "total_fare",
        "requested_at_short",
        "ride_duration",
    ]

    
    list_filter = ["status", "payment_status", "requested_at", "driver"]

    
    search_fields = [
        "passenger__username",
        "passenger__email",
        "driver__username",
        "current_location",
        "destination",
        "payment_reference",
    ]

    
    readonly_fields = [
        "requested_at",
        "accepted_at",
        "started_at",
        "completed_at",
        "cancelled_at",
        "paid_at",
        "driver_earnings_display",
    ]

    # Fieldsets for detailed view
    fieldsets = (
        (
            "Ride Information",
            {
                "fields": (
                    "passenger",
                    "driver",
                    "status",
                    ("requested_at", "accepted_at"),
                    ("started_at", "completed_at"),
                    "cancelled_at",
                )
            },
        ),
        (
            "Location Details",
            {
                "fields": (
                    "current_location",
                    ("pickup_latitude", "pickup_longitude"),
                    "destination",
                    ("destination_latitude", "destination_longitude"),
                )
            },
        ),
        (
            "Payment Information",
            {
                "fields": (
                    "payment_status",
                    "payment_reference",
                    "paid_at",
                    ("base_fare", "surge_multiplier"),
                    ("distance_fare", "time_fare"),
                    "total_fare",
                    "driver_earnings_display",
                )
            },
        ),
        (
            "Ride Metrics",
            {"fields": (("distance_km", "duration_min"),), "classes": ("collapse",)},
        ),
    )

    # Custom methods for display
    def passenger_info(self, obj):
        return f"{obj.passenger.username} ({obj.passenger.email})"

    passenger_info.short_description = "Passenger"

    def driver_info(self, obj):
        if obj.driver:
            return f"{obj.driver.username} ({obj.driver.email})"
        return "No driver assigned"

    driver_info.short_description = "Driver"

    def current_location_short(self, obj):
        return (
            obj.current_location[:30] + "..."
            if len(obj.current_location) > 30
            else obj.current_location
        )

    current_location_short.short_description = "Pickup"

    def destination_short(self, obj):
        return (
            obj.destination[:30] + "..."
            if len(obj.destination) > 30
            else obj.destination
        )

    destination_short.short_description = "Destination"

    def status_badge(self, obj):
        colors = {
            "pending": "orange",
            "accepted": "blue",
            "started": "green",
            "completed": "gray",
            "cancelled": "red",
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.status, "gray"),
            obj.get_status_display().upper(),
        )

    status_badge.short_description = "Status"

    def payment_status_badge(self, obj):
        colors = {
            "pending": "orange",
            "paid": "green",
            "failed": "red",
            "refunded": "blue",
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.payment_status, "gray"),
            obj.get_payment_status_display().upper(),
        )

    def requested_at_short(self, obj):
        return obj.requested_at.strftime("%b %d, %H:%M")

    requested_at_short.short_description = "Requested"

    def ride_duration(self, obj):
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            minutes = duration.total_seconds() / 60
            return f"{int(minutes)} min"
        return "-"

    ride_duration.short_description = "Duration"

    def driver_earnings_display(self, obj):
        return f"₦{obj.driver_earnings:,.2f}"

    driver_earnings_display.short_description = "Driver Earnings"

    # Admin actions
    actions = ["mark_as_completed", "mark_as_cancelled", "cleanup_old_rides"]

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status="completed", completed_at=timezone.now())
        self.message_user(request, f"{updated} rides marked as completed.")

    mark_as_completed.short_description = "Mark selected rides as completed"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status="cancelled", cancelled_at=timezone.now())
        self.message_user(request, f"{updated} rides marked as cancelled.")

    mark_as_cancelled.short_description = "Mark selected rides as cancelled"

    def cleanup_old_rides(self, request, queryset):
        deleted_count = RideRequest.cleanup_canceled_rides(days_old=7)
        self.message_user(request, f"Cleaned up {deleted_count} old cancelled rides.")

    cleanup_old_rides.short_description = "Clean up old cancelled rides (7+ days)"

    # Configuration
    list_per_page = 25
    date_hierarchy = "requested_at"
    ordering = ["-requested_at"]
