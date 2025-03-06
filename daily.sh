#!/bin/bash

# 初始化conda
eval "$(conda shell.bash hook)"
conda activate binance_klines_syncer

echo "Starting daily data sync..."
python sync.py --type daily
echo "Daily data sync completed."