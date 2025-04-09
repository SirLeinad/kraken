# evaluate_new_model.py

import pandas as pd
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, confusion_matrix, ConfusionMatrixDisplay,
    roc_curve, auc
)
import matplotlib.pyplot as plt

DATA_PATH = "data/training_dataset.csv"
MODEL_PATH = "models/model_v2.pkl"

def evaluate():
    print("[INFO] Loading dataset and model...")
    df = pd.read_csv(DATA_PATH)
    model = joblib.load(MODEL_PATH)

    features = ["sma", "rsi", "price_delta", "volume_delta", "volatility"]
    X = df[features]
    y = df["target"]

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    print("[INFO] Predicting...")
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\n[RESULT] Classification Report:\n")
    print(classification_report(y_test, y_pred, digits=4))

    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["↓", "↑"])
    disp.plot(cmap=plt.cm.Blues)
    plt.title("Confusion Matrix")
    plt.tight_layout()
    plt.savefig("models/confusion_matrix.png")
    print("[📊] Saved confusion matrix → models/confusion_matrix.png")

    fpr, tpr, _ = roc_curve(y_test, y_proba)
    roc_auc = auc(fpr, tpr)

    plt.figure()
    plt.plot(fpr, tpr, label=f"ROC Curve (AUC = {roc_auc:.4f})")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Receiver Operating Characteristic")
    plt.legend()
    plt.tight_layout()
    plt.savefig("models/roc_curve.png")
    print("[📈] Saved ROC curve → models/roc_curve.png")

if __name__ == "__main__":
    evaluate()
