
from django.urls import path
from .consumers import ExamConsumer

websocket_urlpatterns = [
    path(r'ws/exam/<uuid:exam_id>/', ExamConsumer.as_asgi()),
    # path(r'ws/exam/', MyAsyncJsonWebSocketConsumer.as_asgi()),
]


# from django.urls import path
# from .consumers import MyAsyncJsonWebSocketConsumer

# websocket_urlpatterns = [
#     # re_path(r'ws/exam/(?P<exam_id>[a-f0-9\-]+)/$', ExamConsumer.as_asgi(), name='exam'),
#     path(r'ws/exam/', MyAsyncJsonWebSocketConsumer.as_asgi()),
# ]
