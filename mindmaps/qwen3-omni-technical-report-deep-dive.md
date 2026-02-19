# Qwen3-Omni Technical Report
## Problem & Motivation
### Modality Trade-offs
- LLM-centric multimodal models often exhibit performance degradation in one modality when improved in others
- Goal: A single model that maintains state-of-the-art (SOTA) performance across text, image, audio, and video without degradation

### Interaction Requirements
- Need for natural real-time speech and fluent text
- Reducing first-packet latency in streaming synthesis for high concurrency in industrial-scale deployments


## Architecture / Method
### Thinker-Talker MoE Architecture
#### Thinker
- Mixture-of-Experts (MoE) Transformer
- 30B total parameters, 3B active parameters (30B-A3B)
- Handles perception and reasoning for text, image, audio, and video

#### Talker
- MoE Transformer
- 3B total parameters, 0.3B active parameters (3B-A0.3B)
- Conditions only on audio and visual features (decoupled from Thinker text representations)
- Generates streaming speech tokens using a multi-codebook autoregressive scheme


### Perception Components
#### Audio Transformer (AuT)
- 0.6B parameter attention-encoder-decoder model
- Trained on 20 million hours of supervised audio
- Downsamples audio 8x to a token rate of 12.5 Hz (80ms segments)
- Uses flash attention with dynamic window sizes (1 to 8 seconds)

#### Vision Encoder
- SigLIP2-So400m-based architecture
- Approximately 543 million parameters
- Handles both image and video via dynamic frame rate sampling

#### TM-RoPE
- Time-aligned Multimodal Rotary Position Embedding
- Redistributes rotary angles: 24 temporal, 20 height, 20 width
- Anchored to absolute time (80ms per temporal ID) to support arbitrary streaming duration


### Generation & Streaming Modules
#### MTP Module
- 80M parameter ultra-lightweight dense Transformer
- Predicts residual codebooks for the current frame to enhance vocal expressivity

#### Code2Wav Renderer
- 200M parameter lightweight causal ConvNet
- Replaces block-wise diffusion/DiT for immediate frame-by-frame synthesis



## Training
### Pretraining Stages
#### S1: Encoder Alignment
- Locks LLM parameters
- Trains vision and audio adapters/encoders separately

#### S2: General Phase
- 2 trillion tokens total
- Distribution: 0.57T text, 0.77T audio, 0.82T image, 0.05T video, 0.05T video-audio

#### S3: Long Context
- Increases max token length from 8,192 to 32,768
- Increases proportion of long audio/video data


### Post-training Pipelines
#### Thinker Training
- Lightweight SFT for instruction following
- Strong-to-Weak Distillation (Alignment with Qwen3-235B)
- GSPO (Generalized Step-level Preference Optimization) with Rule-based and Model-based (LLM-as-a-judge) rewards

#### Talker Training
- Stage 1: Mapping multimodal representations to speech
- Stage 2: Continual Pretraining (CPT) for hallucination reduction
- Stage 3: DPO for multilingual stability
- Stage 4: Speaker fine-tuning for naturalness and expressiveness



## Key Results
### Audio & Audiovisual Benchmarks
- Open-source SOTA on 32 out of 36 benchmarks
- Overall SOTA on 22 benchmarks
- Outperforms Gemini-2.5-Pro, Seed-ASR, and GPT-4o-Transcribe

### Specific Metrics
#### ASR (WER)
- Librispeech Clean/Other: 1.22 / 2.48
- Wenetspeech Meeting: 4.69 / 5.89
- Fleurs-en: 2.72

#### Latency
- Theoretical end-to-end first-packet latency: 234 ms (Audio), 547 ms (Video)
- Generation Real Time Factor (RTF) remains < 1 under high concurrency

#### Music Understanding
- RUL-MuchoMusic: 52.0 (New SOTA)
- GTZAN Accuracy: 93.0

#### Text Reasoning
- GPQA: 73.1 (Thinking model)
- AIME25: 73.7 (Thinking model)
- ZebraLogic: 76.1 (Instruct model)


### Zero-Shot TTS
- SEED test-en WER: 1.39
- Competitive with dedicated systems like F5-TTS and CosyVoice 3


## Contributions
### Model Parity

### AuT Encoder

### Thinking Model

### Streaming Innovation

### Audio Captioner


## Available Resources
### Open Source Release
- Qwen3-Omni-30B-A3B (Base/Instruct)
- Qwen3-Omni-30B-A3B-Thinking
- Qwen3-Omni-30B-A3B-Captioner

### License

### Capabilities
- Text interaction: 119 languages
- Speech understanding: 19 languages
- Speech generation: 10 languages
- Long audio support: Up to 40 minutes per instance


