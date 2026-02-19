# Robust Speech Recognition via Large-Scale Weak Supervision (Whisper)
## Problem & Motivation
### Generalization Gap
- Traditional supervised ASR models overfit to specific datasets (e.g., LibriSpeech).
- Performance drops significantly when applied to out-of-distribution (OOD) data (noise, accents, technical jargon).

### Pre-training vs. Zero-shot
- Self-supervised models (e.g., wav2vec 2.0) require manual fine-tuning on clean data.
- Goal: Create a model that works 'out of the box' across diverse domains without fine-tuning.

### Robustness
- Existing systems are brittle to recording conditions.
- Human speech recognition is highly robust; ASR should match this capability.


## Architecture / Method
### Frontend
- Audio sampled at 16,000 Hz.
- Input: 80-channel log-Magnitude Mel Spectrogram.
- Window size: 25ms, Stride: 10ms.
- Input segmented into 30-second fixed-length chunks (padded or truncated).

### Encoder
- Transformer-based architecture.
- Two 1D convolutional layers with filter size 3 and stride 2 (subsampling).
- Sinusoidal Positional Embeddings.
- Stack of Transformer blocks (Self-attention + MLP).

### Decoder
- Transformer-based decoder.
- Cross-attention over encoder hidden states.
- Sinusoidal Positional Embeddings.
- Learned task-specific prompting via special tokens.

### Multitask Format
#### Special Tokens
- <|startoftranscript|>: Signals beginning of prediction.
- <|en|>, <|fr|>, etc.: Language Identification (LID) tokens.
- <|transcribe|>: Task token for ASR.
- <|translate|>: Task token for Speech-to-English translation.
- <|notimestamps|>: Toggle for timestamp prediction.

#### Timestamps
- Predicts relative timestamps within the 30s window.
- Quantized at 20ms resolution.



## Training
### Dataset
- Total: 680,000 hours of multilingual/multitask audio.
- 438,000 hours of English speech + transcripts.
- 126,000 hours of non-English speech + transcripts.
- 117,000 hours of X-to-English translation data.

### Data Processing
- Weak supervision: Transcripts collected from the internet.
- Automated filtering: Removed machine-generated captions and low-quality transcriptions using heuristics (e.g., lack of punctuation, uppercase-only).

### Procedure
- Loss: Cross-entropy (standard sequence-to-sequence objective).
- Optimizer: AdamW with linear learning rate decay.
- Batch size: 256 segments.
- Trained across multiple model sizes for scaling analysis.


## Key Results
### Zero-shot Performance
- Whisper matches or exceeds fully supervised models on many datasets without seeing a single training sample from them.
- Competitive on LibriSpeech (though not SOTA) but significantly more robust on OOD benchmarks like Fleurs or Common Voice.

### Robustness Comparison
- At the same LibriSpeech WER, Whisper is significantly more robust to background noise than Wav2vec 2.0.
- Approaches human-level robustness and accuracy on several benchmarks.

### Scaling Laws
- Error rate decreases predictably as model capacity and dataset size increase.
- Multilingual performance improves English ASR due to cross-lingual transfer.

### Language Support
- Strong performance on high-resource languages.
- Translation capability (X-to-English) outperforms many dedicated supervised translation models.


## Contributions
### Large-scale Weak Supervision

### Unified Multitask Architecture

### Zero-shot Generalization

### Robustness Benchmark


## Available Resources
### Models
- Tiny: 39M parameters
- Base: 74M parameters
- Small: 244M parameters
- Medium: 769M parameters
- Large: 1550M parameters

### Software
- Official Python implementation available via 'openai/whisper' GitHub repository.
- Inference code and pre-trained weights released under MIT license.


