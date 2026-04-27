# Can I Trust? — Model Training Guide

## Dataset Info (ISOT)
| File | Articles | Label |
|------|---------|-------|
| True.csv | 21,417 | Real (Reuters news) |
| Fake.csv | 23,481 | Fake/satirical news |
| **Total** | **44,898** | — |

Columns: `title, text, subject, date`

## Setup

```bash
pip install -r requirements_ml.txt
```

## Training

### Option 1: Default training (recommended)
```bash
python train_model.py --fake Fake.csv --true True.csv
```

### Option 2: All options
```bash
python train_model.py \
  --fake Fake.csv \
  --true True.csv \
  --output ./app/ml_models/fake_news_model \
  --model distilbert-base-uncased \
  --epochs 3 \
  --batch 16 \
  --max-len 256 \
  --lr 2e-5
```

### Option 3: Quick smoke test (30 seconds)
```bash
python train_model.py --quick --fake Fake.csv --true True.csv
```

### Option 4: With LIAR dataset augmentation (better accuracy)
```bash
# LIAR dataset downloads automatically from HuggingFace
python train_model.py --fake Fake.csv --true True.csv
# (LIAR augmentation is ON by default, use --no-liar to skip)
```

## Expected Training Time
| Hardware | Time |
|----------|------|
| CPU only | ~4–6 hours |
| GPU (T4/3090) | ~15–25 minutes |
| Google Colab Free GPU | ~30–40 minutes |

## Expected Accuracy (ISOT dataset)
| Metric | Expected |
|--------|---------|
| Accuracy | 98–99% |
| F1 Score | 0.98+ |
| ROC-AUC | 0.99+ |

ISOT is a "clean" dataset so accuracy will be very high.
Real-world performance will be lower — LIAR augmentation helps with generalization.

## After Training

```bash
# Evaluate the model
python evaluate_model.py --model ./app/ml_models/fake_news_model

# In your FastAPI .env:
MODEL_PATH=./app/ml_models/fake_news_model
USE_LOCAL_MODEL=True
```

## Model Output Directory
```
app/ml_models/fake_news_model/
├── config.json               # Model architecture
├── model.safetensors         # Model weights (~250MB)
├── tokenizer.json            # Tokenizer
├── tokenizer_config.json
├── vocab.txt
├── training_metadata.json    # Training stats & metrics
└── training.log              # Full training log
```

## Running on Google Colab (Free GPU)
```python
# Upload Fake.csv and True.csv to Colab, then:
!pip install torch transformers datasets scikit-learn loguru pandas
!python train_model.py --fake Fake.csv --true True.csv --batch 32
# After training, download the model folder
from google.colab import files
import shutil
shutil.make_archive('fake_news_model', 'zip', './app/ml_models/fake_news_model')
files.download('fake_news_model.zip')
```
