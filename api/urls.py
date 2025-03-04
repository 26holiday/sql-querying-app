from django.urls import path
from .views import ProcessPromptView

urlpatterns = [
    path('process/', ProcessPromptView.as_view(), name='process-prompt'),
]
