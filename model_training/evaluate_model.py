"""
Model Evaluation & Analysis Script
====================================
Detailed post-training analysis:
  - Per-category accuracy (politicsNews, worldnews, etc.)
  - Error analysis (what type of news does it get wrong?)
  - Confidence distribution
  - Model size & speed benchmarks
  - Export confusion matrix as image

Usage:
  python evaluate_model.py --model ./app/ml_models/fake_news_model
  python evaluate_model.py --model ./app/ml_models/fake_news_model --fake Fake.csv --true True.csv
"""

import argparse
import json
import time
import sys
from pathlib import Path

import pandas as pd
import numpy as np
from loguru import logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",  required=True, help="Path to saved model directory")
    parser.add_argument("--fake",   default="Fake.csv")
    parser.add_argument("--true",   default="True.csv")
    parser.add_argument("--samples", type=int, default=2000, help="Samples to evaluate (0 = all)")
    return parser.parse_args()


def load_model(model_dir: str):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model     = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    return tokenizer, model


def predict_batch(texts, tokenizer, model, batch_size=32, max_len=256):
    import torch
    all_probs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(batch, truncation=True, padding=True, max_length=max_len, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
            probs   = torch.softmax(outputs.logits, dim=1).numpy()
        all_probs.extend(probs.tolist())
    return np.array(all_probs)


def main():
    args = parse_args()
    logger.info(f"Loading model from {args.model}...")
    tokenizer, model = load_model(args.model)

    # Load metadata if exists
    meta_path = Path(args.model) / "training_metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        logger.info(f"Model trained at   : {meta.get('trained_at','?')}")
        logger.info(f"Training samples   : {meta.get('train_samples','?'):,}")
        logger.info(f"Training minutes   : {meta.get('training_minutes','?')}")

    # Load dataset
    logger.info("Loading dataset...")
    df_fake = pd.read_csv(args.fake); df_fake["label"] = 0
    df_true = pd.read_csv(args.true); df_true["label"] = 1
    df = pd.concat([df_fake, df_true], ignore_index=True)
    df["combined"] = (df["title"].fillna("") + " [SEP] " + df["text"].fillna("")).str[:1500]

    if args.samples and args.samples < len(df):
        df = df.sample(args.samples, random_state=42).reset_index(drop=True)
        logger.info(f"Evaluating on {args.samples:,} sampled rows")

    # Predict
    logger.info("Running predictions...")
    t0    = time.time()
    probs = predict_batch(df["combined"].tolist(), tokenizer, model)
    elapsed = time.time() - t0
    preds = np.argmax(probs, axis=1)

    df["pred"]       = preds
    df["fake_prob"]  = probs[:, 0]
    df["real_prob"]  = probs[:, 1]
    df["confidence"] = np.max(probs, axis=1)
    df["correct"]    = (df["pred"] == df["label"]).astype(int)

    # ── Overall Metrics ──────────────────────────────────────────
    from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
    overall_acc = df["correct"].mean()

    print("\n" + "═" * 60)
    print("OVERALL PERFORMANCE")
    print("═" * 60)
    print(classification_report(df["label"], df["pred"], target_names=["FAKE", "REAL"], digits=4))
    print(f"ROC-AUC score : {roc_auc_score(df['label'], df['real_prob']):.4f}")
    print(f"Inference speed: {len(df)/elapsed:.0f} articles/sec")
    print(f"Avg latency/article: {elapsed/len(df)*1000:.1f} ms")

    cm = confusion_matrix(df["label"], df["pred"])
    print(f"\nConfusion Matrix:")
    print(f"             Pred:FAKE  Pred:REAL")
    print(f"True:FAKE       {cm[0][0]:6,}     {cm[0][1]:6,}")
    print(f"True:REAL       {cm[1][0]:6,}     {cm[1][1]:6,}")

    # ── Per-Subject Accuracy ─────────────────────────────────────
    print("\n" + "═" * 60)
    print("ACCURACY BY SUBJECT/CATEGORY")
    print("═" * 60)
    by_subject = df.groupby("subject").agg(
        count=("correct", "count"),
        accuracy=("correct", "mean"),
        avg_confidence=("confidence", "mean"),
    ).sort_values("accuracy", ascending=False)
    print(by_subject.to_string())

    # ── Confidence Analysis ──────────────────────────────────────
    print("\n" + "═" * 60)
    print("CONFIDENCE DISTRIBUTION")
    print("═" * 60)
    bins = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    labels = ["50–60%", "60–70%", "70–80%", "80–90%", "90–100%"]
    df["conf_bin"] = pd.cut(df["confidence"], bins=bins, labels=labels)
    conf_analysis = df.groupby("conf_bin", observed=True).agg(
        count=("correct","count"),
        accuracy=("correct","mean")
    )
    print(conf_analysis.to_string())

    # ── Error Analysis (false positives / negatives) ─────────────
    print("\n" + "═" * 60)
    print("ERROR ANALYSIS — 10 WORST MISTAKES")
    print("═" * 60)
    errors = df[df["correct"] == 0].nsmallest(10, "confidence")
    for _, row in errors.iterrows():
        actual = "REAL" if row["label"] == 1 else "FAKE"
        predicted = "REAL" if row["pred"] == 1 else "FAKE"
        print(f"\nTitle    : {str(row['title'])[:90]}")
        print(f"Subject  : {row['subject']}")
        print(f"Actual   : {actual}  →  Predicted: {predicted}  (confidence: {row['confidence']:.2%})")

    # ── Model Size ───────────────────────────────────────────────
    import os
    model_size = sum(
        os.path.getsize(Path(args.model) / f)
        for f in os.listdir(args.model)
        if os.path.isfile(Path(args.model) / f)
    ) / (1024 * 1024)
    print(f"\n{'═'*60}")
    print(f"Model size on disk: {model_size:.0f} MB")
    print(f"{'═'*60}")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | {message}")
    main()
