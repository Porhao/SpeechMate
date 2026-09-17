# SpeechMate TODO / Roadmap

This document outlines the detailed action items required to complete the SpeechMate project from Phase 5 to Phase 8, as defined in the Interim Report and IEEE paper.

## Phase 5: Data Collection & AI Model Training
*Status: Currently Underway*

- [ ] **Data Collection & Preparation**
  - Collect local Malaysian English and code-switched (Manglish) speech/video samples from consenting volunteers across casual, mock interview, and presentation scenarios.
  - Generate synthetic disfluent data by injecting controlled stutters into standard Malaysian-accented reading transcripts using a Stutter-TTS approach to augment the training set.
  - Conduct a lightweight manual annotation pass to mark filler words, repetitions, and prolonged pauses, cross-checking with automated Whisper transcripts.
- [ ] **Model Development & Refinement**
  - Implement and train the Stuttering/Disfluency Detection model (CNN + BiLSTM with attention mechanism) on UCLASS, SEP-28K, and locally augmented data.
  - Tune the Goodness of Pronunciation (GOP) forced-alignment scoring. Deliberately relax acceptance thresholds to account for Malaysian-English regional variations and avoid penalizing anxious speakers for measurement noise.
  - Refine the MediaPipe-based gaze tracking mapping to robustly classify the tri-zone (left/right/slide) gaze distribution metric using only a standard webcam.
- [ ] **Initial Benchmarking**
  - Record initial baseline metrics for Word Error Rate (WER), Precision, Recall, and F1 scores against the evaluation framework.

## Phase 6: Front-End and Back-End Development
*Status: Planned*

- [ ] **Front-End (Next.js / Tailwind CSS)**
  - Develop the User Management interfaces (authentication, profile, goal tracking).
  - Implement the **Practice Session Interface**: Ensure strict adherence to the *Deferred Feedback* design (i.e., display a silent elapsed timer, hide all on-screen scores, warnings, or live metrics to reduce cognitive load).
  - Implement the **Performance Dashboard**: Build the post-session UI containing summary scorecards, radar charts comparing previous sessions, AI coach feedback, and PDF report generation using Recharts.
- [ ] **Back-End (FastAPI)**
  - Develop core API routes: `auth`, `users`, `practice`, `speech`, `vision`, `coach`, `reports`.
  - Set up asynchronous processing (e.g., Celery) to handle the heavy AI pipeline analysis in the background once a session ends.
- [ ] **Integration**
  - Connect the Next.js frontend state management (Zustand) with the FastAPI back-end endpoints.

## Phase 7: System Integration & Unit Testing
*Status: Planned*

- [ ] **Pipeline Integration**
  - Integrate the distinct Speech and Vision analysis models into a unified multimodal pipeline (`app/ai/pipeline.py`).
  - Implement the **Gaze Tunneling** metric: Write the logic to compute the Pearson correlation between gaze aversion and vocal disfluency timestamps over a shared timeline.
  - Connect the LLM (Gemini Flash) to the analysis outputs to generate structured, concrete, moment-anchored feedback rather than generic advice.
- [ ] **Testing & QA**
  - Conduct unit testing across all modules.
  - Launch internal User Acceptance Testing (UAT) using the planned questionnaire to test whether the system reduces speaking anxiety and effectively delivers actionable feedback.

## Phase 8: Validation, Evaluation & Final Deployment
*Status: Planned*

- [ ] **Technical Validation**
  - Conduct a full technical evaluation using the pre-registered framework (e.g., WER reduction vs baseline, Pronunciation correlation ≥ 0.7, Disfluency F1 ≥ 0.75, Gaze accuracy ≥ 0.8).
  - Compare qualitative UAT findings against the objectives derived from Cognitive Load Theory (i.e., do users feel more prepared and less interrupted?).
- [ ] **Final Tuning & Deployment**
  - Perform final parameter adjustments and diagnostic fixes based on evaluation results (e.g., addressing pronunciation scoring inconsistencies).
  - Finalize documentation and deploy the complete prototype.
  - Compile the final project report summarizing the quantitative results and user acceptance findings.
