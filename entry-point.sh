#!/usr/bin/env bash

# 載入 .env 檔案並將設定值套用到環境變數
source .env

python3 -m pip install -r requirements.txt
echo "System starting... $HOST_IP:$HOST_PORT"

python3 server.py
echo "System ending..."
