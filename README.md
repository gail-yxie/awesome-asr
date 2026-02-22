# Awesome ASR Speech Language [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

> A curated list of awesome Automatic Speech Recognition (ASR) and Speech Language Model resources — with daily tracking of the latest research, papers, Twitter/X discussions, and open-source models.

## Features

- **Curated Resources** — Hand-picked collection of ASR and speech language model papers, models, datasets, tools, and tutorials
- **Daily Tracking** — Automated tracking of new research papers, Twitter/X posts, and open-source ASR & speech language model releases
- **Podcast Generation** — Auto-generated audio podcasts summarizing the latest ASR and speech language developments
- **Ideas Summary** — Concise summaries of new ideas and breakthroughs in speech recognition and speech language models
- **Mindmap Generation** — Interactive mindmaps for exploring topics and connections (inspired by NotebookLM)

## Table of Contents

- [Leaderboards](#leaderboards)
- [Papers](#papers)
- [Open-Source Models](#open-source-models)
- [Datasets](#datasets)
- [Tools & Libraries](#tools--libraries)
- [Tutorials & Courses](#tutorials--courses)
- [Daily Updates](#daily-updates)
- [Podcasts](#podcasts)
- [Mindmaps](#mindmaps)
- [Contributing](#contributing)

## Leaderboards

- [Open ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard) — Explore and compare speech recognition model benchmarks. Maintained by [hf-audio](https://huggingface.co/hf-audio). [[Paper](https://arxiv.org/abs/2510.06961)]

### Top 10 Models (by Average WER)

<!-- leaderboard-top10-start -->
| Rank | Model | Avg WER |
|------|-------|---------|
| 1 | [nvidia/canary-1b](https://huggingface.co/nvidia/canary-1b) | 6.67% |
| 2 | [nvidia/parakeet-tdt-1.1b](https://huggingface.co/nvidia/parakeet-tdt-1.1b) | 6.95% |
| 3 | [nvidia/parakeet-rnnt-1.1b](https://huggingface.co/nvidia/parakeet-rnnt-1.1b) | 7.04% |
| 4 | [nvidia/parakeet-ctc-1.1b](https://huggingface.co/nvidia/parakeet-ctc-1.1b) | 7.58% |
| 5 | [nvidia/parakeet-rnnt-0.6b](https://huggingface.co/nvidia/parakeet-rnnt-0.6b) | 7.63% |
| 6 | [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3) | 7.7% |
| 7 | [nvidia/parakeet-ctc-0.6b](https://huggingface.co/nvidia/parakeet-ctc-0.6b) | 7.99% |
| 8 | [nvidia/stt_en_fastconformer_transducer_xlarge](https://huggingface.co/nvidia/stt_en_fastconformer_transducer_xlarge) | 8.06% |
| 9 | [openai/whisper-large-v2](https://huggingface.co/openai/whisper-large-v2) | 8.06% |
| 10 | [nvidia/stt_en_fastconformer_transducer_xxlarge](https://huggingface.co/nvidia/stt_en_fastconformer_transducer_xxlarge) | 8.07% |
<!-- leaderboard-top10-end -->

*Auto-updated daily. Evaluated on 9 ESB benchmark datasets (lower WER is better).*

## Papers

### Foundational

- [Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356) — Radford et al., OpenAI, Dec 2022. Introduced Whisper.
- [wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations](https://arxiv.org/abs/2006.11477) — Baevski et al., Meta, Jun 2020.
- [HuBERT: Self-Supervised Speech Representation Learning by Masked Prediction of Hidden Units](https://arxiv.org/abs/2106.07447) — Hsu et al., Meta, Jun 2021.
- [W2v-BERT: Combining Contrastive Learning and Masked Language Modeling for Self-Supervised Speech Pre-Training](https://arxiv.org/abs/2108.06209) — Chung et al., Google, Aug 2021.

### Recent

- [TAC: Timestamped Audio Captioning](https://arxiv.org/abs/2602.15766) — Kumar et al., Adobe Research, Feb 2026. Dense temporally grounded audio captioning with minimal hallucination; includes audiovisual variant TAC-V achieving SOTA on multimodal benchmarks.
- [Qwen3-ASR Technical Report](https://arxiv.org/abs/2601.21337) — Qwen Team, 2026. Multilingual ASR with language detection, timestamps, and forced alignment.

## Open-Source Models

| Model | Org | Date | Architecture | Key Innovation | Link |
|-------|-----|------|-------------|----------------|------|
| [Whisper Large V3](https://arxiv.org/abs/2212.04356) | OpenAI | Nov 2023 | Encoder-decoder Transformer (1.5B) | Trained on 5M hours of weakly/pseudo-labeled audio for 10-20% WER reduction | [HF](https://huggingface.co/openai/whisper-large-v3) |
| [Whisper Turbo](https://arxiv.org/abs/2212.04356) | OpenAI | Oct 2024 | Encoder-decoder Transformer, pruned decoder (809M) | Decoder pruned from 32 to 4 layers for 5-8x faster inference | [HF](https://huggingface.co/openai/whisper-large-v3-turbo) |
| [W2v-BERT](https://arxiv.org/abs/2108.06209) | hf-audio | Aug 2021 | Conformer with contrastive + MLM modules (0.6B) | Combines wav2vec 2.0 contrastive learning with BERT-style MLM in one model | [HF](https://huggingface.co/hf-audio/wav2vec2-bert-CV16-en) |
| [wav2vec 2.0](https://arxiv.org/abs/2006.11477) | Meta | Jun 2020 | CNN encoder + Transformer context network | Self-supervised contrastive learning over quantized speech, strong ASR with 10 min labeled data | [HF](https://huggingface.co/facebook/wav2vec2-base-960h) |
| [Qwen3-ASR-1.7B](https://arxiv.org/abs/2601.21337) | Alibaba Qwen | Jan 2026 | AuT audio encoder (300M) + Qwen3 LLM decoder | SOTA open-source ASR via GSPO reinforcement learning, 52 languages | [HF](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) |
| [Qwen3-ASR-0.6B](https://arxiv.org/abs/2601.21337) | Alibaba Qwen | Jan 2026 | AuT audio encoder (180M) + Qwen3 LLM decoder | Best accuracy-efficiency trade-off: 92ms TTFT, 2000x throughput | [HF](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) |
| [Qwen3-ForcedAligner](https://arxiv.org/abs/2601.21337) | Alibaba Qwen | Jan 2026 | Non-autoregressive LLM-based aligner on Qwen3 | First LLM-based forced aligner, 67-77% alignment error reduction | [HF](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) |
| [HuBERT](https://arxiv.org/abs/2106.07447) | Meta | Jun 2021 | CNN encoder + bidirectional Transformer (XL: 48 layers) | Masked prediction of k-means pseudo-labels for self-supervised speech | [HF](https://huggingface.co/facebook/hubert-xlarge-ls960-ft) |

## Datasets

| Dataset | Language | Hours | Description | Link |
|---------|----------|-------|-------------|------|
| ESB Datasets | Multi | — | End-to-end Speech Benchmark test sets | [Dataset](https://huggingface.co/datasets/hf-audio/esb-datasets-test-only-sorted) |
| ASR Leaderboard Longform | Multi | — | Long-form evaluation data for the Open ASR Leaderboard | [Dataset](https://huggingface.co/datasets/hf-audio/asr-leaderboard-longform) |

## Tools & Libraries

- [hf-audio](https://huggingface.co/hf-audio) — A one-stop shop for all things audio at Hugging Face. Maintains the Open ASR Leaderboard, ASR models, datasets, and audio codec models (Vocos, Xcodec).

## Tutorials & Courses

<!-- Educational resources -->

## Daily Updates

Daily updates are generated automatically via GitHub Actions (daily at 06:00 UTC) and stored in the [`daily/`](daily/) directory. Each report includes new papers from arXiv, ASR and speech language models from HuggingFace, and Twitter/X discussions.

## Podcasts

Daily podcast episodes summarizing ASR and speech language model developments are auto-generated and published as [GitHub Releases](https://github.com/gail-yxie/awesome-asr/releases). See the [`podcasts/`](podcasts/) directory for the episode index.

## Mindmaps

Interactive mindmaps exploring ASR and speech language model topics are regenerated weekly and available in the [`mindmaps/`](mindmaps/) directory. Rendered using [markmap](https://markmap.js.org/).

## Contributing

Contributions are welcome! Please read the [contributing guidelines](CONTRIBUTING.md) before submitting a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
