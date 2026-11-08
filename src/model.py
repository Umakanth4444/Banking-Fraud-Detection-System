from pathlib import Path
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from src.db import get_engine

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "fraud_model.joblib"

def train_model():
    query = """SELECT transaction_amount, merchant_category, transaction_type, location,
      payment_channel, device_type, is_international,
      EXTRACT(HOUR FROM transaction_date)::int AS hour,
      EXTRACT(DOW FROM transaction_date)::int AS day_of_week,
      EXTRACT(MONTH FROM transaction_date)::int AS month, is_fraud FROM transactions"""
    df = pd.read_sql(query, get_engine())
    if df.empty or df["is_fraud"].nunique() < 2:
        raise ValueError("Load data with both fraud and legitimate examples before training.")
    features = ["transaction_amount","merchant_category","transaction_type","location",
                "payment_channel","device_type","is_international","hour","day_of_week","month"]
    X, y = df[features], df["is_fraud"].astype(int)
    stratify = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42, stratify=stratify)
    numeric = ["transaction_amount","hour","day_of_week","month"]
    categorical = ["merchant_category","transaction_type","location","payment_channel","device_type","is_international"]
    prep = ColumnTransformer([
      ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric),
      ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical)])
    model = Pipeline([("prep", prep), ("classifier", RandomForestClassifier(
      n_estimators=250, class_weight="balanced", min_samples_leaf=2, random_state=42, n_jobs=-1))])
    model.fit(X_train, y_train)
    pred, proba = model.predict(X_test), model.predict_proba(X_test)[:,1]
    auc = roc_auc_score(y_test, proba) if y_test.nunique() > 1 else None
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return {"report":classification_report(y_test,pred,zero_division=0),
            "confusion_matrix":confusion_matrix(y_test,pred).tolist(),
            "roc_auc":auc,"model_path":str(MODEL_PATH)}
