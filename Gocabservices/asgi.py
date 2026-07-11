import os
from django.core.asgi import get_asgi_application
import django

# Don't hardcode production — let the environment decide
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Gocabservices.settings.development")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import gocabapp.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(gocabapp.routing.websocket_urlpatterns)
    ),
})