"""
Model Training Script
======================
Trains DistilBERT on LIAR + ISOT datasets for fake news detection.

Usage:
  python scripts/train_model.py

Output:
  ./app/ml_models/fake_news_model/
"""
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
from loguru import logger
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score


def load_liar_dataset():
    from datasets import load_dataset
    logger.info("Loading LIAR dataset...")
    dataset = load_dataset("liar")
    label_map = {
        "pants-fire": 0, "false": 0, "barely-true": 0,
        "half-true": 1, "mostly-true": 1, "true": 1,
    }
    rows = []
    for split in ["train", "validation", "test"]:
        for item in dataset[split]:
            label_str = item.get("label", "")
            if label_str in label_map:
                rows.append({"text": item["statement"], "label": label_map[label_str]})
    return pd.DataFrame(rows)


def load_isot_dataset(data_dir="./data"):
    dfs = []
    for fname, label in [("Fake.csv", 0), ("True.csv", 1)]:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["text"] = df["title"].fillna("") + " " + df["text"].fillna("")
            df["label"] = label
            dfs.append(df[["text", "label"]])
            logger.info(f"{fname}: {len(df)} rows")
    return pd.concat(dfs) if dfs else None


def train():
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification,
        TrainingArguments, Trainer, EarlyStoppingCallback,
    )
    from torch.utils.data import Dataset

    MODEL_NAME = "distilbert-base-uncased"
    OUTPUT_DIR = "./app/ml_models/fake_news_model"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    dfs = []
    try:
        dfs.append(load_liar_dataset())
    except Exception as e:
        logger.warning(f"LIAR load failed: {e}")
    isot = load_isot_dataset()
    if isot is not None:
        dfs.append(isot)

    if not dfs:
        logger.error("No datasets found. Download LIAR or ISOT first.")
        return

    df = pd.concat(dfs, ignore_index=True).dropna(subset=["text", "label"])
    df["text"] = df["text"].str[:512]
    logger.info(f"Total: {len(df)} | Fake: {(df.label==0).sum()} | Real: {(df.label==1).sum()}")

    X_train, X_val, y_train, y_val = train_test_split(
        df["text"].tolist(), df["label"].tolist(),
        test_size=0.15, random_state=42, stratify=df["label"],
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    class FakeNewsDataset(Dataset):
        def __init__(self, texts, labels):
            self.enc = tokenizer(texts, truncation=True, padding=True, max_length=256)
            self.labels = labels
        def __len__(self): return len(self.labels)
        def __getitem__(self, idx):
            return {
                "input_ids":      torch.tensor(self.enc["input_ids"][idx]),
                "attention_mask": torch.tensor(self.enc["attention_mask"][idx]),
                "labels":         torch.tensor(self.labels[idx], dtype=torch.long),
            }

    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=1)
        return {"accuracy": accuracy_score(labels, preds)}

    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        weight_decay=0.01,
        warmup_ratio=0.1,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Trainer(
        model=model, args=args,
        train_dataset=FakeNewsDataset(X_train, y_train),
        eval_dataset=FakeNewsDataset(X_val, y_val),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    logger.info("Training started...")
    trainer.train()
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    logger.success(f"Model saved to {OUTPUT_DIR}")

    preds_output = trainer.predict(FakeNewsDataset(X_val, y_val))
    preds = np.argmax(preds_output.predictions, axis=1)
    logger.info("\n" + classification_report(y_val, preds, target_names=["Fake", "Real"]))


if __name__ == "__main__":
    train()
