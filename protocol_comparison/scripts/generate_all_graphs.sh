#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================="
echo "グラフ自動生成スクリプト"
echo "========================================="
echo ""

if [ ! -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo "Python仮想環境を作成中..."
    cd "$PROJECT_ROOT"
    python3 -m venv venv
    source venv/bin/activate
    echo "必要なパッケージをインストール中..."
    pip install -q pandas matplotlib seaborn
else
    source "$PROJECT_ROOT/venv/bin/activate"
fi

CSV_FILE=$(find "$PROJECT_ROOT/logs" -name "benchmark_results.csv" -type f 2>/dev/null | sort -r | head -1)

if [ -z "$CSV_FILE" ]; then
    echo "エラー: ベンチマーク結果ファイルが見つかりません"
    exit 1
fi

LOG_DIR="$(dirname "$CSV_FILE")"

echo "データソース: $CSV_FILE"
echo "出力先: $LOG_DIR"
echo ""

export BENCHMARK_CSV="$CSV_FILE"
export BENCHMARK_OUTPUT_DIR="$LOG_DIR"

echo "1. 応答速度比較グラフを生成中..."
python3 "$SCRIPT_DIR/visualize_response_time.py" 2>&1 | grep "グラフを保存"

echo ""
echo "2. 安定性比較グラフを生成中..."
python3 "$SCRIPT_DIR/visualize_stability.py" 2>&1 | grep "グラフを保存"

echo ""
echo "3. 総合分析グラフを生成中..."
python3 "$SCRIPT_DIR/visualize_results.py" 2>&1 | grep "グラフを保存"

echo ""
echo "========================================="
echo "グラフ生成完了！"
echo "========================================="
echo ""
echo "生成されたグラフ:"
ls -lh "$LOG_DIR"/*.png 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'

echo ""
echo "すべてのグラフを開く場合:"
echo "  open $LOG_DIR/*.png"

