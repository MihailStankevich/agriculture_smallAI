# CropSignal Coffee Pilot — model card

## Intended decision

This is an **offline screening aid** for a farmer or extension worker who has
a close photo of a single Arabica coffee leaf. It can indicate one of five
visual conditions: Cercospora, healthy/no supported visible condition, leaf
rust, leaf miner, or Phoma. It must not prescribe treatment, confirm disease,
or replace a local extension worker.

## Data

The development subset is drawn reproducibly by
`training/download_coffee_pilot.py` from
`Project-AgML/arabica_coffee_leaf_disease_classification`, which republishes
JMuBEN and JMuBEN2. The original images were collected at Mutira coffee
plantation in Kirinyaga County, Kenya, under sunny, windy and cloudy
conditions, with pathologist-supported labels.

- Original labelled rows: 58,549 across five classes.
- MVP subset: 40 samples per class, downloaded across each class range.
- Classes: Cerscospora, Healthy, Leaf_rust, Miner, Phoma.
- Licence/source terms: verify the original JMuBEN/JMuBEN2 Mendeley records
  before production deployment; retain the source citation in any demo.

## Training and evaluation

`training/train_coffee_mvp.py` uses an ImageNet-pretrained MobileNetV2
(alpha 0.35) with a frozen backbone and a five-class head. Its reported metric
is an internal held-out development split only. It is **not** an independent
field evaluation and must not be presented as a real-world accuracy claim.

The public upstream dataset is known to contain many exact duplicates. The
subset is deliberately described as a prototype rather than an evaluation
dataset. Before a pilot, collect consented local images, deduplicate by leaf
and farm, evaluate by farm/location, and have local agronomists validate both
labels and guidance.

## Safeguards

- The app marks scores below 60% as uncertain and prevents community reporting.
- Photos never leave the phone. A saved signal only contains the label,
  confidence, time, optional observed conditions, and rounded location.
- Regional clusters are prioritisation signals, not outbreak confirmations.
- Kiswahili wording is a prototype; local partners must review it before use.

## Sources

- Jepkoech et al. (2021), *Arabica coffee leaf images dataset for coffee leaf
  disease detection and classification*, Data in Brief 36, 107142.
- JMuBEN: https://doi.org/10.17632/t2r6rszp5c.1
- JMuBEN2: https://doi.org/10.17632/tgv3zb82nd.1
