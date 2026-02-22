# ASR Deep Dive — TAC: Timestamped Audio Captioning

*arXiv: [2602.15766](https://arxiv.org/abs/2602.15766)*

Host: Welcome back to ASR Deep Dive. Today we're looking at a brand-new paper from Adobe Research, dropped on February 17th, 2026. It's called TAC: Timestamped Audio Captioning, and it tackles a problem that has quietly plagued Large Audio Language Models—their inability to disentangle overlapping sound events in complex acoustic scenes. Joining me to unpack this one is our expert. Welcome back.

Guest: Thanks. This is one of those papers that makes you say "of course, why didn't we do this sooner?" The core insight is deceptively simple: if you want a language model to truly *understand* audio, it needs to know not just *what* sounds are happening, but *when* they happen—down to the fraction of a second. TAC is a model that produces dense, temporally grounded audio descriptions at varying levels of detail and resolution. And the results are striking—state-of-the-art on dense captioning benchmarks with a hallucination rate of under five percent.

Host: Let's set the stage. What exactly is the problem with how current audio-language models handle complex scenes?

Guest: It's what the authors call a "supervision mismatch." Today's training datasets typically pair a 10-to-30-second audio clip with a single global caption—something like "a dog barks, then a car drives by." But in reality, those events overlap, they have specific onset and offset times, and there might be five other things happening underneath. When you train with that single-caption paradigm, you get what the paper calls "semantic collapse." The model learns to compress all the temporal detail into a brief summary. And when you ask it about specific moments, it hallucinates—it confidently describes sounds that aren't there.

Host: How bad is the hallucination problem in practice?

Guest: The paper benchmarks existing models like Audio Flamingo 3 and Qwen3-Omni, and they see hallucination rates around 10 to 12 percent. That means roughly one in ten sound events the model describes simply doesn't exist in the audio. For safety-critical applications—think surveillance, accessibility, or autonomous driving—that's unacceptable.

Host: So TAC solves this with timestamped captions. Walk me through the architecture.

Guest: TAC is built on top of Qwen2-Audio as its backbone. They freeze the base model and apply LoRA fine-tuning with a rank of 128. But the real magic is in the training data pipeline, not just the model. They created what they call the "Dynamic Acoustic Mixer"—a system that can generate essentially infinite synthetic audio mixtures from real-world sources. It takes isolated audio stems—speech, music, sound effects, ambient noise—and combines them according to structured "scene templates" that define temporal constraints and role bindings.

Host: So they're creating their own training data. How do they get the timestamps right?

Guest: This is the clever part. Instead of relying on human annotations, they use RMS-based activity detection on the individual stems *before* mixing. Since they know exactly when each source is active in the mix—because they created the mix—they get perfectly precise temporal labels for free. It's a form of "analysis by synthesis." You know the ground truth because you constructed the scene.

Host: That's elegant. But synthetic data can be brittle. How do they handle the simulation-to-reality gap?

Guest: Through what they call "dynamic supervision." During training, they vary three key parameters: merge threshold, activity threshold, and time resolution. The merge threshold controls how close two events need to be before they're described as one. The activity threshold controls the minimum loudness for a sound to be reported. And the time resolution controls how precisely timestamps are rounded. By randomly varying these during training, the model learns to be flexible—it can produce coarse overviews or fine-grained, frame-level descriptions depending on what you ask for.

Host: You mentioned varying levels of detail. How does that work at inference time?

Guest: TAC supports four controllable "knobs" per query. First is *style*—you can ask for keywords, a brief description, or a detailed narrative. Second is merge threshold. Third is activity threshold. And fourth is time resolution. So a user can say, "Give me a brief keyword-level description at one-second resolution," or "Give me a detailed description at 100-millisecond precision." It's fully controllable at inference time without retraining.

Host: Let's talk about results. How does TAC perform on dense captioning?

Guest: On the TACOS benchmark—which is the current standard for dense audio captioning—TAC achieves an Event F1 of 0.50 and a Segment F1 of 0.71. For comparison, Qwen3-Omni gets 0.37 Event F1, and Audio Flamingo 3 gets 0.27. So TAC is roughly 35 percent better than the next best model on event detection. And the hallucination rate is 4.9 percent—less than half of Audio Flamingo 3's 11.6 percent.

Host: Those are impressive numbers. But does the model actually understand audio, or is it just good at labeling events?

Guest: Great question, and this is where the "describe-then-reason" paradigm comes in. The authors show that TAC's dense captions can serve as a "semantic bridge" between audio and a text-only reasoning model. You feed audio into TAC, get a detailed timestamped description, and then hand that text to a strong language model like GPT-4o or Claude for reasoning. On the MMAR audio reasoning benchmark, this cascade approach scores 71.9 percent versus a 60.1 percent baseline—a 12-point improvement. On MMSU, it's 72.4 versus 62.3. The text-only reasoner can answer questions about audio it never "heard" because the description is rich enough.

Host: That's a powerful paradigm. It decouples perception from reasoning.

Guest: Exactly. And it has a practical benefit: you can upgrade the reasoning model independently of the audio model. When a better LLM comes out, you just swap it in. The audio front-end stays the same.

Host: Now, the paper also introduces TAC-V, an audiovisual variant. How does that work?

Guest: TAC-V is a five-stage pipeline. Stage one: run TAC on the audio track to get timestamped sound descriptions plus Whisper-based speech transcription. Stage two: use FLAM—a contrastive audio-text model—to score the confidence of each detected event, filtering out potential hallucinations. Stage three: create a "timestamped shot-list" by mapping audio events to video timestamps. Stage four: sample visual frames at those timestamps and analyze them with a vision-language model. Stage five: use the VLM to cross-check audio and visual information, correcting any remaining hallucinations.

Host: And the results on video benchmarks?

Guest: On DailyOmni, TAC-V scores 77.9 percent, beating Qwen3-Omni at 76.2 percent—that's a new state-of-the-art. On VideoHolmes, it gets 59.2 versus 57.3. And on the AVHBench hallucination detection task, it scores 81.7 percent on audio-visual hallucination and 76.6 percent on visual-audio hallucination. That's a massive improvement over end-to-end models like PandaGPT, which sits around 58 to 61 percent.

Host: The modality separation seems to be key. By not fusing audio and video early, they avoid the cross-modal hallucination problem.

Guest: Precisely. End-to-end multimodal models often "leak" information between modalities—they'll describe a sound that matches the visual but isn't actually in the audio, or vice versa. By keeping the modalities separate and reconciling them late, TAC-V gets the best of both worlds.

Host: Let's talk about the training details. How expensive is this to train?

Guest: Surprisingly modest. They used 8 NVIDIA A100 GPUs for 5,000 iterations. The LoRA approach means the base Qwen2-Audio weights are frozen—they're only training about 22 million additional parameters. There's also a pre-training stage on high-fidelity single-source audio with LLM-generated captions, which helps the model learn clean event-caption associations before tackling the harder polyphonic mixtures.

Host: What about the loss function? Anything special?

Guest: Yes, they use a weighted loss that gives extra emphasis to timestamp tokens. The total loss is the standard language modeling cross-entropy plus a timestamp-specific term weighted by lambda of 5.0. The intuition is that getting "a dog barks" right is one thing, but getting "a dog barks at 3.2 to 4.7 seconds" right requires extra precision. Without this weighting, the model tends to produce vague, imprecise timestamps.

Host: The ablation study must have been illuminating. What were the key findings?

Guest: Several things stood out. First, multitask training—varying the style, merge threshold, and activity threshold—is critical. When they trained with static settings, Event F1 dropped from 0.50 to 0.45. Second, the pre-training stage reduced hallucination from 8.8 percent to 4.9 percent. Third, LoRA rank matters a lot—rank 128 was optimal, and dropping to rank 8 caused what they called "model collapse" with Event F1 plummeting to 0.19. And fourth, scene templates for the acoustic mixer were important for generating realistic mixtures that transfer to real-world audio.

Host: Let's talk limitations. What should practitioners be aware of?

Guest: The paper is refreshingly honest about three issues. First, there's a simulation-to-reality gap. The synthetic mixer can overestimate dramatic or rare events because the templates may not perfectly match real-world distributions. Second, TAC isn't precise enough for music-specific descriptions—it can tell you "music is playing from 2 to 8 seconds" but it won't give you chord progressions or key signatures. And third, like all models trained on curated audio libraries, it inherits whatever biases exist in those libraries—certain sound categories may be over- or under-represented.

Host: If I'm a practitioner, what are my three takeaways from this paper?

Guest: Number one: Dense, timestamped audio descriptions are a fundamentally better representation than global captions. They enable downstream reasoning that was previously impossible. Number two: Synthetic data generation with precise temporal labels can overcome the annotation bottleneck that has been holding back audio understanding. You don't need millions of human-annotated clips—you need a smart mixing pipeline. And number three: The "describe-then-reason" cascade—where a specialized perception model feeds a general-purpose reasoner—is now competitive with and often better than end-to-end multimodal models. This has huge implications for system design.

Host: It really does feel like we're moving from "hear the audio" to "understand the scene." TAC treats audio not as a blob of features to classify, but as a rich temporal narrative to describe.

Guest: And that narrative becomes a universal interface. Any text-based model can now "hear" through TAC's descriptions. It's audio understanding as a service.

Host: This has been a fascinating deep dive into TAC from Adobe Research. Thank you for walking us through the Dynamic Acoustic Mixer, the multi-resolution captioning, and that elegant describe-then-reason paradigm.

Guest: My pleasure. Can't wait to see what people build with this.

Host: To our listeners—if you're working on audio understanding, dense captioning, or multimodal reasoning, this paper is a must-read. The arXiv link is 2602.15766. We'll see you in the next episode. Until then, keep listening.