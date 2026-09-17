# SpeechMate Technical Documentation

This document outlines the theoretical foundations, implementation architecture, model training configuration, and technical evaluation protocol for SpeechMate, an AI-powered communication and speech training assistant.

## 1. Theoretical Foundations

SpeechMate's design is heavily informed by pedagogical and cognitive research:

1. **Cognitive Load Theory (Sweller, 1988):** Limits to working memory mean that simultaneous presentation of spoken prompts, reading tasks, and live feedback causes cognitive overload.
   * **Design Impact:** Implementation of a *Pre-Presentation Scripting Assistant* to reduce intrinsic load beforehand, and a strictly *Deferred Feedback* interaction model that suppresses on-screen scores or warnings during active speech.
2. **Dual-Coding Theory (Mayer, 2001):** Visual and verbal channels compete for cognitive resources if forced to process disconnected information concurrently.
   * **Design Impact:** Avoids live text prompts during the practice session to prevent "Gaze Tunneling"—the phenomenon where users stare at text rather than practicing audience eye contact.
3. **Feedback Loops Framework (Carless, 2006; Butler & Winne, 1995):** Feedback is most effective when timed appropriately and structured actionably.
   * **Design Impact:** AI Feedback is provided in a single, cohesive post-session dashboard.

## 2. Core AI Pipeline & Models

SpeechMate processes multi-modal inputs (speech and video) using a pipeline of specialized models. All components currently prioritize local inference capabilities to support privacy (data minimization) and low deployment cost.

### 2.1 Speech Recognition (Dual-Engine Routing)
To address the prevalence of Malaysian English and English-Malay code-switching, SpeechMate avoids forcing a single general-purpose model to handle heavily accented or code-switched speech:
- **Primary Engine & Router:** `faster-whisper` (small, int8, CPU). Transcribes and provides language confidence scores.
- **Specialized Engine:** If Whisper confidence drops (indicating code-switching), the audio is routed to Mesolitica’s `wav2vec2-xls-r-300m-mixed` checkpoint (trained on Malay, Singlish, and Mandarin-mixed speech).
- **Code-Switching Detection:** A ~190-term Bahasa Malaysia/Manglish lexicon acts as a heuristic to estimate English-to-Malay ratio.

### 2.2 Stuttering & Disfluency Detection
- **Architecture:** CNN + BiLSTM with an attention mechanism (based on the FluentNet architecture by Kourkounakis et al., 2021).
- **Training Data:** UCLASS, SEP-28K, and planned augmentation via Gagap-TTS-style synthetic injection of disfluencies into Malaysian-accented reading transcripts, plus locally recorded samples.

### 2.3 Accent-Fair Pronunciation Scoring
- **Architecture:** Goodness of Pronunciation (GOP) forced-alignment scoring.
- **Design Impact:** Based on Mathad et al. (2021) which found forced-alignment errors weakly predict pronunciation scores. Thresholds are deliberately relaxed so that variations in Malaysian English phonology are not penalized as errors, ensuring that anxiety-prone users are only flagged for variations that impact intelligibility.

### 2.4 Presentation Behavior Analysis (Computer Vision)
- **Eye Contact / Gaze Tracking:** Re-implements Du, Zhang, and Lan’s (2026) wearable tri-zone gaze tracking using only a standard webcam. It utilizes MediaPipe face-mesh landmark extraction mapped to a tri-zone (left/right/slide) gaze-distribution metric.
- **Posture & Facial Expression:** MediaPipe Pose and facial landmarks coupled with a lightweight expression classifier (neutral/happy/nervous/confident).

### 2.5 Multimodal Fusion: The Gaze Tunneling Metric
Instead of treating vision and speech as parallel tracks, SpeechMate combines them on a shared session timeline.
- **Gaze Tunneling:** The Pearson correlation between gaze aversion (looking away from the audience) and speech disfluency events (pauses, filler words, stuttering). It mathematically identifies if a user looks away *because* they are struggling to speak.

### 2.6 AI Coach (LLM)
- **Engine:** Gemini Flash via API.
- **Function:** Handles intelligent dialogue generation for training scenarios (casual, interview, presentation) and generates structured, post-session recommendations.

## 3. Evaluation Protocol

A pre-registered technical evaluation framework ensures rigorous benchmarking of the system once model fine-tuning and integration (Phases 5-8) are complete.

| Component | Evaluation Method | Metric | Success Criterion |
|-----------|-------------------|--------|-------------------|
| **Speech Recognition** | Compare AI transcript with spoken text | Word Error Rate (WER) | Measurable WER reduction vs. baseline |
| **Fluency Analysis** | Compare AI analysis with manual observation | Speaking Rate (WPM), pause-detection accuracy | N/A |
| **Pronunciation Assessment**| Compare pronunciation scores with human evaluation | Pronunciation accuracy score | Correlation ≥ 0.7 |
| **Filler Word Detection** | Compare detected fillers with manually counted fillers | Detection accuracy | N/A |
| **Stuttering Detection** | Compare detected repetitions/pauses with manual annotation | Precision, Recall, F1-score | F1 ≥ 0.75; low false positives |
| **Eye Contact Detection** | Observe gaze direction compared with actual video | Detection accuracy | Accuracy ≥ 0.8 |
| **Posture & Expression** | Compare classification with manual observation | Classification accuracy | N/A |
| **Communication Score** | Compare AI score with supervisor rating | Correlation analysis | N/A |
| **Feedback Quality** | User Acceptance Testing (UAT) questionnaires | Likert scale | Significant gain in specificity/accuracy |
