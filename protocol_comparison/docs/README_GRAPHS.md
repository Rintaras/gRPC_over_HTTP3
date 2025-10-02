# グラフ自動生成の使い方

## 自動生成の仕組み

ベンチマークスクリプト（`benchmark_latency.sh`）を実行すると、実験終了後に**自動的に**以下のグラフが生成されます：

1. **response_time_comparison.png** - 応答速度の比較（メイングラフ）
2. **stability_comparison.png** - 安定性の比較（標準偏差）
3. **benchmark_visualization.png** - 総合分析グラフ（6種類）
4. **benchmark_analysis.png** - 詳細分析グラフ（4種類）

## 使い方

### 1. 通常のベンチマーク実行（自動でグラフ生成）

```bash
./benchmark_latency.sh
```

実験終了後、自動的にグラフが生成されます。

### 2. グラフのみを再生成

既存のCSVファイルから再度グラフを生成する場合：

```bash
./generate_all_graphs.sh
```

### 3. 個別のグラフを生成

特定のグラフのみを生成する場合：

```bash
source venv/bin/activate

# 応答速度比較グラフ
python visualize_response_time.py

# 安定性比較グラフ
python visualize_stability.py

# 総合分析グラフ
python visualize_results.py
```

## 初回セットアップ

Python仮想環境がない場合、初回のみ以下を実行：

```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas matplotlib seaborn
```

2回目以降は自動的に既存の環境を使用します。

## 生成されるグラフの詳細

### 1. response_time_comparison.png (464KB)
**応答速度の比較 - プレゼンテーションに最適**

- 平均応答時間の比較
- 標準偏差の範囲を塗りつぶしで表示
- 各データポイントに数値ラベル付き
- サイズ: 12×8インチ、300dpi

**見るべきポイント:**
- どちらのプロトコルが速いか一目瞭然
- 低遅延ではHTTP/2、高遅延ではHTTP/3が優位

### 2. stability_comparison.png (269KB)
**安定性の比較 - 信頼性評価に最適**

- 標準偏差（ばらつき）の比較
- 低い値ほど安定
- サイズ: 10×7インチ、300dpi

**見るべきポイント:**
- 50ms環境でHTTP/3が8倍不安定
- 0msと150msではHTTP/3が安定

### 3. benchmark_visualization.png (617KB)
**総合分析グラフ - 論文に最適**

6つのグラフを含む：
1. 平均転送時間の比較（標準偏差付き）
2. 平均転送速度の比較
3. 転送時間の直接比較（棒グラフ）
4. 転送時間の分布（箱ひげ図）
5. 遅延による性能劣化の比較
6. HTTP/3 vs HTTP/2 相対性能

### 4. benchmark_analysis.png (412KB)
**詳細分析グラフ - 深掘り分析に最適**

4つのグラフを含む：
1. 標準偏差の比較（安定性指標）
2. 全データポイントの散布図（400リクエスト）
3. 成功率の比較
4. 結果サマリー（テキスト）

## グラフのカスタマイズ

グラフの見た目を変更したい場合：

1. `visualize_response_time.py` を編集 - 応答速度グラフ
2. `visualize_stability.py` を編集 - 安定性グラフ
3. `visualize_results.py` を編集 - 総合グラフ

変更例：
- `plt.rcParams['figure.figsize'] = (12, 8)` - サイズ変更
- `plt.rcParams['font.size'] = 12` - フォントサイズ
- `colors = {...}` - 色の変更
- `dpi=300` - 解像度変更

## トラブルシューティング

### グラフが生成されない

```bash
# Python環境を確認
which python3

# 仮想環境を再作成
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install pandas matplotlib seaborn
```

### 文字化けする

macOSでは自動的にHiragino Sansを使用します。
それでも文字化けする場合は、visualize_*.pyの先頭で別のフォントを指定してください。

### CSVファイルが見つからない

```bash
# CSVファイルを確認
ls -l benchmark_results_*.csv

# 最新のファイル
ls -t benchmark_results_*.csv | head -1
```

## ファイル構成

```
protocol_comparison/
├── benchmark_latency.sh              # ベンチマーク実行（グラフ自動生成付き）
├── generate_all_graphs.sh            # グラフのみ生成
├── visualize_response_time.py        # 応答速度グラフ
├── visualize_stability.py            # 安定性グラフ
├── visualize_results.py              # 総合グラフ
├── benchmark_results_YYYYMMDD_HHMMSS.csv  # データ
├── response_time_comparison.png      # 出力: 応答速度
├── stability_comparison.png          # 出力: 安定性
├── benchmark_visualization.png       # 出力: 総合分析
└── benchmark_analysis.png            # 出力: 詳細分析
```

## ワークフロー

1. **実験実行**: `./benchmark_latency.sh`
2. **自動でグラフ生成** ← 何もしなくてOK！
3. **グラフ確認**: `open *.png`
4. **プレゼン/論文に使用**

これで実験が終わったら自動的に美しいグラフが手に入ります！

