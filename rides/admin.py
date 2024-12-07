from django.contrib import admin

from rides.models import ChatMessage, PassengerRideRequest, Rating, RideDetails


@admin.register(RideDetails)
class RideDetailsAdmin(admin.ModelAdmin):
    def ride_id(self, obj):
        return f"RIDE-{obj.id:05d}"
    ride_id.short_description = 'Ride ID'

    list_display = ('ride_id', 'driver', 'start_location', 'end_location', 'start_time', 'available_seats', 'status', 'created_at')
    list_filter = ('status', 'start_time', 'created_at')
    search_fields = ('driver__email', 'start_location', 'end_location', 'id')
    readonly_fields = ('created_at', 'ride_id')
    ordering = ('-created_at',)
    date_hierarchy = 'start_time'


@admin.register(PassengerRideRequest)
class PassengerRideRequestAdmin(admin.ModelAdmin):
    def request_id(self, obj):
        return f"REQ-{obj.id:05d}"
    request_id.short_description = 'Request ID'

    def ride_id(self, obj):
        return f"RIDE-{obj.ride.id:05d}"
    ride_id.short_description = 'Associated Ride'

    def passenger_id(self, obj):
        return f"PASS-{obj.passenger.id:05d}"
    passenger_id.short_description = 'Passenger ID'

    list_display = ('request_id', 'passenger_id', 'ride_id', 'passenger', 'pickup_location', 'dropoff_location', 'seats_needed', 'status', 'payment_completed')
    list_filter = ('status', 'payment_completed', 'created_at')
    search_fields = ('passenger__email', 'pickup_location', 'dropoff_location', 'ride__driver__email', 'passenger__id')
    readonly_fields = ('created_at', 'request_id', 'ride_id', 'passenger_id')
    ordering = ('-created_at',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    def rating_id(self, obj):
        return f"RATING-{obj.id:05d}"
    rating_id.short_description = 'Rating ID'

    def ride_id(self, obj):
        return f"RIDE-{obj.ride.id:05d}"
    ride_id.short_description = 'Associated Ride'

    def from_user_id(self, obj):
        return f"USER-{obj.from_user.id:05d}"
    from_user_id.short_description = 'From User ID'

    def to_user_id(self, obj):
        return f"USER-{obj.to_user.id:05d}"
    to_user_id.short_description = 'To User ID'

    list_display = ('rating_id', 'ride_id', 'from_user_id', 'to_user_id', 'from_user', 'to_user', 'score', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('from_user__email', 'to_user__email', 'id')
    readonly_fields = ('created_at', 'rating_id', 'ride_id', 'from_user_id', 'to_user_id')
    ordering = ('-created_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    def message_id(self, obj):
        return f"MSG-{obj.id:05d}"
    message_id.short_description = 'Message ID'

    def ride_id(self, obj):
        return f"RIDE-{obj.ride.id:05d}"
    ride_id.short_description = 'Associated Ride'

    def sender_id(self, obj):
        return f"USER-{obj.sender.id:05d}"
    sender_id.short_description = 'Sender ID'

    def receiver_id(self, obj):
        return f"USER-{obj.receiver.id:05d}"
    receiver_id.short_description = 'Receiver ID'

    list_display = ('message_id', 'ride_id', 'sender_id', 'receiver_id', 'sender', 'receiver', 'short_message', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('sender__email', 'receiver__email', 'message', 'id')
    readonly_fields = ('timestamp', 'message_id', 'ride_id', 'sender_id', 'receiver_id')
    ordering = ('-timestamp',)

    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message'