# # your_project_name/asgi.py

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quiz_portal.settings')
django_asgi_app = get_asgi_application()
from quiz.routing import websocket_urlpatterns
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket":
        URLRouter(
            websocket_urlpatterns  # Your WebSocket URLs
        )
})


