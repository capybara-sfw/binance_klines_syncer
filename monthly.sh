#!/bin/bash

# 初始化conda
eval "$(conda shell.bash hook)"
conda activate binance_klines_syncer

echo "Starting monthly data sync..."
python sync.py --type monthly
echo "Monthly data sync completed."