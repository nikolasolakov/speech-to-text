import logging
import os
import threading

from faster_whisper import WhisperModel


logger = logging.getLogger(__name__)

_models: dict[str, WhisperModel] = {}
_model_lock = threading.Lock()


def _split_csv_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def _extract_text(segments) -> str:
    text_parts = [segment.text.strip() for segment in segments if segment.text]
    return " ".join(part for part in text_parts if part).strip()


def _is_probable_oom(exc: Exception) -> bool:
    message = str(exc).lower()
    patterns = [
        "out of memory",
        "cannot allocate memory",
        "std::bad_alloc",
        "oom",
    ]
    return any(pattern in message for pattern in patterns)


def get_whisper_model(model_size: str | None = None) -> WhisperModel:
    resolved_model_size = model_size or os.getenv("WHISPER_MODEL_SIZE", "small")
    cache_key = resolved_model_size.strip().lower()

    if cache_key in _models:
        return _models[cache_key]

    with _model_lock:
        if cache_key not in _models:
            device = os.getenv("WHISPER_DEVICE", "cpu")
            compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
            download_root = os.getenv("WHISPER_MODEL_DIR", "/models")
            cpu_threads = int(os.getenv("WHISPER_CPU_THREADS", "4"))

            _models.clear()
            _models[cache_key] = WhisperModel(
                model_size_or_path=cache_key,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
                cpu_threads=cpu_threads,
            )

    return _models[cache_key]


def _initial_prompt_for(language: str) -> str | None:
    prompt = os.getenv(f"WHISPER_INITIAL_PROMPT_{language.upper()}")
    return prompt.strip() if prompt and prompt.strip() else None


def _hotwords_for(language: str) -> str | None:
    hotwords = os.getenv(f"WHISPER_HOTWORDS_{language.upper()}")
    return hotwords.strip() if hotwords and hotwords.strip() else None


def _decode_kwargs() -> dict:
    return {
        "temperature": float(os.getenv("WHISPER_TEMPERATURE", "0.0")),
        "condition_on_previous_text": os.getenv("WHISPER_CONDITION_ON_PREVIOUS_TEXT", "false").lower() == "true",
        "patience": float(os.getenv("WHISPER_PATIENCE", "2.0")),
        "compression_ratio_threshold": float(os.getenv("WHISPER_COMPRESSION_RATIO_THRESHOLD", "2.4")),
        "log_prob_threshold": float(os.getenv("WHISPER_LOG_PROB_THRESHOLD", "-1.0")),
        "no_speech_threshold": float(os.getenv("WHISPER_NO_SPEECH_THRESHOLD", "0.6")),
    }


def _transcribe_with_model(file_path: str, model: WhisperModel, beam_size: int, allowed_languages: list[str]) -> str:
    decode_kwargs = _decode_kwargs()

    for language in allowed_languages:
        segments, _info = model.transcribe(
            file_path,
            beam_size=beam_size,
            language=language,
            vad_filter=True,
            initial_prompt=_initial_prompt_for(language),
            hotwords=_hotwords_for(language),
            **decode_kwargs,
        )
        text = _extract_text(segments)
        logger.info(
            "Forced-language transcription attempt: language=%s text_len=%d",
            language,
            len(text),
        )
        if text:
            return text

    auto_segments, auto_info = model.transcribe(file_path, beam_size=beam_size, vad_filter=True, **decode_kwargs)
    auto_text = _extract_text(auto_segments)
    auto_lang = getattr(auto_info, "language", None)
    logger.info(
        "Auto-detect transcription attempt: language=%s probability=%s text_len=%d",
        auto_lang,
        getattr(auto_info, "language_probability", None),
        len(auto_text),
    )

    if auto_text and (not allowed_languages or (auto_lang and auto_lang.lower() in allowed_languages)):
        return auto_text

    if auto_text:
        return auto_text

    raise ValueError("No speech could be transcribed from the audio.")


def transcribe_audio_file(file_path: str) -> str:
    primary_model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
    fallback_model_size = os.getenv("WHISPER_FALLBACK_MODEL_SIZE", "tiny")

    model = get_whisper_model(primary_model_size)
    beam_size = int(os.getenv("WHISPER_BEAM_SIZE", "1"))
    allowed_languages = _split_csv_env("WHISPER_ALLOWED_LANGUAGES", "mk,en")

    try:
        return _transcribe_with_model(file_path, model, beam_size, allowed_languages)
    except Exception as exc:
        same_model = fallback_model_size.strip().lower() == primary_model_size.strip().lower()
        if not same_model and _is_probable_oom(exc):
            fallback_model = get_whisper_model(fallback_model_size)
            return _transcribe_with_model(file_path, fallback_model, beam_size, allowed_languages)
        raise
