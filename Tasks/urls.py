from django.urls import path, include

from Identity import views
from Tasks.views import ChatCompletionView

urlpatterns = [
    path('v1/chat/completions',  ChatCompletionView.as_view(), name='chat-completion'),
]