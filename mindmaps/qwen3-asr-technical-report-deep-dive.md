# Qwen3-ASR Technical Report
## Problem & Motivation
- Transition from traditional E2E (Transducer/AED) to Large Audio-Language Model (LALM) paradigm
- Leveraging LLM world knowledge and reasoning for challenging scenarios (long-form, noise, named entities)
- Need for robust multilingual and dialectal ASR (standard models often hit annotation error limits)
- Requirement for high-accuracy timestamps in ASR outputs (e.g., subtitles)
- Lack of a unified, multilingual, and efficient forced alignment system

## Architecture / Method
### Qwen3-ASR Family
- Models: Qwen3-ASR-1.7B (300M encoder + 1.7B LLM) and Qwen3-ASR-0.6B (180M encoder + 0.6B LLM)
- Foundation: Built on Qwen3-Omni with strong audio understanding
- AuT Encoder: AED-based, 8x downsampling, 12.5Hz token rate, 128-dim Fbank features
- Dynamic Flash Attention: Window size 1s to 8s supporting both streaming and offline inference
- Projector: Connects AuT encoder embeddings to the Qwen3 LLM backbone

### Qwen3-ForcedAligner-0.6B
- Formulation: Reframes forced alignment as a Non-Autoregressive (NAR) slot-filling task
- Special Tokens: Uses [time] tokens inserted into transcripts as timestamp slots
- Prediction: A linear layer predicts discrete timestamp indices (80ms frame duration)
- Capacity: Supports up to 300s audio (3,750 classes) with 11 languages


## Training
### ASR Training Pipeline
- Stage 1: AuT Pretraining - 40 million hours of pseudo-labeled data (primarily English/Chinese)
- Stage 2: Omni Pretraining - 3 trillion tokens across audio, vision, and text for multimodal capability
- Stage 3: ASR SFT - Style transfer on input/output formats, includes context biasing and streaming-enhancement data
- Stage 4: ASR RL - Group Sequence Policy Optimization (GSPO) using 50k utterances for noise robustness and stability

### ForcedAligner Training
- Data: Distillation and smoothing of pseudo-labels from Montreal Forced Aligner (MFA)
- Loss: Cross-entropy loss applied specifically to timestamp slots
- Strategy: Causal training with non-shifted sequences; dynamic slot insertion for generalization


## Key Results
### ASR Accuracy
- Qwen3-ASR-1.7B: SOTA among open-source models; competitive with GPT-4o and Gemini-2.5-Pro
- WenetSpeech (Mandarin): 4.97 CER (Meeting subset) for 1.7B model
- GigaSpeech (English): 8.45 WER for 1.7B model
- Dialects: Supports 22 Chinese dialects; 15.94 average CER on internal dialect suite

### Efficiency (0.6B Model)
- TTFT: Average as low as 92ms
- RTF: 0.064 at concurrency 128
- Throughput: Processes 2,000 seconds of audio per 1 second of wall time

### Forced Alignment
- Accuracy: 67% to 77% reduction in accumulated average shift (AAS) vs MFA/NFA/WhisperX
- AAS: 32.4ms on human-labeled test sets (vs 101.2ms for NFA)

### Specialized Tasks
- Singing Voice: Strong performance on M4Singer and Opencpop
- Song Transcription: Robust to background music (BGM) in long-form songs


## Contributions
### Novel Architecture

### Language Coverage

### Unified Inference

### Robustness

### Alignment Versatility


## Available Resources
### Models
- Qwen3-ASR-1.7B (HuggingFace)
- Qwen3-ASR-0.6B (HuggingFace)
- Qwen3-ForcedAligner-0.6B

### Code & Tools
- GitHub: https://github.com/QwenLM/Qwen3-ASR
- Inference framework: vLLM-based (ASR) and Transformers-based (FA)

### License


