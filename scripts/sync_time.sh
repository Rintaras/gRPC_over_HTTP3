#!/bin/bash

# タイムゾーンをJSTに設定
export TZ=Asia/Tokyo

# ホストの現在時刻を取得してコンテナの時刻を設定
HOST_DATE=$(date)
echo "Setting container time to: $HOST_DATE"
date -s "$HOST_DATE"

# 元のコマンドを実行
exec "$@" 