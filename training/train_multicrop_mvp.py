"""Train the browser MVP on 12 PlantVillage classes across four crops.

This deliberately scopes the field demo to maize, potato, tomato and bell
pepper.  It is not an open-world disease detector: unknown crops must be
shown as unsupported by the application rather than forced into a diagnosis.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import tensorflow as tf

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
tf.keras.utils.set_random_seed(42)

ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "PlantVillage-Dataset" / "raw" / "color"
OUTPUT = ROOT / "artifacts" / "multicrop-mvp"
IMAGE_SIZE = 160
BATCH_SIZE = 32
EPOCHS = 5


def make_dataset(subset: str, shuffle: bool) -> tf.data.Dataset:
    return tf.keras.utils.image_dataset_from_directory(
        DATA,
        validation_split=0.2,
        subset=subset,
        seed=42,
        image_size=(IMAGE_SIZE, IMAGE_SIZE),
        batch_size=BATCH_SIZE,
        label_mode="int",
        shuffle=shuffle,
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    train = make_dataset("training", shuffle=True)
    validation = make_dataset("validation", shuffle=False)
    labels = train.class_names
    supported_crops = ["Maize", "Potato", "Tomato", "Bell pepper"]
    (OUTPUT / "class_indices.json").write_text(
        json.dumps(dict(enumerate(labels)), indent=2), encoding="utf-8"
    )
    (OUTPUT / "model_scope.json").write_text(
        json.dumps(
            {
                "dataset": "PlantVillage color subset",
                "supported_crops": supported_crops,
                "class_count": len(labels),
                "image_size": IMAGE_SIZE,
                "notes": "Controlled leaf images; validate field photos locally before treatment.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.08),
            tf.keras.layers.RandomContrast(0.10),
        ],
        name="augmentation",
    )
    base = tf.keras.applications.MobileNetV2(
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3),
        include_top=False,
        alpha=0.35,
        weights="imagenet",
    )
    base.trainable = False
    inputs = tf.keras.Input((IMAGE_SIZE, IMAGE_SIZE, 3), name="image")
    x = augmentation(inputs)
    # The preprocessing is exported inside the model. Browser clients pass RGB
    # pixels in their natural 0..255 range, avoiding a hidden mismatch.
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(len(labels), activation="softmax", name="crop_health")(x)
    model = tf.keras.Model(inputs, outputs, name="cropsignal_multicrop_mvp")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=2, restore_best_weights=True
        ),
        tf.keras.callbacks.ModelCheckpoint(
            OUTPUT / "best.keras", monitor="val_accuracy", save_best_only=True
        ),
    ]
    model.fit(
        train.prefetch(tf.data.AUTOTUNE),
        validation_data=validation.prefetch(tf.data.AUTOTUNE),
        epochs=EPOCHS,
        callbacks=callbacks,
    )
    model = tf.keras.models.load_model(OUTPUT / "best.keras")
    metrics = model.evaluate(validation.prefetch(tf.data.AUTOTUNE), return_dict=True, verbose=0)
    model.save(OUTPUT / "multicrop_mvp.keras")
    report = {
        "labels": labels,
        "validation": {name: float(value) for name, value in metrics.items()},
        "supported_crops": supported_crops,
    }
    (OUTPUT / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
