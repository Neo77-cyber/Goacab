import os
from django.core.asgi import get_asgi_application
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Gocabservices.settings.production")
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