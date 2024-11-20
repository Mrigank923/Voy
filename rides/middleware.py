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
        access_token = AccessToken(token)
        user = User.objects.get(
            id=access_token["user_id"]
        )  # user from the database using the ID in the token(login ke time pe)
        return user
    except Exception:
        return AnonymousUser()  # for any invalid user


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])

        if b"authorization" in headers:  # authorization must be there.

            try:
                token_name, token_key = (
                    headers[b"authorization"].decode().split()
                )  # for extracting the token
                if token_name.lower() == "bearer":
                    scope["user"] = await get_user_from_token(
                        token_key
                    )  # tnow the user associating with the token asynchronously

            except Exception:

                scope["user"] = AnonymousUser()  # for any error occurring

        else:
            scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)  # will furthur proceed
