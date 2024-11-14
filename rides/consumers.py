from channels.generic.websocket import WebsocketConsumer
import json

class RideConsumer(WebsocketConsumer):
    def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.ride_group_name = f"ride_{self.ride_id}"

        #this is  to  Join ride group
        self.channel_layer.group_add(
            self.ride_group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        # this is to Leave ride group
        self.channel_layer.group_discard(
            self.ride_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']

        # after group joining user can Send message to ride group
        self.channel_layer.group_send(
            self.ride_group_name,
            {
                'type': 'ride_message',
                'message': message
            }
        )

    def ride_message(self, event):
        message = event['message']

        # msgs to be sent to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))
