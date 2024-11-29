from django.contrib import admin

from rides.models import ChatMessage, PassengerRideRequest, Rating, RideDetails


@admin.register(RideDetails)
class RideDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'driver', 'start_location', 'end_location', 'start_time', 'available_seats', 'status', 'created_at')
    list_filter = ('status', 'start_time', 'created_at')
    search_fields = ('driver__email', 'start_location', 'end_location')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'start_time'

@admin.register(PassengerRideRequest)
class PassengerRideRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'passenger', 'ride', 'pickup_location', 'dropoff_location', 'seats_needed', 'status', 'payment_completed')
    list_filter = ('status', 'payment_completed', 'created_at')
    search_fields = ('passenger__email', 'pickup_location', 'dropoff_location', 'ride__driver__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('ride', 'from_user', 'to_user', 'score', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('from_user__email', 'to_user__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('ride', 'sender', 'receiver', 'short_message', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('sender__email', 'receiver__email', 'message')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)

    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message'