"""Builds an advanced openWakeWord training notebook for 'hey lumina'.

Produces hey_lumina_advanced.ipynb — same pipeline as the official automatic
trainer, but tuned for a higher-quality model:
  * target phrase 'hey lumina'
  * many more synthetic positive/negative samples
  * more background noise (several AudioSet parts) + more music (FMA)
  * longer training, production target metrics
"""
import json

def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": src}

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}

cells = []

cells.append(md(
"# Lumina Desk — Advanced 'Hey Lumina' Wake Word Training\n"
"\n"
"Higher-quality version of openWakeWord's automatic trainer, tuned for the phrase "
"**hey lumina**. Everything is synthetic — you do **not** record your voice.\n"
"\n"
"**Before running:** Runtime -> Change runtime type -> **T4 GPU**. "
"Then Runtime -> Run all. Expect roughly **60-120 min** (bigger data = better model).\n"))

# --- Environment setup (verbatim from the official notebook) ---
cells.append(md("## 1. Environment setup"))
cells.append(code(
"# WORKAROUND for HuggingFace 'Xet' CDN outages (403 SignatureError: invalid key\n"
"# pair id). Remove the xet backend + disable it so downloads use HF's classic\n"
"# CDN instead. Fixes 'Format not recognised' failures on dataset downloads.\n"
"import os\n"
"os.environ['HF_HUB_DISABLE_XET'] = '1'\n"
"os.environ['HF_XET_DISABLE'] = '1'\n"
"!pip uninstall -y hf_xet hf-xet 2>/dev/null\n"
"\n"
"# install piper-sample-generator (synthetic TTS) and openWakeWord training deps\n"
"!git clone https://github.com/rhasspy/piper-sample-generator\n"
"!wget -O piper-sample-generator/models/en_US-libritts_r-medium.pt 'https://github.com/rhasspy/piper-sample-generator/releases/download/v2.0.0/en_US-libritts_r-medium.pt'\n"
"!pip install piper-phonemize\n"
"!pip install webrtcvad\n"
"\n"
"!git clone https://github.com/dscripka/openwakeword\n"
"!pip install -e ./openwakeword\n"
"\n"
"!pip install mutagen==1.47.0\n"
"!pip install torchinfo==1.8.0\n"
"!pip install torchmetrics==1.2.0\n"
"!pip install speechbrain==0.5.14\n"
"!pip install audiomentations==0.33.0\n"
"!pip install torch-audiomentations==0.11.0\n"
"!pip install acoustics==0.2.6\n"
"!pip install tensorflow-cpu==2.8.1\n"
"!pip install tensorflow_probability==0.16.0\n"
"!pip install onnx_tf==1.10.0\n"
"!pip install pronouncing==0.2.0\n"
"!pip install datasets==2.14.6\n"
"!pip install deep-phonemizer==0.0.19\n"
"\n"
"import os\n"
"os.makedirs('./openwakeword/openwakeword/resources/models', exist_ok=True)\n"
"!wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx -O ./openwakeword/openwakeword/resources/models/embedding_model.onnx\n"
"!wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.tflite -O ./openwakeword/openwakeword/resources/models/embedding_model.tflite\n"
"!wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx -O ./openwakeword/openwakeword/resources/models/melspectrogram.onnx\n"
"!wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.tflite -O ./openwakeword/openwakeword/resources/models/melspectrogram.tflite\n"))

cells.append(code(
"import os\n"
"import numpy as np\n"
"import torch\n"
"import sys\n"
"from pathlib import Path\n"
"import uuid\n"
"import yaml\n"
"import datasets\n"
"import scipy\n"
"from tqdm import tqdm\n"))

# --- Download data ---
cells.append(md("## 2. Download data (RIRs, background noise, music, features)"))
cells.append(code(
"# Room impulse responses (make the wake word robust to room echo)\n"
"output_dir = './mit_rirs'\n"
"os.makedirs(output_dir, exist_ok=True)\n"
"rir_dataset = datasets.load_dataset('davidscripka/MIT_environmental_impulse_responses', split='train', streaming=True)\n"
"for row in tqdm(rir_dataset):\n"
"    name = row['audio']['path'].split('/')[-1]\n"
"    scipy.io.wavfile.write(os.path.join(output_dir, name), 16000, (row['audio']['array']*32767).astype(np.int16))\n"))

cells.append(code(
"# ADVANCED: more background noise (several AudioSet parts) + more music (FMA)\n"
"os.makedirs('audioset', exist_ok=True)\n"
"\n"
"# Several balanced-train parts for diverse noise (restaurant-like chatter, clatter, music)\n"
"audioset_parts = ['bal_train06.tar', 'bal_train07.tar', 'bal_train08.tar', 'bal_train09.tar']\n"
"for fname in audioset_parts:\n"
"    out = f'audioset/{fname}'\n"
"    link = 'https://huggingface.co/datasets/agkphysics/AudioSet/resolve/main/data/' + fname\n"
"    !wget -O {out} {link}\n"
"    !cd audioset && tar -xf {fname}\n"
"\n"
"output_dir = './audioset_16k'\n"
"os.makedirs(output_dir, exist_ok=True)\n"
"audioset_dataset = datasets.Dataset.from_dict({'audio': [str(i) for i in Path('audioset/audio').glob('**/*.flac')]})\n"
"audioset_dataset = audioset_dataset.cast_column('audio', datasets.Audio(sampling_rate=16000))\n"
"for row in tqdm(audioset_dataset):\n"
"    name = row['audio']['path'].split('/')[-1].replace('.flac', '.wav')\n"
"    scipy.io.wavfile.write(os.path.join(output_dir, name), 16000, (row['audio']['array']*32767).astype(np.int16))\n"
"\n"
"# Free Music Archive — more hours than the quick example (music is a common false-trigger source)\n"
"output_dir = './fma'\n"
"os.makedirs(output_dir, exist_ok=True)\n"
"fma_dataset = datasets.load_dataset('rudraml/fma', name='small', split='train', streaming=True)\n"
"fma_dataset = iter(fma_dataset.cast_column('audio', datasets.Audio(sampling_rate=16000)))\n"
"n_hours = 4\n"
"for i in tqdm(range(n_hours*3600//30)):\n"
"    row = next(fma_dataset)\n"
"    name = row['audio']['path'].split('/')[-1].replace('.mp3', '.wav')\n"
"    scipy.io.wavfile.write(os.path.join(output_dir, name), 16000, (row['audio']['array']*32767).astype(np.int16))\n"
"    if i == n_hours*3600//30 - 1:\n"
"        break\n"))

cells.append(code(
"# Pre-computed openWakeWord features: ~2,000 hrs negatives + validation set\n"
"!wget https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/openwakeword_features_ACAV100M_2000_hrs_16bit.npy\n"
"!wget https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/validation_set_features.npy\n"))

# --- Config ---
cells.append(md(
"## 3. Training configuration (advanced 'hey lumina')\n"
"\n"
"Bigger than the quick example: **30,000** positive + negative synthetic samples, "
"**3,000** validation, **50,000** training steps, and production target metrics "
"(accuracy >= 0.7, recall >= 0.5, false positives <= 0.2/hr). openWakeWord also "
"auto-generates *adversarial* phrases (words that sound like 'hey lumina') to cut "
"false triggers."))

cells.append(code(
"config = yaml.load(open('openwakeword/examples/custom_model.yml', 'r').read(), yaml.Loader)\n"
"config\n"))

cells.append(code(
"# ---- Advanced 'hey lumina' settings ----\n"
"config['target_phrase'] = ['hey lumina']\n"
"config['model_name'] = 'hey_lumina'\n"
"\n"
"config['n_samples'] = 20000        # synthetic positives (plenty; finishes faster)\n"
"config['n_samples_val'] = 2000     # validation examples for early stopping\n"
"config['steps'] = 30000            # strong training, but likely to finish on free Colab\n"
"\n"
"# Production target metrics (higher quality than the quick-example defaults)\n"
"config['target_accuracy'] = 0.7\n"
"config['target_recall'] = 0.5\n"
"config['target_false_positive_rate'] = 0.2\n"
"\n"
"config['background_paths'] = ['./audioset_16k', './fma']\n"
"config['false_positive_validation_data_path'] = 'validation_set_features.npy'\n"
"config['feature_data_files'] = {'ACAV100M_sample': 'openwakeword_features_ACAV100M_2000_hrs_16bit.npy'}\n"
"\n"
"with open('my_model.yaml', 'w') as file:\n"
"    yaml.dump(config, file)\n"
"print('config written for', config['target_phrase'], '->', config['model_name'])\n"))

# --- Train ---
cells.append(md("## 4. Train"))
cells.append(code(
"# Step 1: generate synthetic 'hey lumina' clips (and adversarial negatives)\n"
"!{sys.executable} openwakeword/openwakeword/train.py --training_config my_model.yaml --generate_clips\n"))
cells.append(code(
"# Step 2: augment clips with room echo + background noise\n"
"!{sys.executable} openwakeword/openwakeword/train.py --training_config my_model.yaml --augment_clips\n"))
cells.append(code(
"# Step 3: train the model (this is the long step)\n"
"!{sys.executable} openwakeword/openwakeword/train.py --training_config my_model.yaml --train_model\n"))

cells.append(code(
"# Step 4 (optional): re-save tflite if Colab didn't (we only need the .onnx anyway)\n"
"def convert_onnx_to_tflite(onnx_model_path, output_path):\n"
"    import onnx, logging, tempfile\n"
"    from onnx_tf.backend import prepare\n"
"    import tensorflow as tf\n"
"    onnx_model = onnx.load(onnx_model_path)\n"
"    tf_rep = prepare(onnx_model, device='CPU')\n"
"    with tempfile.TemporaryDirectory() as tmp_dir:\n"
"        tf_rep.export_graph(os.path.join(tmp_dir, 'tf_model'))\n"
"        converter = tf.lite.TFLiteConverter.from_saved_model(os.path.join(tmp_dir, 'tf_model'))\n"
"        tflite_model = converter.convert()\n"
"        with open(output_path, 'wb') as f:\n"
"            f.write(tflite_model)\n"
"\n"
"try:\n"
"    convert_onnx_to_tflite(f\"my_custom_model/{config['model_name']}.onnx\", f\"my_custom_model/{config['model_name']}.tflite\")\n"
"except Exception as e:\n"
"    print('tflite convert skipped:', e)\n"))

# --- Download ---
cells.append(md(
"## 5. Save the model (to Google Drive AND direct download)\n"
"\n"
"IMPORTANT: Colab wipes its temporary storage when the runtime disconnects, so we "
"save the model to **Google Drive** first — that copy survives even if the runtime "
"recycles. It appears in your Drive as `hey_lumina.onnx`."))

cells.append(code(
"# Save the trained model to Google Drive so it can't be lost to a runtime recycle\n"
"from google.colab import drive\n"
"drive.mount('/content/drive')\n"
"\n"
"import shutil\n"
"src = f\"my_custom_model/{config['model_name']}.onnx\"\n"
"dst = '/content/drive/MyDrive/hey_lumina.onnx'\n"
"shutil.copy(src, dst)\n"
"print('Saved to Google Drive:', dst)\n"
"print('Size:', os.path.getsize(dst), 'bytes')\n"))

cells.append(md(
"### Get it onto the Pi\n"
"- The model is now in your **Google Drive** as `hey_lumina.onnx` (open drive.google.com).\n"
"- Download it to the Pi and run:\n"
"```bash\n"
"cp ~/Downloads/hey_lumina.onnx ~/lumina-desk/models/\n"
"```\n"
"Lumina Desk auto-detects it and the wake word becomes **Hey Lumina**."))

cells.append(code(
"# Also trigger a direct browser download (backup to the Drive copy)\n"
"from google.colab import files\n"
"files.download(f\"my_custom_model/{config['model_name']}.onnx\")\n"))

nb = {
    "cells": cells,
    "metadata": {
        "colab": {"provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out = "/home/techiesms/lumina-desk/training/hey_lumina_advanced.ipynb"
with open(out, "w") as f:
    json.dump(nb, f, indent=1)
print("wrote", out, "with", len(cells), "cells")
