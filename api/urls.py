from django.urls import path
from .views import ProcessPromptView, TableSchemaView

urlpatterns = [
    path('process/', ProcessPromptView.as_view(), name='process-prompt'),
    path('tableschema/', TableSchemaView.as_view(), name='table-schema'),
]
