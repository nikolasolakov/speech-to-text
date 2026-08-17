from django.core.management.base import BaseCommand
import os

from transcription.services import get_whisper_model


class Command(BaseCommand):
    help = "Loads Whisper model at startup so model download/init happens before requests."

    def handle(self, *args, **options):
        model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
        self.stdout.write(f"Loading Whisper model ({model_size})...")
        get_whisper_model(model_size)
        self.stdout.write(self.style.SUCCESS("Whisper model is ready."))
