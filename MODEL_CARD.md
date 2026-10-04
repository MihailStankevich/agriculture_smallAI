# Legacy PlantVillage classifier

> The field app now uses `model-coffee-v1/`, the five-class Arabica coffee
> pilot documented in [COFFEE_MODEL_CARD.md](COFFEE_MODEL_CARD.md). This file
> is kept only as provenance for the earlier multi-crop experiment; it is not
> loaded by the current app.

## Bundled model

The app bundles the public 38-class TensorFlow.js model published at TensorFlow Hub as `rishit-dagli/tfjs-model/plant-disease/default/1`. Its project documentation states that it accepts RGB images scaled to `[0, 1]` at 224 × 224 and emits logits for the original PlantVillage 38 labels. `model/class_indices.json` is the matching label map from that project's release.

The model and the TensorFlow.js runtime are stored locally under `model/` and `vendor/`. The service worker caches every model shard at installation. Therefore, prediction runs on-device after the initial connected install; the photo is never sent to the server.

## Intended use and safety

This is an **early screening and community-signal tool**, not a diagnosis or treatment recommendation. Do not present the model confidence as probability of disease. Reports are deliberately tagged as potential signals and must be reviewed by trained local extension staff before alerts or interventions.

PlantVillage contains mostly isolated leaves photographed under controlled conditions. It is not representative of ordinary farm photos with complex backgrounds, multiple leaves, shadows, pests, nutrient deficiencies, or unseen diseases. A high validation score on PlantVillage is not evidence of field performance.

## Upgrade path

`training/train_plantvillage.py` is a reproducible MobileNetV2 transfer-learning baseline; it downloads TFDS PlantVillage, freezes the ImageNet backbone, then lightly fine-tunes the last 30 layers. `training/export_tfjs.py` writes a TF.js Layers model to the folder the app loads. For a real pilot, add consented local images, hold out farms/regions rather than random images, measure per-class precision/recall and abstention behavior, and obtain agronomy review.
