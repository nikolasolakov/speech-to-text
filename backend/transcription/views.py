import logging
import os
import tempfile
from pathlib import Path

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AudioUploadSerializer
from .services import transcribe_audio_file

logger = logging.getLogger(__name__)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class TranscribeView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AudioUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        audio_file = serializer.validated_data["audio_file"]
        suffix = Path(audio_file.name).suffix or ".webm"
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                for chunk in audio_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            text = transcribe_audio_file(temp_path)
            return Response({"text": text}, status=status.HTTP_200_OK)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Transcription failed")
            return Response(
                {"error": "Transcription failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
