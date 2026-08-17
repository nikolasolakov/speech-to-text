from django.urls import path

from .views import HealthView, TranscribeView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("transcribe/", TranscribeView.as_view(), name="transcribe"),
]
