"""Train a compact, reproducible three-class Tomato PlantVillage MVP model."""
from __future__ import annotations

import json
import os
from pathlib import Path

import tensorflow as tf

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
tf.keras.utils.set_random_seed(42)
ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "PlantVillage-Dataset" / "raw" / "color"
OUTPUT = ROOT / "artifacts" / "tomato-mvp"
IMAGE_SIZE, BATCH_SIZE = 160, 32


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    train = tf.keras.utils.image_dataset_from_directory(
        DATA, validation_split=0.2, subset="training", seed=42, image_size=(IMAGE_SIZE, IMAGE_SIZE),
        batch_size=BATCH_SIZE, label_mode="int", shuffle=True,
    )
    validation = tf.keras.utils.image_dataset_from_directory(
        DATA, validation_split=0.2, subset="validation", seed=42, image_size=(IMAGE_SIZE, IMAGE_SIZE),
        batch_size=BATCH_SIZE, label_mode="int", shuffle=False,
    )
    labels = train.class_names
    (OUTPUT / "class_indices.json").write_text(json.dumps(dict(enumerate(labels)), indent=2), encoding="utf-8")
    augmentation = tf.keras.Sequential([tf.keras.layers.RandomFlip("horizontal"), tf.keras.layers.RandomRotation(0.08), tf.keras.layers.RandomContrast(0.1)])
    base = tf.keras.applications.MobileNetV2(input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3), include_top=False, alpha=0.35, weights="imagenet")
    base.trainable = False
    inputs = tf.keras.Input((IMAGE_SIZE, IMAGE_SIZE, 3), name="image")
    x = augmentation(inputs)
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(len(labels), activation="softmax", name="tomato_health")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    callbacks = [tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=2, restore_best_weights=True), tf.keras.callbacks.ModelCheckpoint(OUTPUT / "best.keras", monitor="val_accuracy", save_best_only=True)]
    model.fit(train.prefetch(tf.data.AUTOTUNE), validation_data=validation.prefetch(tf.data.AUTOTUNE), epochs=4, callbacks=callbacks)
    model = tf.keras.models.load_model(OUTPUT / "best.keras")
    metrics = model.evaluate(validation, return_dict=True, verbose=0)
    model.save(OUTPUT / "tomato_mvp.keras")
    (OUTPUT / "metrics.json").write_text(json.dumps({k: float(v) for k, v in metrics.items()}, indent=2), encoding="utf-8")
    print(json.dumps({"labels": labels, "validation": metrics}, indent=2))


if __name__ == "__main__":
    main()
