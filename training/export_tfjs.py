"""Convert a Keras model created by train_plantvillage.py into CropSignal assets."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import sys
import types

import tensorflow as tf
import tf_keras

# tensorflowjs imports its optional Decision Forest converter at module import.
# It is irrelevant for Keras export, so avoid requiring that large optional package.
sys.modules.setdefault("tensorflow_decision_forests", types.ModuleType("tensorflow_decision_forests"))
import tensorflowjs as tfjs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keras", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", default="../model")
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    trained = tf.keras.models.load_model(args.keras)
    # Rebuild the inference path with tf_keras (Keras 2). TensorFlow.js's
    # Layers exporter consumes this format faithfully; the newer SavedModel
    # graph route caused browser/Python output drift in this environment.
    inputs = tf_keras.Input(trained.input_shape[1:], name="image")
    backbone = next(layer for layer in trained.layers if layer.name.startswith("mobilenetv2"))
    browser_backbone = tf_keras.applications.MobileNetV2(
        input_shape=trained.input_shape[1:], include_top=False, alpha=0.35, weights=None
    )
    browser_backbone.set_weights(backbone.get_weights())
    x = browser_backbone(inputs, training=False)
    x = tf_keras.layers.GlobalAveragePooling2D(name="global_average_pooling2d")(x)
    output_layer = next(layer for layer in trained.layers if layer.name in {"crop_health", "coffee_health"})
    outputs = tf_keras.layers.Dense(
        trained.output_shape[-1], activation="softmax", name=output_layer.name
    )(x)
    model = tf_keras.Model(inputs, outputs, name="cropsignal_browser_inference")
    model.get_layer(output_layer.name).set_weights(output_layer.get_weights())
    tfjs.converters.save_keras_model(model, str(output))
    shutil.copy2(args.labels, output / "class_indices.json")
    print(f"Wrote browser model to {output.resolve()}")


if __name__ == "__main__":
    main()
