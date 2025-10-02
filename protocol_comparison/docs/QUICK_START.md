# クイックスタートガイド

## 5分で始めるHTTP/2 vs HTTP/3ベンチマーク

### 1. 初回セットアップ（1回のみ）

```bash
mkcert -install
mkcert localhost 127.0.0.1 ::1

python3 -m venv venv
source venv/bin/activate
pip install pandas matplotlib seaborn
```

### 2. ベンチマーク実行

```bash
./benchmark_latency.sh
```

これだけで完了！

実行内容：
- ✅ Dockerコンテナ起動
- ✅ 4つの遅延条件でテスト（0ms, 50ms, 100ms, 150ms）
- ✅ 各条件50回のリクエスト（計400リクエスト）
- ✅ 統計分析
- ✅ グラフ自動生成（4種類）

### 3. 結果確認

実験結果は`logs/タイムスタンプ/`に保存されます：

```bash
# 最新の実験ディレクトリを確認
ls -lt logs/ | head -5

# グラフを開く
open logs/最新のタイムスタンプ/response_time_comparison.png
```

または、最新の結果を自動で開く：

```bash
open logs/$(ls -t logs/ | head -1)/response_time_comparison.png
```

---

## 残されたファイル

### 必須スクリプト（4個）

1. **benchmark_latency.sh** (9.7KB)
   - メインベンチマーク実行
   - グラフ自動生成機能付き
   - 統計分析機能付き

2. **generate_all_graphs.sh** (1.5KB)
   - グラフのみ再生成
   - CSVファイルから再作成

3. **tc_setup.sh** (661B)
   - トラフィック制御設定
   - ルーター内で使用

4. **tc_reset.sh** (247B)
   - トラフィック制御リセット
   - ルーター内で使用

### Python可視化スクリプト（3個）

1. **visualize_response_time.py**
   - 応答速度比較グラフ生成
   - プレゼン用メイングラフ

2. **visualize_stability.py**
   - 安定性比較グラフ生成
   - 標準偏差の可視化

3. **visualize_results.py**
   - 総合分析グラフ生成
   - 6+4グラフの詳細分析

### ドキュメント（5個）

1. **README.md** - プロジェクト全体の説明
2. **QUICK_START.md** - このファイル
3. **README_GRAPHS.md** - グラフ生成の詳細ガイド
4. **BENCHMARK_ANALYSIS.md** - 詳細な分析結果
5. **EXPERIMENT_CONDITIONS.md** - 実験条件の詳細

### Docker構成（3個）

1. **docker-compose.router_tc.yml** - メイン構成
2. **Dockerfile.router_tc** - ルーターイメージ
3. **Dockerfile.http3_test** - HTTP/3クライアントイメージ

---

## 簡単な使い方まとめ

### ベンチマーク実行→グラフ生成（一発で完了）

```bash
./benchmark_latency.sh
```

### グラフだけ作り直す

```bash
./generate_all_graphs.sh
```

### カスタム実験

```bash
# 帯域や遅延を変更して起動
BANDWIDTH=10mbit LATENCY=100ms LOSS=0% \
  docker-compose -f docker-compose.router_tc.yml up -d

# tc設定を確認
docker exec network-router tc qdisc show dev eth0

# HTTP/2テスト
curl -k --http2 https://localhost:8444/1mb -o /dev/null \
  -w "時間: %{time_total}s\n"

# クリーンアップ
docker-compose -f docker-compose.router_tc.yml down
```

---

## 出力されるグラフ

実験終了後、4つのグラフが自動生成されます：

| ファイル名 | 内容 | 用途 |
|-----------|------|------|
| response_time_comparison.png | 応答速度比較 | プレゼンのメイン |
| stability_comparison.png | 安定性比較 | 信頼性評価 |
| benchmark_visualization.png | 総合分析（6グラフ） | 論文用 |
| benchmark_analysis.png | 詳細分析（4グラフ） | 深掘り分析 |

すべて300dpi、印刷品質で出力されます。

---

## よくある質問

### Q: 実験にどれくらい時間がかかりますか？

A: 約20-30分（400リクエスト + グラフ生成）

### Q: グラフをカスタマイズできますか？

A: はい。`visualize_*.py`を編集してください。詳細は`README_GRAPHS.md`参照。

### Q: 別の条件でテストしたい

A: `benchmark_latency.sh`内の条件を編集してください：
- `BANDWIDTH="5mbit"` - 帯域変更
- `run_benchmark "200ms" "..."` - 遅延追加
- `ITERATIONS=100` - 試行回数変更

### Q: HTTP/3が失敗する

A: Docker内でHTTP/3クライアントを実行しているため、ホストのcurlは不要です。
スクリプトが自動的に適切なクライアントを使用します。

---

## トラブルシューティング

### コンテナが起動しない

```bash
docker-compose -f docker-compose.router_tc.yml down
docker-compose -f docker-compose.router_tc.yml up -d --build
docker logs network-router
docker logs http3-server
```

### グラフが生成されない

```bash
# Python環境を確認
ls -la venv/

# 再作成
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install pandas matplotlib seaborn
```

### 実験を中断したい

`Ctrl+C`で中断できます。途中まで取得したデータはCSVに保存されます。

---

これで簡単に実験を開始できます！

