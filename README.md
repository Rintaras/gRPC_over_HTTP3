# HTTP/3 vs HTTP/2 Performance Benchmark

## 概要
このプロジェクトは、HTTP/3とHTTP/2の性能比較をDocker環境で実施するベンチマークツールです。

## 技術スタック

### コンテナ化・オーケストレーション
- **Docker Compose**: マルチコンテナ環境の管理
- **Docker**: コンテナ化による環境の再現性確保

### Webサーバー・プロトコル
- **nginx**: HTTP/2/HTTP/3対応Webサーバー
- **HTTP/2**: バイナリプロトコル、ヘッダー圧縮、マルチプレクシング
- **HTTP/3**: QUICベース、UDP上での信頼性確保、0-RTT接続

### ベンチマーク・テストツール
- **h2load**: HTTP/2/HTTP/3専用ベンチマークツール
- **tc/netem**: Linuxネットワークエミュレーション（遅延・損失・帯域制限）

### データ分析・可視化
- **Python 3.11**: メイン分析言語
- **numpy**: 数値計算・統計処理
- **matplotlib**: グラフ生成・可視化
- **seaborn**: 統計的データ可視化
- **pandas**: データ処理・CSV操作

### ネットワーク・システム
- **gRPC**: HTTP/2上でのRPCフレームワーク
- **QUIC**: UDP上での信頼性確保プロトコル
- **TLS 1.3**: 暗号化・認証
- **Linux tc**: トラフィック制御・ネットワークエミュレーション

### 開発・運用ツール
- **Bash**: 自動化スクリプト
- **Git**: バージョン管理
- **CSV**: データ保存形式
- **PNG**: グラフ出力形式

## 実験運用ルール

### 1. 専用ディレクトリ作成（必須）
- 各ベンチマーク実行時に、タイムスタンプ付きの専用ディレクトリを自動作成
- 例：`logs/benchmark_20240705_143022/`
- 全てのログ・CSV・レポート・グラフをそのディレクトリに保存

### 2. グラフ生成の義務付け（必須）
- 全てのベンチマークで、必ずグラフ（PNG）とサマリーレポート（TXT）を自動生成
- 数値データだけでなく、視覚的な比較も必須
- 再現性と比較性を確保

### 3. 実験データの整理
- 過去の実験データと混在しないよう、専用ディレクトリで管理
- 各実験の条件・結果を明確に分離

## ベンチマークスクリプト

### 1. 基本性能比較
```bash
./scripts/run_bench.sh
```
- 通常のネットワーク条件下でのHTTP/2 vs HTTP/3比較
- 出力: `logs/benchmark_YYYYMMDD_HHMMSS/`

### 2. 高遅延・低帯域テスト
```bash
./scripts/run_high_latency_bandwidth_test.sh
```
- 論文の仮説検証：高遅延・低帯域環境でのHTTP/3優位性
- 出力: `logs/high_latency_bandwidth_YYYYMMDD_HHMMSS/`

### 3. 極端な条件テスト
```bash
./scripts/run_extreme_conditions_test.sh
```
- 極端なネットワーク条件下での性能逆転現象の検証
- 出力: `logs/extreme_YYYYMMDD_HHMMSS/`

## 出力ファイル構成

各実験ディレクトリには以下が含まれます：

### ログファイル
- `h2_*.log`: HTTP/2ベンチマークログ
- `h3_*.log`: HTTP/3ベンチマークログ

### データファイル
- `*_data.csv`: 測定データ（CSV形式）
- `*_report.txt`: 詳細分析レポート

### グラフファイル（必須）
- `performance_comparison_overview.png`: 全体性能比較
- `detailed_performance_analysis.png`: 詳細分析グラフ
- `performance_summary_statistics.png`: 統計サマリー

### サマリーレポート（必須）
- `performance_reversal_summary.txt`: 性能逆転現象の分析

## 分析スクリプト

### 手動分析
```bash
# 基本性能分析
python3 scripts/analyze_results.py <log_directory>

# 高遅延・低帯域分析
python3 scripts/analyze_high_latency_results.py <log_directory>

# 極端な条件分析
python3 scripts/analyze_extreme_conditions.py <log_directory>

# グラフ生成
python3 scripts/generate_performance_graphs.py <log_directory>
```

## 環境セットアップ

```bash
# コンテナビルド
docker-compose build

# 環境起動
docker-compose up -d

# ベンチマーク実行
./scripts/run_bench.sh
```

## 重要な発見

### 性能逆転現象
- **閾値**: 遅延400ms以上、帯域5Mbps以下でHTTP/3が優位
- **衛星通信環境**: 800ms遅延、20%損失、2Mbps帯域でHTTP/3が63%優位
- **実用的指針**: 特定の極端な条件下でのみHTTP/3が明確に優位

### 論文の仮説検証結果
✅ **再現された主張**:
- 極端な高遅延環境でのHTTP/3優位性
- 極低帯域環境でのHTTP/3優位性
- 高損失環境でのHTTP/3優位性

❌ **再現されなかった部分**:
- レイテンシではHTTP/2が一貫して優位
- 接続時間ではHTTP/2が優位

## 注意事項

1. **実験データの分離**: 各実験は専用ディレクトリで管理
2. **グラフ生成の必須化**: 全ての実験で視覚的比較を実施
3. **再現性の確保**: 条件・結果の明確な記録
4. **公平な比較**: ウォームアップと測定フェーズの分離

## ライセンス
MIT License 