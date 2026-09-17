"""
Stuttering Detection Engine

Real implementation: a signal-processing heuristic over the actual recorded
audio + ASR word timestamps — NOT a trained deep model. A CNN+BiLSTM
classifier (Mel Spectrogram -> CNN -> BiLSTM -> Attention -> Fluent /
Repetition / Prolongation / Block) is the intended production component for
this FYP, but training one needs a labelled dataset (e.g. SEP-28k + UCLASS)
and a separate training pipeline that doesn't exist in this repo yet. The
hook to swap in a trained checkpoint is left below.

Heuristic approach (real signal analysis, not fabricated):
- Repetition: consecutive identical/near-identical words in the transcript
  with a short inter-word gap (confirms a stutter repeat rather than a new
  sentence starting with the same word).
- Block: abnormally long silences inside an utterance (detected from the
  audio's RMS energy envelope via librosa.effects.split), excluding gaps
  that fall at the start/end of the clip or between long-tail sentences.
- Prolongation: sustained, low-variance voiced segments (stable RMS + low
  zero-crossing-rate) longer than a typical phoneme duration.
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Tunable thresholds
BLOCK_MIN_SECONDS = 1.2          # mid-utterance silence longer than this = block
PROLONGATION_MIN_SECONDS = 0.35  # sustained steady-energy voiced segment
REPETITION_MAX_GAP = 0.6         # seconds between repeated words to count as a stutter


class StutterType(str, Enum):
    FLUENT = "Fluent"
    REPETITION = "Repetition"
    PROLONGATION = "Prolongation"
    BLOCK = "Block"


@dataclass
class StutteringResult:
    stuttering_score: float         # 0–100 (higher = more stuttering)
    severity: str                   # None / Mild / Moderate / Severe
    repetition_count: int
    prolongation_count: int
    block_count: int
    detected_events: list[dict]     # [{type, start_time, end_time, word}]
    model_confidence: float


class StutteringDetector:
    """
    Signal-processing stuttering heuristic (see module docstring). The
    `use_real_model` flag/`_load_model` hook is kept so a trained
    CNN+BiLSTM checkpoint can be dropped in later without touching callers.
    """

    def __init__(self, use_real_model: bool = False):
        self.use_real_model = use_real_model
        self._model = None

        if use_real_model:
            self._load_model()

    def _load_model(self):
        # --- TRAINED MODEL HOOK (future work — needs SEP-28k/UCLASS + training) ---
        # import torch
        # from .models.cnn_bilstm import StutterCNNBiLSTM
        # self._model = StutterCNNBiLSTM.load_from_checkpoint("models/stuttering_v1.ckpt")
        # self._model.eval()
        pass

    async def detect(
        self,
        audio_path: str,
        transcript: str,
        word_timestamps: list[dict] | None = None,
    ) -> StutteringResult:
        if self.use_real_model and self._model:
            return await self._detect_trained_model(audio_path)
        if audio_path and Path(audio_path).is_file():
            try:
                return self._detect_heuristic(audio_path, transcript, word_timestamps or [])
            except Exception:
                logger.exception("Stuttering heuristic failed for %s — falling back to transcript-only", audio_path)
        return self._detect_transcript_only(transcript)

    async def _detect_trained_model(self, _audio_path: str) -> StutteringResult:
        # --- TRAINED MODEL INFERENCE (future work) ---
        # import librosa, torch, numpy as np
        # y, sr = librosa.load(audio_path, sr=16000)
        # mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, hop_length=512)
        # mel_db = librosa.power_to_db(mel, ref=np.max)
        # tensor = torch.FloatTensor(mel_db).unsqueeze(0).unsqueeze(0)
        # with torch.no_grad():
        #     logits = self._model(tensor)
        #     probs = torch.softmax(logits, dim=-1).numpy()
        # ... parse frame-level results into events
        return self._detect_transcript_only("")

    def _detect_heuristic(
        self, audio_path: str, transcript: str, word_timestamps: list[dict]
    ) -> StutteringResult:
        import librosa
        import numpy as np
        from ._audio import load_audio

        y, sr = load_audio(audio_path)
        events: list[dict] = []

        # --- Repetition: identical/near-identical consecutive words, close together ---
        repetitions = 0
        words = transcript.lower().split()
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                gap = None
                if i + 1 < len(word_timestamps) and i < len(word_timestamps):
                    gap = word_timestamps[i + 1]["start"] - word_timestamps[i]["end"]
                if gap is None or gap <= REPETITION_MAX_GAP:
                    repetitions += 1
                    events.append({
                        "type": StutterType.REPETITION.value,
                        "start_time": word_timestamps[i]["start"] if i < len(word_timestamps) else 0.0,
                        "end_time": word_timestamps[i + 1]["end"] if i + 1 < len(word_timestamps) else 0.0,
                        "word": words[i],
                    })

        # --- Block: long mid-utterance silences via RMS-based voice activity split ---
        blocks = 0
        if y.size > 0:
            intervals = librosa.effects.split(y, top_db=30)
            if len(intervals) > 1:
                total_duration = y.size / sr
                for i in range(len(intervals) - 1):
                    gap_start = intervals[i][1] / sr
                    gap_end = intervals[i + 1][0] / sr
                    gap_duration = gap_end - gap_start
                    is_mid_utterance = gap_start > 0.5 and gap_end < total_duration - 0.5
                    if gap_duration >= BLOCK_MIN_SECONDS and is_mid_utterance:
                        blocks += 1
                        events.append({
                            "type": StutterType.BLOCK.value,
                            "start_time": round(gap_start, 2),
                            "end_time": round(gap_end, 2),
                            "word": "",
                        })

        # --- Prolongation: sustained low-variance voiced segments ---
        prolongations = 0
        if y.size > 0:
            frame_length, hop_length = 1024, 256
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            zcr = librosa.feature.zero_crossing_rate(y, frame_length=frame_length, hop_length=hop_length)[0]
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

            voiced = (rms > np.percentile(rms, 40)) & (zcr < np.percentile(zcr, 60))
            run_start = None
            for i, is_voiced in enumerate(voiced):
                if is_voiced and run_start is None:
                    run_start = i
                elif not is_voiced and run_start is not None:
                    duration = times[i - 1] - times[run_start]
                    segment_rms = rms[run_start:i]
                    stability = 1 - (segment_rms.std() / (segment_rms.mean() + 1e-6))
                    if duration >= PROLONGATION_MIN_SECONDS and stability > 0.6:
                        prolongations += 1
                        events.append({
                            "type": StutterType.PROLONGATION.value,
                            "start_time": round(float(times[run_start]), 2),
                            "end_time": round(float(times[i - 1]), 2),
                            "word": "",
                        })
                    run_start = None

        total = repetitions + prolongations + blocks
        score = min(total * 8, 100)
        severity = (
            "None" if score == 0
            else "Mild" if score < 25
            else "Moderate" if score < 50
            else "Severe"
        )

        return StutteringResult(
            stuttering_score=float(score),
            severity=severity,
            repetition_count=repetitions,
            prolongation_count=prolongations,
            block_count=blocks,
            detected_events=sorted(events, key=lambda e: e["start_time"]),
            model_confidence=0.65,  # heuristic, not a trained classifier — lower confidence than a real model
        )

    def _detect_transcript_only(self, transcript: str) -> StutteringResult:
        """
        Fallback when no audio is available: transcript-only repetition
        pattern detection (used e.g. for the stub ASR path).
        """
        words = transcript.lower().split()
        repetitions = sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1])
        prolongations = len(re.findall(r"(.)\1{2,}", transcript))

        total = repetitions + prolongations
        score = min(total * 8, 100)
        severity = (
            "None" if score == 0
            else "Mild" if score < 25
            else "Moderate" if score < 50
            else "Severe"
        )

        return StutteringResult(
            stuttering_score=float(score),
            severity=severity,
            repetition_count=repetitions,
            prolongation_count=prolongations,
            block_count=0,
            detected_events=[],
            model_confidence=0.5,
        )


stuttering_detector = StutteringDetector()
