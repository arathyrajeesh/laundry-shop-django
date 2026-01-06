# shop/ai/cloth_ai.py
import tensorflow as tf
import numpy as np
from PIL import Image

_model = None

def get_model():
    global _model
    if _model is None:
        _model = tf.keras.applications.MobileNetV2(
            weights="imagenet",
            include_top=True   # ✅ REQUIRED
        )
    return _model

def detect_cloth_type(image_path):
    model = get_model()

    img = Image.open(image_path).convert("RGB").resize((224, 224))
    img_array = np.array(img)
    img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
    img_array = np.expand_dims(img_array, axis=0)

    preds = model.predict(img_array)
    decoded = tf.keras.applications.mobilenet_v2.decode_predictions(preds, top=3)[0]
    labels = [label for (_, label, _) in decoded]

    if any(x in labels for x in ["jean", "denim"]):
        return "Denim"
    elif any(x in labels for x in ["shirt", "t-shirt"]):
        return "Cotton"
    elif any(x in labels for x in ["silk"]):
        return "Silk"
    else:
        return "Unknown"
