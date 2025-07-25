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
- **リクエスト数**: 200,000回（ウォームアップ20,000回 + 測定180,000回）
- 出力: `logs/benchmark_YYYYMMDD_HHMMSS/`

### 2. 5回自動実行（平均化）
```bash
./scripts/run_bench_5times.sh
```
- 5回のベンチマークを自動実行し、データを平均化
- **各回のリクエスト数**: 200,000回
- **総リクエスト数**: 1,000,000回（5回 × 200,000回）
- **平均化グラフ**: 5回の結果を平均化した信頼性の高いグラフ
- 出力: `logs/benchmark_5times_YYYYMMDD_HHMMSS/`

### 3. 高負荷テスト
```bash
./scripts/run_bench_highload.sh
```
- 高負荷環境でのHTTP/2 vs HTTP/3比較
- **リクエスト数**: 200,000回（ウォームアップ20,000回 + 測定180,000回）
- 出力: `logs/benchmark_highload_YYYYMMDD_HHMMSS/`

### 4. 軽量テスト（高速実行）
```bash
./scripts/run_bench2.sh
./scripts/run_bench3.sh
```
- 軽量なベンチマーク（開発・テスト用）
- **リクエスト数**: 20,000回（ウォームアップ2,000回 + 測定18,000回）
- 出力: `logs/benchmark2_YYYYMMDD_HHMMSS/`

### 5. 高遅延・低帯域テスト
```bash
./scripts/run_high_latency_bandwidth_test.sh
```
- 論文の仮説検証：高遅延・低帯域環境でのHTTP/3優位性
- 出力: `logs/high_latency_bandwidth_YYYYMMDD_HHMMSS/`

### 6. 極端な条件テスト
```bash
./scripts/run_extreme_conditions_test.sh
```
- 極端なネットワーク条件下での性能逆転現象の検証
- 出力: `logs/extreme_YYYYMMDD_HHMMSS/`

### 7. 境界値分析（信頼性向上版）
```bash
./scripts/run_improved_boundary_analysis.sh
```
- 信頼性の高い境界値分析
- **改善点**: 複数回測定、外れ値除去、統計的有意性検定
- **測定回数**: 各条件で3回測定し平均化
- **信頼区間**: 95%信頼区間の計算
- 出力: `logs/improved_boundary_analysis_YYYYMMDD_HHMMSS/`

## 境界値分析の問題点と改善策

### 🔍 検出された問題点

#### 1. **極端な性能差の異常値**
- **18ms遅延**: HTTP/2が1,846 req/s、HTTP/3が7,411 req/s（**75%の性能差**）
- この極端な差は測定エラーまたは異常なネットワーク条件を示唆

#### 2. **測定の不整合性**
- **6ms遅延**: HTTP/2が2,205 req/s、HTTP/3が3,548 req/s
- **13ms遅延**: HTTP/2が8,980 req/s、HTTP/3が9,522 req/s
- 遅延が増加しているのにHTTP/2の性能が向上しているのは不自然

#### 3. **統計的安定性の問題**
- 同じ条件下でも測定値に大きなばらつき
- 境界値検出の信頼性に疑問

#### 4. **単回測定の限界**
- 1回の測定では外れ値の影響を受けやすい
- 統計的有意性の検証が不十分

### 🔧 改善策

#### 1. **複数回測定による平均化**
- 各条件で3回測定を実行
- 外れ値除去（3σルール）を適用
- 信頼性の高い平均値を算出

#### 2. **統計的有意性検定**
- 95%信頼区間の計算
- t検定による有意性判定
- 信頼区間の重複チェック

#### 3. **エラーバー付きグラフ**
- 標準偏差をエラーバーとして表示
- 測定の信頼性を視覚化
- 境界値の統計的有意性を明示

#### 4. **測定安定性の評価**
- 標準偏差の比較
- 有効測定回数の追跡
- 測定品質の定量化

### 📊 改善された分析手法

#### 信頼性向上された境界値分析
```bash
# 改善された境界値分析の実行
./scripts/run_improved_boundary_analysis.sh
```

#### 主な改善点
- **複数回測定**: 各条件で3回測定し平均化
- **外れ値除去**: 3σルールによる異常値除去
- **統計的有意性**: 95%信頼区間による有意性検定
- **信頼区間表示**: エラーバー付きグラフ
- **測定安定性評価**: 標準偏差と有効測定回数の追跡

#### 出力ファイル
- `improved_boundary_analysis.png`: 信頼性付きグラフ
- `reliability_report.txt`: 詳細な信頼性レポート
- 統計的有意性と信頼区間を含む結果

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