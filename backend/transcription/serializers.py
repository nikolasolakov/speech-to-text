from pathlib import Path

from rest_framework import serializers


class AudioUploadSerializer(serializers.Serializer):
    audio_file = serializers.FileField(required=True)

    def validate_audio_file(self, value):
        allowed_extensions = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".mp4", ".flac"}
        ext = Path(value.name).suffix.lower()
        content_type = (getattr(value, "content_type", None) or "").lower()

        if ext and ext not in allowed_extensions:
            raise serializers.ValidationError("Unsupported audio format.")

        if content_type and not content_type.startswith("audio/"):
            raise serializers.ValidationError("Uploaded file must be an audio file.")

        return value
