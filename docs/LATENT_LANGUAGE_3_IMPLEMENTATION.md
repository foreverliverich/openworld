# Latent Language 3.0 — executable integration

**Status:** first executable integration layer; not a claim that the complete research program is trained or scientifically validated.

This implementation follows the uploaded *Engine of Latent Language 3.0: Continuous Multimodal Morphogenetic AI Architecture* and the repository's master source reconciliation. The research document describes a 1,760-D base state and adds visual, audio and sensor subspaces. The resulting canonical layout is preserved exactly:

| Subspace | Dimensions | Current executable role |
|---|---:|---|
| Language | 768 | BERT-family text embedding |
| Emotion | 128 | ISCE projection plus explicit lexical baseline classifier |
| Cognition | 256 | ISCE projection plus explicit intent baseline |
| Memory | 512 | ISCE projection plus read-only similarity retrieval |
| Social | 64 | Explicit interaction metadata; no sensitive-trait inference |
| Temporal | 32 | Organism time/tick Fourier encoding |
| Visual | 512 | CLIP image embedding |
| Audio | 128 | Wav2Vec2 embedding through a trained 768→128 compressor |
| Sensor | 64 | Calibrated, named physical sensor channels |
| **Total** | **2,464** | Concatenated ephemeral working representation |

## Runtime dataflow

1. A modality observation arrives with source ID, timestamp and confidence.
2. A registered encoder produces a correctly sized vector. Missing encoders fail closed; there is no random-vector fallback.
3. Confidence-aware fusion updates only that modality's subspace. Stale observations are rejected.
4. The current ISCE state is projected into the ephemeral latent workspace. Latent state is not persisted as a second organism state and does not supersede ISCE.
5. Specialist processes execute concurrently against the same immutable snapshot and produce typed proposals and/or bounded subspace updates. Results are consolidated in stable specialist order.
6. The global workspace scores proposals by salience, confidence, urgency, novelty and estimated cost; it applies capacity and conflict limits and broadcasts the selected set.
7. A world mutation can occur only when a proposal is selected, evidence-bearing, confidence-qualified, unchanged since arbitration, within the current ISCE resource reserve, and still matches the current RealityEngine revision. The gateway charges the estimated cost through an ISCE transition before attempting the world mutation. An allowlist check runs before charging. If world validation then rejects the action, the estimate remains spent; this is deliberately conservative and prevents a committed action from escaping its resource debit. The gateway delegates the world mutation to the existing ChimeraToolbox/RealityEngine transaction boundary.
8. Bounded novelty from new encoded observations—and prediction error only when a trained dynamics model is present—is returned as an ISCE feedback contract. The runtime consumes that feedback on the next authoritative organism tick through OrganismKernel, so sensory surprise affects actual ISCE memory/physiology transitions rather than only a display value.

## Implemented components

- `chimera/latent_language.py`: 2,464-D schema, timestamped observation contracts, fusion, aligned-space similarity guard, ISCE projection, scene graph, specialist proposal contract, deterministic global workspace, and revision-checked cognitive action gateway.
- `chimera/encoders.py`: lazy-loaded BERT text, CLIP image and CLIP text shared-space adapters; Wav2Vec2 audio adapter; calibrated 64-channel sensor encoder. Heavy dependencies are optional.
- `chimera/latent_training.py`: trainable text/image/audio projection heads, symmetric InfoNCE alignment objective, audio 128-D bottleneck with reconstruction loss, evaluation metrics and checkpoint validation.
- `chimera/learned_dynamics.py`: trainable latent vector field, bounded RK4 integration, trajectory training, validation metrics, gradient clipping and schema-checked checkpoints. Untrained dynamics are prohibited from evolving the live latent state.
- `chimera/runtime.py`: queues cognition work onto the organism-owned tick, projects the current ISCE state, exposes the shared action gateway, and feeds prior-cycle novelty/prediction error into the next ISCE transition.
- Specialist calls run concurrently with deterministic result consolidation; latent and workspace maps are immutable snapshots.
- Specialist implementations: emotion lexical baseline, explicit-intent baseline, read-only memory retrieval, social interaction metadata, temporal encoding, spatial scene composition and structured creative artifact generation.

The specialist baselines are deliberately named as baselines. They are not substitutes for trained emotion/social models or a general-purpose reasoning model. The spatial composer creates validated symbolic scene blueprints and submits them through RealityEngine; it does not claim to produce photorealistic assets or run Blender/3D diffusion.

## Install model dependencies

The base engine and its tests remain standard-library-only. For pretrained encoder inference and model training:

```bash
python -m pip install -r requirements-latent.txt
```

The model adapters load public pretrained model weights on first construction. For a fully offline deployment, download and pin the model snapshots in advance, then pass local model directories as `model_id`. No model weights or API keys are embedded in this repository.

## Train cross-modal alignment

Use paired, semantically corresponding encoder outputs. Rows must align: row i in text must describe the same item/event as row i in image and optional audio. Do not train with independently shuffled modality batches.

- text: 768-D BERT mean-pooled embeddings
- image: 512-D CLIP image embeddings
- audio: 768-D Wav2Vec2 mean-pooled hidden states
- optional audio: row-aligned with text/image

The training class provides symmetric InfoNCE losses and an audio reconstruction constraint. Run `evaluate()` on a held-out split before using or checkpointing the audio compressor; retain recall@1, paired cosine and audio reconstruction metrics. The audio slot projection remains unavailable until paired audio training and held-out validation have both run. The repository does not include a project training corpus or claim that project weights have already been trained. Small synthetic tensors in the optional CI tests verify code paths only; they are not scientific training or validation evidence.

## Train morphogenetic dynamics

Collect versioned latent trajectories from real runtime cycles. Each row is one complete 2,464-D state; adjacent rows must be consecutive observations from the same trajectory. Separate train and validation trajectories by organism/session, not by randomly splitting adjacent timesteps.

The model learns a vector field from next-state prediction with bounded derivative, smoothness and norm-growth penalties. It integrates using RK4 and clamps the working vector to the documented range. A held-out trajectory set is mandatory before the model is marked deployable; `evolve()` refuses to run until training and validation have passed or a validated compatible checkpoint has been loaded. A trained checkpoint is still an empirical predictor, not proof of autonomous thought or subjective experience.

## Tests

```bash
python -m unittest discover -s tests -p "test_latent_language.py" -v
python -m unittest discover -s tests -v
```

The acceptance suite checks dimensions, provenance, confidence fusion, stale-observation rejection, scene-graph geometry, workspace capacity, proposal mutation protection, ISCE resource admission, sensor calibration, runtime feedback and committed RealityEngine effects. A separate CI job installs CPU PyTorch and executes both learned-model training/evaluation suites.

## Explicit remaining gates

This PR supplies executable interfaces and first working baselines; the following require additional data or infrastructure and are not represented as complete:

1. **Model training evidence:** no paired multimodal corpus or trained projection/dynamics checkpoints are included. Downloaded pretrained encoders are available after installing dependencies, but project-specific alignment and morphogenetic dynamics must be trained and evaluated on real Chimera trajectories.
2. **Specialist depth:** emotion and intent specialists are transparent deterministic baselines; social specialist encodes explicit interaction metadata only. Trained classifiers/LLM reasoning adapters and calibrated confidence are still required.
3. **Persistent episodic memory:** retrieval accepts records from the caller and does not create a competing memory database. A rebuildable index over the authoritative event journal must be wired with provenance and retention policy.
4. **Semantic scene parsing:** the spatial module consumes typed scene graphs; a language/vision parser that constructs those graphs and validates uncertainty is still required.
5. **Visual/audio sensor lifecycle:** browser capture, timestamp synchronization, worker ownership, permissions and durable sensor replay are not yet connected end-to-end.
6. **Creative asset backends:** structured scene/concept artifacts are implemented; image diffusion, mesh generation, Blender execution/export and behavioral animation backends remain separate adapters.
7. **Causal physiology experiments:** global-workspace and latent dynamics need CCPL intervention, sham, double-intervention and mediation batteries before any causal or consciousness-related interpretation.
8. **Legacy baseline policy:** the existing deterministic autonomous agent remains in place for compatibility. Its legacy direct construction path is not yet migrated to the new proposal gateway; all new Latent Language world actions use the gateway.

No component here establishes sentience or subjective experience. The evidence produced is software behavior, deterministic tests, model-training metrics and causal intervention results only.
