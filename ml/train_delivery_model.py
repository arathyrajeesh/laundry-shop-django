import pandas as pd
import pickle
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor

data = pd.read_csv("delivery_data.csv")

X = data.drop("delivery_hours", axis=1)
y = data["delivery_hours"]

cat_cols = ["cloth", "service"]
num_cols = ["branch_load", "items"]

preprocessor = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ("num", "passthrough", num_cols)
])

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

pipeline = Pipeline([
    ("prep", preprocessor),
    ("model", model)
])

pipeline.fit(X, y)

with open("delivery_model.pkl", "wb") as f:
    pickle.dump(pipeline, f)

print("✅ Delivery prediction model trained")
