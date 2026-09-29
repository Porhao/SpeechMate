"""Live-session analysis (camera + mic practice): speech, vision and scoring.

Heavy models are optional (requirements-ml.txt). Each stage uses a local
model when it's installed, falls back to a lighter real signal when one
exists (OpenAI Whisper, ffmpeg silence detection), and otherwise reports the
metric as unavailable with a warning — it never invents numbers.
"""
