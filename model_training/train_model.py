"""
╔══════════════════════════════════════════════════════════════════╗
║       Can I Trust? — Fake News Classifier Training Script        ║
║                                                                  ║
║  Dataset  : ISOT Fake News Dataset (Fake.csv + True.csv)         ║
║  Base Model: distilbert-base-uncased (fast, accurate, ~250MB)   ║
║  Output   : ./app/ml_models/fake_news_model/                    ║
║                                                                  ║
║  Usage:                                                          ║
║    python train_model.py                          (default)      ║
║    python train_model.py --epochs 5               (more epochs)  ║
║    python train_model.py --quick                  (smoke test)   ║
║    python train_model.py --fake Fake.csv --true True.csv         ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import argparse
import time
import json
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from loguru import logger
from pathlib import Path
from datetime import datetime


# ── CLI Arguments ────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="Train fake news classifier")
    parser.add_argument("--fake",       default="Fake.csv",   help="Path to Fake.csv")
    parser.add_argument("--true",       default="True.csv",   help="Path to True.csv")
    parser.add_argument("--output",     default="./app/ml_models/fake_news_model", help="Output model directory")
    parser.add_argument("--model",      default="distilbert-base-uncased",          help="HuggingFace base model")
    parser.add_argument("--epochs",     type=int, default=3,   help="Training epochs")
    parser.add_argument("--batch",      type=int, default=16,  help="Batch size")
    parser.add_argument("--max-len",    type=int, default=256, help="Max token length (256 recommended)")
    parser.add_argument("--lr",         type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--val-split",  type=float, default=0.15,  help="Validation split ratio")
    parser.add_argument("--test-split", type=float, default=0.10,  help="Test split ratio")
    parser.add_argument("--seed",       type=int, default=42,  help="Random seed")
    parser.add_argument("--quick",      action="store_true",    help="Quick smoke test (500 samples)")
    parser.add_argument("--no-liar",    action="store_true",    help="Skip LIAR dataset augmentation")
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════
# STEP 1: DATA LOADING & PREPROCESSING
# ═══════════════════════════════════════════════════════════════

def load_isot_dataset(fake_path: str, true_path: str) -> pd.DataFrame:
    """
    Load ISOT dataset from Fake.csv and True.csv.

    Dataset info:
      - True.csv  : 21,417 articles — Reuters real news (politicsNews, worldnews)
      - Fake.csv  : 23,481 articles — Fake/satirical news (multiple categories)
      - Columns   : title, text, subject, date

    Label: 0 = Fake, 1 = Real
    """
    logger.info("Loading ISOT dataset...")

    # Load both files
    df_fake = pd.read_csv(fake_path)
    df_true = pd.read_csv(true_path)

    df_fake["label"] = 0   # Fake
    df_true["label"] = 1   # Real

    logger.info(f"  Fake articles : {len(df_fake):,}")
    logger.info(f"  Real articles : {len(df_true):,}")

    # Combine
    df = pd.concat([df_fake, df_true], ignore_index=True)

    # ── Feature Engineering ──────────────────────────────────────
    # Combine title + text for richer context
    # Title is repeated because it carries strong signal
    df["combined"] = (
        df["title"].fillna("").str.strip()
        + " [SEP] "
        + df["title"].fillna("").str.strip()   # title repeated = emphasize headline
        + " " 
        + df["text"].fillna("").str.strip()
    )

    # Remove rows with very short text (likely corrupted)
    before = len(df)
    df = df[df["combined"].str.len() > 50].reset_index(drop=True)
    removed = before - len(df)
    if removed:
        logger.warning(f"  Removed {removed} rows with too-short text")

    # Strip whitespace from text
    df["combined"] = df["combined"].str.strip()

    logger.success(f"  Total samples after cleaning: {len(df):,}")
    logger.info(f"  Label distribution: Fake={( df.label==0).sum():,} | Real={(df.label==1).sum():,}")

    return df[["combined", "label", "subject", "title"]]


def try_load_liar_dataset() -> pd.DataFrame:
    """
    Optionally augment with LIAR dataset from HuggingFace.
    Returns empty DataFrame if unavailable.

    LIAR label mapping:
      pants-fire, false, barely-true → 0 (Fake)
      half-true, mostly-true, true   → 1 (Real)
    """
    try:
        from datasets import load_dataset
        logger.info("Augmenting with LIAR dataset from HuggingFace...")

        dataset = load_dataset("liar", trust_remote_code=True)
        label_map = {
            "pants-fire": 0, "false": 0, "barely-true": 0,
            "half-true": 1, "mostly-true": 1, "true": 1,
        }
        rows = []
        for split in ["train", "validation", "test"]:
            for item in dataset[split]:
                label_str = item.get("label", "")
                if label_str in label_map:
                    text = item.get("statement", "").strip()
                    if text:
                        rows.append({"combined": text, "label": label_map[label_str]})

        df_liar = pd.DataFrame(rows)
        logger.success(f"  LIAR dataset: {len(df_liar):,} samples added")
        return df_liar

    except Exception as e:
        logger.warning(f"  LIAR dataset not available ({e}) — skipping")
        return pd.DataFrame()


def preprocess(df: pd.DataFrame, max_len_chars: int = 2000) -> pd.DataFrame:
    """
    Text cleaning pipeline applied before tokenization.
    We keep it light — BERT handles most NLP internally.
    """
    import re
    logger.info("Preprocessing text...")

    def clean(text):
        # Remove URLs
        text = re.sub(r"http\S+|www\.\S+", " ", text)
        # Collapse excessive whitespace
        text = re.sub(r"\s{3,}", "  ", text)
        # Remove non-ASCII junk (but keep punctuation)
        text = text.encode("ascii", errors="ignore").decode()
        # Truncate to max chars (tokenizer will also truncate, but saves memory)
        return text[:max_len_chars].strip()

    df["combined"] = df["combined"].apply(clean)
    # Drop empty after cleaning
    df = df[df["combined"].str.len() > 20].reset_index(drop=True)
    logger.success(f"  Preprocessing done: {len(df):,} samples")
    return df


# ═══════════════════════════════════════════════════════════════
# STEP 2: PYTORCH DATASET
# ═══════════════════════════════════════════════════════════════

def build_datasets(df: pd.DataFrame, tokenizer, max_len: int, val_split: float, test_split: float, seed: int):
    """
    Stratified train / val / test split, then wrap in PyTorch datasets.
    """
    import torch
    from torch.utils.data import Dataset
    from sklearn.model_selection import train_test_split

    texts  = df["combined"].tolist()
    labels = df["label"].tolist()

    # Train / (val+test) split
    X_train, X_tmp, y_train, y_tmp = train_test_split(
        texts, labels,
        test_size=(val_split + test_split),
        random_state=seed,
        stratify=labels,
    )
    # Val / test split
    relative_test = test_split / (val_split + test_split)
    X_val, X_test, y_val, y_test = train_test_split(
        X_tmp, y_tmp,
        test_size=relative_test,
        random_state=seed,
        stratify=y_tmp,
    )

    logger.info(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")

    class FakeNewsDataset(Dataset):
        def __init__(self, texts, labels):
            logger.info(f"    Tokenizing {len(texts):,} samples (max_len={max_len})...")
            self.encodings = tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=max_len,
                return_tensors="pt",
            )
            self.labels = torch.tensor(labels, dtype=torch.long)

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, idx):
            return {
                "input_ids":      self.encodings["input_ids"][idx],
                "attention_mask": self.encodings["attention_mask"][idx],
                "labels":         self.labels[idx],
            }

    train_ds = FakeNewsDataset(X_train, y_train)
    val_ds   = FakeNewsDataset(X_val,   y_val)
    test_ds  = FakeNewsDataset(X_test,  y_test)

    return train_ds, val_ds, test_ds, X_test, y_test


# ═══════════════════════════════════════════════════════════════
# STEP 3: METRICS
# ═══════════════════════════════════════════════════════════════

def compute_metrics(eval_pred):
    """Called by HuggingFace Trainer after each eval epoch."""
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    return {
        "accuracy":  round(accuracy_score(labels, preds), 4),
        "f1":        round(f1_score(labels, preds, average="weighted"), 4),
        "precision": round(precision_score(labels, preds, average="weighted", zero_division=0), 4),
        "recall":    round(recall_score(labels, preds, average="weighted", zero_division=0), 4),
    }


# ═══════════════════════════════════════════════════════════════
# STEP 4: TRAINING
# ═══════════════════════════════════════════════════════════════

def train(args):
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        TrainingArguments,
        Trainer,
        EarlyStoppingCallback,
    )
    from sklearn.metrics import classification_report, confusion_matrix

    # ── Setup ────────────────────────────────────────────────────
    logger.info(f"PyTorch version : {torch.__version__}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device          : {device.upper()}")
    if device == "cuda":
        logger.info(f"GPU             : {torch.cuda.get_device_name(0)}")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Load ISOT ────────────────────────────────────────────────
    df = load_isot_dataset(args.fake, args.true)

    # ── Optionally augment with LIAR ─────────────────────────────
    if not args.no_liar:
        df_liar = try_load_liar_dataset()
        if not df_liar.empty:
            df = pd.concat([df, df_liar[["combined", "label"]]], ignore_index=True)
            logger.info(f"Combined dataset size: {len(df):,}")

    # ── Preprocess ───────────────────────────────────────────────
    df = preprocess(df)

    # ── Quick mode (smoke test) ──────────────────────────────────
    if args.quick:
        logger.warning("QUICK MODE — using 500 samples only (for testing)")
        df = df.sample(500, random_state=args.seed).reset_index(drop=True)

    # ── Shuffle ──────────────────────────────────────────────────
    df = df.sample(frac=1, random_state=args.seed).reset_index(drop=True)

    # ── Tokenizer ────────────────────────────────────────────────
    logger.info(f"Loading tokenizer: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    # ── Datasets ─────────────────────────────────────────────────
    train_ds, val_ds, test_ds, X_test_raw, y_test_raw = build_datasets(
        df, tokenizer, args.max_len, args.val_split, args.test_split, args.seed
    )

    # ── Model ────────────────────────────────────────────────────
    logger.info(f"Loading model   : {args.model}")
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=2,
        id2label={0: "FAKE", 1: "REAL"},
        label2id={"FAKE": 0, "REAL": 1},
    )

    # ── Training Arguments ───────────────────────────────────────
    training_args = TrainingArguments(
        output_dir                  = str(output_dir / "checkpoints"),
        num_train_epochs            = args.epochs,
        per_device_train_batch_size = args.batch,
        per_device_eval_batch_size  = args.batch * 2,
        learning_rate               = args.lr,
        weight_decay                = 0.01,
        warmup_ratio                = 0.1,              # 10% warmup
        lr_scheduler_type           = "cosine",         # smooth LR decay
        evaluation_strategy         = "epoch",
        save_strategy               = "epoch",
        load_best_model_at_end      = True,
        metric_for_best_model       = "f1",
        greater_is_better           = True,
        logging_steps               = 50,
        logging_dir                 = str(output_dir / "logs"),
        fp16                        = (device == "cuda"),  # half-precision on GPU
        dataloader_num_workers      = 0,                   # 0 = safe on Windows/Mac
        report_to                   = "none",              # disable wandb/tensorboard
        save_total_limit            = 2,                   # keep only last 2 checkpoints
        seed                        = args.seed,
    )

    # ── Trainer ──────────────────────────────────────────────────
    trainer = Trainer(
        model           = model,
        args            = training_args,
        train_dataset   = train_ds,
        eval_dataset    = val_ds,
        compute_metrics = compute_metrics,
        callbacks       = [EarlyStoppingCallback(early_stopping_patience=2)],
    )

    # ── TRAIN ────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Training started")
    logger.info("=" * 60)
    start = time.time()
    trainer.train()
    elapsed = time.time() - start
    logger.success(f"Training completed in {elapsed/60:.1f} minutes")

    # ── EVALUATE on held-out test set ────────────────────────────
    logger.info("=" * 60)
    logger.info("Final evaluation on test set")
    logger.info("=" * 60)
    test_results = trainer.predict(test_ds)
    test_preds   = np.argmax(test_results.predictions, axis=1)

    report = classification_report(
        y_test_raw, test_preds,
        target_names=["FAKE", "REAL"],
        digits=4,
    )
    logger.info(f"\n{report}")

    cm = confusion_matrix(y_test_raw, test_preds)
    logger.info(f"Confusion Matrix:\n{cm}")

    # ── Save model + tokenizer ────────────────────────────────────
    logger.info(f"Saving model to {output_dir}...")
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # ── Save metadata ─────────────────────────────────────────────
    metadata = {
        "model_name":       args.model,
        "trained_at":       datetime.now().isoformat(),
        "total_samples":    len(df),
        "train_samples":    len(train_ds),
        "val_samples":      len(val_ds),
        "test_samples":     len(test_ds),
        "epochs":           args.epochs,
        "batch_size":       args.batch,
        "max_length":       args.max_len,
        "learning_rate":    args.lr,
        "device":           device,
        "training_minutes": round(elapsed / 60, 1),
        "labels":           {"0": "FAKE", "1": "REAL"},
        "id2label":         {"0": "FAKE", "1": "REAL"},
        "label2id":         {"FAKE": 0, "REAL": 1},
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }
    with open(output_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.success(f"Model and metadata saved to: {output_dir}")
    logger.info("=" * 60)
    logger.success("TRAINING COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"To use the model in your FastAPI backend, set:")
    logger.info(f"  MODEL_PATH={output_dir}")
    logger.info(f"  USE_LOCAL_MODEL=True")

    return output_dir


# ═══════════════════════════════════════════════════════════════
# STEP 5: QUICK INFERENCE TEST
# ═══════════════════════════════════════════════════════════════

def test_inference(model_dir: str):
    """
    Quick sanity check — run a few sample headlines through the model.
    """
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    logger.info("\nRunning inference test on sample headlines...")

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()

    samples = [
        # Real news
        ("WASHINGTON (Reuters) - The Federal Reserve held interest rates steady on Wednesday, "
         "saying the U.S. economy was growing at a moderate pace.", "Expected: REAL"),

        # Fake news
        ("SHOCKING: Scientists confirm that drinking bleach cures all diseases "
         "— government doesn't want you to know this miracle cure!", "Expected: FAKE"),

        # Real news
        ("Pakistan's Prime Minister met with the Chinese President to discuss trade and investment "
         "relations between the two countries.", "Expected: REAL"),

        # Fake news
        ("BREAKING: Deep state operatives caught planting microchips in COVID vaccines — "
         "whistleblower EXPOSES massive globalist conspiracy you won't believe!", "Expected: FAKE"),

        # Ambiguous
        ("Sources say the president will announce major policy changes next week "
         "affecting millions of Americans.", "Expected: UNCERTAIN"),
    ]

    print("\n" + "=" * 60)
    print("INFERENCE RESULTS")
    print("=" * 60)

    for text, hint in samples:
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        )
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1).squeeze()

        fake_prob = float(probs[0])
        real_prob = float(probs[1])
        verdict   = "REAL" if real_prob > 0.5 else "FAKE"
        confidence = max(fake_prob, real_prob) * 100
        trust_score = real_prob * 100

        print(f"\nText     : {text[:80]}...")
        print(f"Verdict  : {verdict}  (confidence: {confidence:.1f}%)")
        print(f"Trust    : {trust_score:.1f}/100")
        print(f"Hint     : {hint}")
        print(f"Probs    : FAKE={fake_prob:.3f}  REAL={real_prob:.3f}")

    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = parse_args()

    # Logger setup
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    log_path = Path(args.output) / "training.log"
    Path(args.output).mkdir(parents=True, exist_ok=True)
    logger.add(str(log_path), level="DEBUG", rotation="10 MB")

    # Validate input files
    for label, path in [("Fake", args.fake), ("True", args.true)]:
        if not Path(path).exists():
            logger.error(f"{label} dataset not found at: {path}")
            logger.info(f"Usage: python train_model.py --fake /path/to/Fake.csv --true /path/to/True.csv")
            sys.exit(1)

    # Check dependencies
    try:
        import torch
        import transformers
        import sklearn
        logger.info(f"transformers={transformers.__version__}  sklearn={sklearn.__version__}")
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.info("Run: pip install torch transformers scikit-learn pandas loguru")
        sys.exit(1)

    # Train
    output_dir = train(args)

    # Inference test
    test_inference(str(output_dir))
