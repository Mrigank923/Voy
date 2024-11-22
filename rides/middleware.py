from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

# getting the user custom model used
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token):
    try:
        # Add print statements for debugging
        print(f"Received Token: {token}")
        access_token = AccessToken(token)
        print(f"Decoded Token User ID: {access_token['user_id']}")
        
        user = User.objects.get(id=access_token["user_id"])
        print(f"Authenticated User: {user.email}")
        return user
    except Exception as e:
        print(f"Token Authentication Error: {e}")
        return AnonymousUser()

class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])
        
        # Add debug print statements
        print("WebSocket Connection Attempt")
        print(f"Available Headers: {headers}")

        if b"authorization" in headers:
            try:
                token_name, token_key = headers[b"authorization"].decode().split()
                print(f"Token Name: {token_name}, Token Key: {token_key}")
                
                if token_name.lower() == "bearer":
                    scope["user"] = await get_user_from_token(token_key)
            except Exception as e:
                print(f"Middleware Authentication Error: {e}")
                scope["user"] = AnonymousUser()
        else:
            print("No Authorization Header Found")
            scope["user"] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)