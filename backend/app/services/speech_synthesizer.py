"""Speech synthesis (Ideal Agent Stage 3): script text → narration WAV per slide.

Fallback chain, per slide, so the pipeline never hard-fails on audio:
    1. ElevenLabs instant voice clone of the user's sample (only when
       ELEVENLABS_API_KEY is set and a sample was uploaded — optional)
    2. Local Malaysian TTS (mesolitica/Malaysian-TTS-0.6B-v1), open source,
       in the deck's chosen narrator voice — the default
    3. OpenAI TTS with a standard voice (needs OPENAI_API_KEY)
    4. espeak-ng, local and offline (robotic, but free)
    5. Silence sized to the script length (video still renders)
"""

import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import settings
from app.services import malaysian_tts
from app.services.ai import count_words, get_openai_client, with_retries
from app.services.media import MediaError, normalize_to_wav, run_command, write_silence_wav

logger = logging.getLogger(__name__)

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

# Human-readable labels used in session warnings
SOURCE_LABELS = {
    "elevenlabs_clone": "your cloned voice",
    "malaysian_tts": "the local Malaysian TTS voice",
    "openai_tts": "a standard AI voice",
    "espeak": "the offline espeak voice",
    "silence": "silent placeholder audio",
}


@dataclass
class VoiceContext:
    """Per-session voice state. voice_id is set when cloning succeeded."""
    voice_id: str | None = None
    clone_error: str | None = None
    narrator_voice: str | None = None  # Malaysian TTS speaker id


class SpeechSynthesizer:
    async def prepare_voice(
        self, session_id: str, voice_sample: Path | None, narrator_voice: str | None = None
    ) -> VoiceContext:
        """Create an ElevenLabs instant voice clone from the user's sample, if possible."""
        if voice_sample is None:
            return VoiceContext(clone_error="No voice sample was provided", narrator_voice=narrator_voice)
        if not settings.elevenlabs_api_key:
            return VoiceContext(
                clone_error="Voice cloning needs ELEVENLABS_API_KEY", narrator_voice=narrator_voice
            )

        async def create() -> str:
            async with httpx.AsyncClient(timeout=settings.ai_timeout_sec) as http:
                with voice_sample.open("rb") as f:
                    resp = await http.post(
                        f"{ELEVENLABS_BASE}/voices/add",
                        headers={"xi-api-key": settings.elevenlabs_api_key},
                        data={"name": f"speechmate-{session_id[:8]}"},
                        files={"files": (voice_sample.name, f, "audio/wav")},
                    )
            if resp.status_code >= 400:
                raise RuntimeError(f"ElevenLabs voice clone HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json()["voice_id"]

        try:
            voice_id = await with_retries(create, attempts=2, label="ElevenLabs voice clone")
            logger.info("Created ElevenLabs voice %s for session %s", voice_id, session_id)
            return VoiceContext(voice_id=voice_id, narrator_voice=narrator_voice)
        except Exception as e:  # noqa: BLE001
            return VoiceContext(clone_error=f"Voice cloning failed: {e}", narrator_voice=narrator_voice)

    async def cleanup_voice(self, voice: VoiceContext) -> None:
        """Delete the temporary cloned voice so it doesn't use up the account's voice slots."""
        if not voice.voice_id:
            return
        try:
            async with httpx.AsyncClient(timeout=30) as http:
                await http.delete(
                    f"{ELEVENLABS_BASE}/voices/{voice.voice_id}",
                    headers={"xi-api-key": settings.elevenlabs_api_key},
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not delete ElevenLabs voice %s: %s", voice.voice_id, e)

    async def synthesize(self, text: str, out_wav: Path, voice: VoiceContext) -> str:
        """Synthesize `text` into `out_wav`. Returns the source used (see SOURCE_LABELS)."""
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        raw = out_wav.with_suffix(".raw")

        if voice.voice_id:
            try:
                audio = await with_retries(
                    lambda: self._elevenlabs_tts(text, voice.voice_id), label="ElevenLabs TTS"
                )
                raw.write_bytes(audio)
                await self._finish(raw, out_wav)
                return "elevenlabs_clone"
            except Exception as e:  # noqa: BLE001
                logger.error("Cloned-voice TTS failed, falling back: %s", e)

        if malaysian_tts.is_available():
            try:
                await asyncio.to_thread(malaysian_tts.synthesize, text, raw, voice.narrator_voice)
                await self._finish(raw, out_wav)
                return "malaysian_tts"
            except Exception as e:  # noqa: BLE001
                logger.error("Malaysian TTS failed, falling back: %s", e)

        client = get_openai_client()
        if client is not None:
            try:
                audio = await with_retries(lambda: self._openai_tts(client, text), label="OpenAI TTS")
                raw.write_bytes(audio)
                await self._finish(raw, out_wav)
                return "openai_tts"
            except Exception as e:  # noqa: BLE001
                logger.error("OpenAI TTS failed, falling back: %s", e)

        try:
            await self._espeak(text, raw)
            await self._finish(raw, out_wav)
            return "espeak"
        except MediaError as e:
            logger.error("espeak-ng failed, writing silence: %s", e)

        # ~2.5 words per second of natural speech
        write_silence_wav(out_wav, count_words(text) / 2.5)
        return "silence"

    async def _finish(self, raw: Path, out_wav: Path) -> None:
        try:
            await normalize_to_wav(raw, out_wav)
        finally:
            raw.unlink(missing_ok=True)

    async def _elevenlabs_tts(self, text: str, voice_id: str) -> bytes:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_sec) as http:
            resp = await http.post(
                f"{ELEVENLABS_BASE}/text-to-speech/{voice_id}",
                params={"output_format": "mp3_44100_128"},
                headers={"xi-api-key": settings.elevenlabs_api_key},
                json={"text": text, "model_id": settings.elevenlabs_model},
            )
        if resp.status_code >= 400:
            raise RuntimeError(f"ElevenLabs TTS HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.content

    async def _openai_tts(self, client, text: str) -> bytes:
        resp = await client.audio.speech.create(
            model=settings.tts_model,
            voice=settings.tts_voice,
            input=text,
            response_format="wav",
        )
        return resp.content

    async def _espeak(self, text: str, out: Path) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(text)
            text_file = f.name
        try:
            await run_command(
                [settings.espeak_bin, "-v", "en-us", "-s", "155", "-f", text_file, "-w", str(out)],
                timeout=120,
            )
        finally:
            Path(text_file).unlink(missing_ok=True)


speech_synthesizer = SpeechSynthesizer()
