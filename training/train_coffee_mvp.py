"""Fine-tune a small MobileNetV2 coffee classifier and export browser assets."""
from __future__ import annotations

import json
import os
from pathlib import Path

import tensorflow as tf

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
tf.keras.utils.set_random_seed(42)
ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "coffee-pilot"
OUTPUT = ROOT / "artifacts" / "coffee-mvp"
IMAGE_SIZE = 160
BATCH_SIZE = 16
EPOCHS = 12
LABELS = ["Cerscospora", "Healthy", "Leaf_rust", "Miner", "Phoma"]


def datasets() -> tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset]:
    train = tf.keras.utils.image_dataset_from_directory(
        DATA, labels="inferred", label_mode="int", class_names=LABELS,
        validation_split=.20, subset="training", seed=42, image_size=(IMAGE_SIZE, IMAGE_SIZE), batch_size=BATCH_SIZE,
    )
    heldout = tf.keras.utils.image_dataset_from_directory(
        DATA, labels="inferred", label_mode="int", class_names=LABELS,
        validation_split=.20, subset="validation", seed=42, image_size=(IMAGE_SIZE, IMAGE_SIZE), batch_size=BATCH_SIZE,
    )
    # The small MVP subset has no independent test set. Use its held-out split
    # only for model selection and label it clearly in the model card.
    return train, heldout, heldout


def main() -> None:
    if not DATA.exists() or any(not (DATA / label).exists() for label in LABELS):
        raise SystemExit("Run download_coffee_pilot.py before training.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    train, validation, _ = datasets()
    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"), tf.keras.layers.RandomRotation(.08),
        tf.keras.layers.RandomContrast(.10),
    ])
    backbone = tf.keras.applications.MobileNetV2(
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3), include_top=False, alpha=.35, weights="imagenet"
    )
    backbone.trainable = False
    inputs = tf.keras.Input((IMAGE_SIZE, IMAGE_SIZE, 3), name="image")
    x = augmentation(inputs)
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = backbone(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(.25)(x)
    outputs = tf.keras.layers.Dense(len(LABELS), activation="softmax", name="coffee_health")(x)
    model = tf.keras.Model(inputs, outputs, name="cropsignal_coffee_pilot")
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    checkpoint = OUTPUT / "best.keras"
    model.fit(train.prefetch(tf.data.AUTOTUNE), validation_data=validation.prefetch(tf.data.AUTOTUNE), epochs=EPOCHS,
              callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
                         tf.keras.callbacks.ModelCheckpoint(checkpoint, monitor="val_accuracy", save_best_only=True)])
    best = tf.keras.models.load_model(checkpoint)
    metrics = best.evaluate(validation.prefetch(tf.data.AUTOTUNE), return_dict=True, verbose=0)
    best.save(OUTPUT / "coffee_mvp.keras")
    (OUTPUT / "class_indices.json").write_text(json.dumps(dict(enumerate(LABELS)), indent=2), encoding="utf-8")
    (OUTPUT / "metrics.json").write_text(json.dumps({"heldout_development_split": {key: float(value) for key, value in metrics.items()}}, indent=2), encoding="utf-8")
    print(json.dumps({"labels": LABELS, "heldout_development_split": metrics}, indent=2, default=float))


if __name__ == "__main__":
    main()
