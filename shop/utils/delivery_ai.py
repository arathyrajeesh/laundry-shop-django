import pickle
import pandas as pd
import os

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

MODEL_PATH = os.path.join(BASE_DIR, "ml", "delivery_model.pkl")

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

def predict_delivery_hours(cloth, service, branch_load, items):
    df = pd.DataFrame([{
        "cloth": cloth,
        "service": service,
        "branch_load": branch_load,
        "items": items
    }])
    return int(round(model.predict(df)[0]))
