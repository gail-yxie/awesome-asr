# TAC: Timestamped Audio Captioning
## Problem & Motivation
### Supervision Mismatch
- Existing datasets pair 10-30s clips with single global captions
- Causes "semantic collapse": temporal details compressed into brief summaries
- Global pooling supervision collapses temporal information

### Current LALM Limitations
- Struggle to disentangle overlapping events in complex acoustic scenes
- Temporally inconsistent descriptions
- High hallucination rates (10-12% in existing models)
- Cannot produce fine-grained temporal grounding

### Application Needs
- Safety-critical monitoring requires precise event localization
- Accessibility tools need accurate temporal descriptions
- Multimodal reasoning requires rich, structured audio representations


## Architecture / Method
### Dynamic Acoustic Mixer (Data Pipeline)
#### Scene Templates
- Structural specifications defining temporal constraints and role bindings
- Roles: speech, music, sound effects, background noise
- Generates infinite synthetic mixtures from real audio sources

#### RMS-based Activity Detection
- Precise temporal grounding via loudness proxies
- Timestamps derived from individual stems before mixing
- "Analysis by synthesis": ground truth from construction

#### Dynamic Supervision
- Varying merge thresholds (event fusion distance)
- Varying activity thresholds (minimum loudness sensitivity)
- Diverse supervision schedules during training

### Multitask Prompts & Output
#### Four Controllable Properties
- Style: keywords, brief, or detailed descriptions
- Merge Threshold: determines event fusion distance
- Activity Threshold: controls sound loudness sensitivity
- Time Resolution: rounding precision for timestamps

#### Structured Output Format
- Token-efficient concatenation of event labels with timestamps
- Synchronized temporal grounding for each event
- Enables reliable downstream parsing

### TAC Model
#### Backbone
- Qwen2-Audio (frozen weights)
- LoRA fine-tuning (rank 128, ~22M trainable parameters)

#### Pre-training
- Continued on high-fidelity single-source audio
- LLM-generated captions for clean event-caption associations

#### Loss Function
- Weighted combination: L_total = L_LM + λ_time * Σ CE(y_t, ŷ_t)
- λ_time = 5.0 for optimal timestamp precision
- Extra emphasis on timestamp tokens

#### Training
- 5,000 iterations on 8 NVIDIA A100 GPUs
- Speech segments processed through Whisper for transcription

### TAC-V: Audiovisual Extension
#### Five-Stage Pipeline
1. Audio processing via TAC + Whisper speech transcription
2. Event confidence scoring using FLAM (contrastive audio-text model)
3. Timestamped shot-list creation from audio events
4. Visual frame analysis at configurable rates (22fps)
5. VLM-based hallucination correction and visual grounding

#### Design Philosophy
- Late modality fusion to avoid cross-modal hallucination
- Audio and visual streams processed independently then reconciled
- Leverages best-in-class models for each modality


## Evaluation
### Metrics
#### Semantic Alignment
- LLM-based judge with bipartite matching (predicted vs. ground truth events)

#### Temporal Precision
- Segment-Based F1 (SegF1): 100ms resolution activity detection
- Event-Based F1 (EvtF1): discrete event evaluation with ±1.0s collar

#### Robustness
- Hallucination Rate: % of events below FLAM confidence threshold (τ=0.25)
- Confidence: audio-text similarity score
- Specificity: accuracy of duration descriptions

### Dense Captioning (TACOS Benchmark)
- Event F1: 0.50 (vs. Qwen3-Omni: 0.37, Audio Flamingo 3: 0.27)
- Segment F1: 0.71 (outperforming all competitors)
- Hallucination Rate: 4.9% (vs. Audio Flamingo 3: 11.6%)
- Confidence: 0.89 | Specificity: 0.74

### Audio Understanding & Reasoning
- MMAU: 73.9% accuracy (Audio Thinker: 75.9%)
- MMAR: 71.9% (+12% over baseline 60.1%)
- MMSU: 72.4% (+10% over baseline 62.3%)
- MMAU-Pro: 62.9% (baseline: 59.2%)

### Audiovisual Benchmarks (TAC-V)
- DailyOmni: 77.9% (SOTA, vs. Qwen3-Omni: 76.2%)
- VideoHolmes: 59.2% (vs. Qwen3-Omni: 57.3%)
- AVHBench AVH: 81.7% (vs. PandaGPT: 58.5%)
- AVHBench VAH: 76.6% (vs. PandaGPT: 61.3%)


## Key Ablations
### Multitask Training
- Static task settings: EvtF1 drops from 0.50 to 0.45
- Dynamic variation critical for generalization

### Pre-training Impact
- Reduces hallucination from 8.8% to 4.9%
- Clean single-source audio establishes event-caption priors

### LoRA Rank
- Rank 128: optimal performance
- Rank 8: model collapse (EvtF1 plummets to 0.19)

### Timestamp-Weighted Loss
- λ_time = 5.0 provides best balance
- Without weighting, timestamps become vague and imprecise

### Scene Templates
- Important for realistic mixture generation
- Improves transfer from synthetic to real-world audio


## Key Contributions
### Describe-Then-Reason Paradigm
- Decoupled perception (TAC) from reasoning (LLM)
- Text-only reasoners achieve expert-level multimodal performance
- Enables test-time scaling with stronger reasoners
- Audio understanding as a "semantic bridge"

### Dense Temporal Grounding
- SOTA on TACOS dense captioning benchmark
- Minimal hallucination (4.9%)
- Controllable detail and resolution at inference time

### Synthetic Data Pipeline
- Overcomes annotation bottleneck
- Infinite training data with precise temporal labels
- Dynamic supervision for robust generalization

### Audiovisual Integration
- TAC-V achieves SOTA on DailyOmni and VideoHolmes
- Late fusion avoids cross-modal hallucination
- Reference-free hallucination evaluation via FLAM


## Limitations & Future Work
### Current Limitations
- Simulation-to-reality gap: overestimation of dramatic events
- Insufficient precision for musical descriptions (chords, keys)
- Bias inheritance from source audio libraries

### Future Directions
- Unsupervised domain adaptation for event prior calibration
- Dense multimodal conditioning for audiovisual generation
- TAC as semantic encoder with text latents
- Expansion to other multimodal domains
