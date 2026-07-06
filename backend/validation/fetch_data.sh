#!/usr/bin/env bash
# Downloads the three external validation datasets into validation/data/
# (gitignored — re-run this after a fresh clone, before `python -m validation.run_all`).
set -euo pipefail
cd "$(dirname "$0")/data"

echo "Fetching vedastro-org birth-location dataset (MIT license)..."
curl -sL "https://huggingface.co/datasets/vedastro-org/15000-Famous-People-Birth-Date-Location/resolve/main/PersonList-15k.csv" -o birth_location.csv

echo "Fetching vedastro-org marriage/divorce dataset (MIT license)..."
curl -sL "https://huggingface.co/datasets/vedastro-org/15000-Famous-People-Marriage-Divorce-Info/resolve/main/MarriageInfoDataset.csv" -o marriage.csv

echo "Fetching AstroDatabank C-sample (Astrodienst-offered research sample, not scraped)..."
curl -sL "https://www.astro.com/adbexport/c_sample.zip" -o c_sample.zip
mkdir -p c_sample
unzip -o -q c_sample.zip -d c_sample

echo "Done. $(wc -l < birth_location.csv) birth rows, $(wc -l < marriage.csv) marriage rows, $(du -h c_sample/c_sample.xml | cut -f1) C-sample XML."
