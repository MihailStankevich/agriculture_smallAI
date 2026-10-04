"""Fine-tune MobileNetV2 on PlantVillage and save a browser-ready source model.

Run this in Google Colab with a GPU. It downloads the official TFDS PlantVillage
builder (~828 MiB) on the first run. The resulting .keras file is converted by
export_tfjs.py and copied to ../model/ for CropSignal.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import tensorflow as tf
import tensorflow_datasets as tfds

IMAGE_SIZE = 224
BATCH_SIZE = 32
AUTOTUNE = tf.data.AUTOTUNE


def prepare(dataset: tf.data.Dataset, training: bool) -> tf.data.Dataset:
    def format_example(example):
        image = tf.image.convert_image_dtype(example["image"], tf.float32)
        image = tf.image.resize(image, (IMAGE_SIZE, IMAGE_SIZE), antialias=True)
        return image, example["label"]

    dataset = dataset.map(format_example, num_parallel_calls=AUTOTUNE)
    if training:
        dataset = dataset.shuffle(4096)
    return dataset.batch(BATCH_SIZE).prefetch(AUTOTUNE)


def create_model(class_count: int) -> tf.keras.Model:
    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.08),
        tf.keras.layers.RandomZoom(0.12),
        tf.keras.layers.RandomContrast(0.12),
    ], name="field_augmentation")
    backbone = tf.keras.applications.MobileNetV2(
        include_top=False, weights="imagenet", input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3)
    )
    backbone.trainable = False
    inputs = tf.keras.Input((IMAGE_SIZE, IMAGE_SIZE, 3), name="image")
    x = augmentation(inputs)
    # PlantVillage input is [0,1]; MobileNetV2's preprocessing converts it to [-1,1].
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x * 255.0)
    x = backbone(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(class_count, activation="softmax", name="plant_disease")(x)
    model = tf.keras.Model(inputs, outputs, name="cropsignal_mobilenetv2")
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts", help="Output folder")
    parser.add_argument("--head-epochs", type=int, default=8)
    parser.add_argument("--finetune-epochs", type=int, default=4)
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)

    (train_raw, validation_raw), info = tfds.load(
        "plant_village", split=["train[:85%]", "train[85%:]"], with_info=True
    )
    labels = list(info.features["label"].names)
    (output / "class_indices.json").write_text(json.dumps(dict(enumerate(labels)), indent=2), encoding="utf-8")
    train, validation = prepare(train_raw, True), prepare(validation_raw, False)
    model = create_model(len(labels))
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(output / "best.keras", monitor="val_accuracy", save_best_only=True),
    ]
    model.fit(train, validation_data=validation, epochs=args.head_epochs, callbacks=callbacks)
    # Carefully unfreeze only late convolution blocks for a short adaptation pass.
    backbone = next(layer for layer in model.layers if layer.name.startswith("mobilenetv2"))
    backbone.trainable = True
    for layer in backbone.layers[:-30]:
        layer.trainable = False
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-5), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(train, validation_data=validation, epochs=args.finetune_epochs, callbacks=callbacks)
    model.save(output / "plantvillage_mobilenetv2.keras")
    metrics = model.evaluate(validation, return_dict=True)
    (output / "metrics.json").write_text(json.dumps({key: float(value) for key, value in metrics.items()}, indent=2), encoding="utf-8")
    print(f"Saved Keras model and labels to {output}. Run export_tfjs.py next.")


if __name__ == "__main__":
    main()
