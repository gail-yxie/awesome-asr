# Qwen3-ASR Technical Report
## Problem & Motivation
### Paradigm Shift
- Transition from traditional E2E (Transducer/AED) to Large Audio-Language Model (LALM) paradigm
- Need to leverage LLM world knowledge and language modeling for ASR robustness

### Current Limitations
- Inconsistencies in ASR quality in real-world scenarios vs open benchmarks
- Lack of unified, multilingual forced alignment systems for LALMs
- Difficulty in balancing high accuracy with low latency for on-device deployment

### Functional Gaps
- Requirement for accurate word-level/sentence-level timestamps for subtitles
- Need for robustness to noise, accents, dialects, and singing voice


## Architecture / Method
### Model Family
- Qwen3-ASR-1.7B: SOTA open-source performance, competitive with proprietary APIs
- Qwen3-ASR-0.6B: Optimized for accuracy-efficiency trade-off and on-device deployment
- Qwen3-ForcedAligner-0.6B: LLM-based Non-Autoregressive (NAR) timestamp predictor

### Foundation Model
- Post-trained from Qwen3-Omni foundation model
- Inherits multi-modal understanding capabilities

### Audio Encoder (AuT)
- AED-based architecture with 8x downsampling
- Fbank features: 128 dimensions
- Token rate: 12.5Hz (80ms frame duration)
- Dynamic Flash Attention: Window sizes 1s to 8s for unified streaming/offline inference
- Parameters: 300M (for 1.7B model, 1024 hidden size) and 180M (for 0.6B model, 896 hidden size)

### Qwen3-ForcedAligner-0.6B Architecture
- Reframes forced alignment as a slot-filling task
- Uses [time] special tokens as word/character boundary slots
- Non-autoregressive (NAR) decoding for simultaneous timestamp prediction
- Supports speech inputs up to 300 seconds


## Training
### Four-Stage Pipeline
#### 1. AuT Pretraining
- AED framework with ~40 million hours of pseudo-labeled ASR data
- Focus on Chinese and English for stable audio representations

#### 2. Omni Pretraining
- Trained on 3 trillion tokens across audio, vision, and text tasks

#### 3. ASR Supervised Finetuning (SFT)
- Style transfer for input/output formatting
- Includes non-speech data, streaming-enhancement data, and context biasing
- Mitigates instruction injection by making it ASR-only (no instruction following)

#### 4. ASR Reinforcement Learning (RL)
- Utilizes Group Sequence Policy Optimization (GSPO)
- Data: 50k utterances (35% CN/EN, 35% Multilingual, 30% Functional)
- Improves noise robustness and transcription stability


### ForcedAligner Training
- Distilled and smoothed from Montreal Forced Aligner (MFA) pseudo-labels
- Causal training strategy to ensure global consistency without position offsets
- Dynamic slot insertion strategy to improve generalization


## Key Results
### ASR Performance
- Supports 30 languages and 22 Chinese dialects
- SOTA on WenetSpeech (4.97-5.88 CER) and LibriSpeech (1.63-3.38 WER)
- Outperforms Whisper-large-v3 and competitive with GPT-4o-Transcribe on internal robustness suites
- Robust to singing voice (M4Singer, Popcs) and full songs with BGM

### Inference Efficiency (0.6B Model)
- Average TTFT (Time-to-First-Token): 92ms
- Real-Time Factor (RTF): 0.064
- Throughput: 2,000 seconds of audio per second at concurrency 128

### Language Identification (LID)
- Average accuracy of 97.9% for 1.7B model across 4 benchmarks
- Stable performance on 30 languages including long-tail distributions

### Forced Alignment Accuracy
- Accumulated Average Shift (AAS) reduced by 67%~77% compared to MFA/NFA/WhisperX
- Maintains high accuracy on long utterances (300s) where baselines often degrade


## Contributions
### Unified Modeling
- First Large Language Model based speech forced aligner for flexible granularities
- Supports offline and streaming inference in a single model

### Capability Expansion
- Robust support for 52 languages and dialects
- Advanced singing-voice recognition and robustness to background music (BGM)

### Open Science
- Released model weights under Apache 2.0 license
- Open-source codebase for inference and fine-tuning recipes


## Available Resources
### Models
- Qwen/Qwen3-ASR-1.7B (HuggingFace)
- Qwen/Qwen3-ASR-0.6B (HuggingFace)
- Qwen/Qwen3-ForcedAligner-0.6B (HuggingFace)

### Code
- GitHub: QwenLM/Qwen3-ASR
- Unified toolkit for multi-granularity alignment, streaming, and SFT


