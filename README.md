# HTTP/3 vs HTTP/2 Performance Benchmark

## 概要
このプロジェクトは、HTTP/3とHTTP/2の性能比較をDocker環境で実施するベンチマークツールです。Docker環境とRaspberry Pi 5実機サーバーとの比較実験も含む包括的な性能評価システムです。

## 技術スタック

### コンテナ化・オーケストレーション
- **Docker Compose**: マルチコンテナ環境の管理（client, router, server）
- **Docker**: コンテナ化による環境の再現性確保

### Webサーバー・プロトコル
- **nginx**: HTTP/2/HTTP/3対応Webサーバー（Alt-SvcヘッダーによるHTTP/3通知）
- **HTTP/2**: バイナリプロトコル、ヘッダー圧縮、マルチプレクシング
- **HTTP/3**: QUICベース、UDP上での信頼性確保、0-RTT接続
- **quiche (Cloudflare)**: Rust実装のHTTP/3サーバー・クライアント

### ベンチマーク・テストツール
- **h2load**: HTTP/2/HTTP/3専用ベンチマークツール
- **quiche-client**: HTTP/3専用クライアントツール
- **tc/netem**: Linuxネットワークエミュレーション（遅延・損失・帯域制限）
- **curl**: HTTP/2接続テスト

### データ分析・可視化
- **Python 3.13**: メイン分析言語
- **numpy**: 数値計算・統計処理
- **matplotlib**: グラフ生成・可視化（Aggバックエンド対応）
- **pandas**: データ処理・CSV操作
- **scipy**: 統計解析（Python 3.13対応版）

### ネットワーク・システム
- **gRPC**: HTTP/2上でのRPCフレームワーク
- **QUIC**: UDP上での信頼性確保プロトコル
- **TLS 1.3**: 暗号化・認証（自己署名証明書対応）
- **Linux tc**: トラフィック制御・ネットワークエミュレーション

### 開発・運用ツール
- **Bash**: 自動化スクリプト
- **Git**: バージョン管理
- **SSH/SCP**: リモートサーバー管理
- **CSV**: データ保存形式
- **PNG**: グラフ出力形式


## 実験環境

### ローカル環境（Docker）
- **クライアント**: HTTP/2/HTTP/3ベンチマーク実行
- **ルーター**: ネットワークエミュレーション（tc/netem）
- **サーバー**: nginx + quiche HTTP/3サーバー

### リモート環境（Raspberry Pi 5）
- **IPアドレス**: 172.30.0.2
- **サーバー**: nginx + HTTP/3対応サーバー（ネイティブインストール）
- **証明書**: 自己署名TLS証明書（IPアドレス対応）
- **ポート**: HTTP/2 (443), HTTP/3 (443)
- **インストール**: Docker不使用、ネイティブインストール

## ベンチマークスクリプト

### 1. ローカル環境ベンチマーク
```bash
./scripts/run_bench.sh
```
- 4つのネットワーク条件（0ms, 75ms, 150ms, 225ms遅延、3%パケットロス）
- **リクエスト数**: 50,000回（ウォームアップ20,000回 + 測定30,000回）
- **接続数**: 100、スレッド数: 20
- 出力: `logs/benchmark_YYYYMMDD_HHMMSS/`

### 2. Raspberry Pi 5実機サーバーベンチマーク
```bash
./scripts/run_bench_raspberry_pi.sh
```
- リモートRaspberry Pi 5実機サーバーに対するベンチマーク
- 同じネットワーク条件での性能比較
- HTTP/2（nginx）とHTTP/3（nginx）の両方でテスト
- 出力: `logs/benchmark_raspberry_pi_YYYYMMDD_HHMMSS/`

### 3. 軽量テスト（開発・テスト用）
```bash
./scripts/run_bench2.sh
./scripts/run_bench3.sh
```
- 軽量なベンチマーク
- **リクエスト数**: 20,000回
- 出力: `logs/benchmark2_YYYYMMDD_HHMMSS/`

## グラフ生成・分析

### 自動グラフ生成
```bash
python3 scripts/simple_graph_generator.py <log_directory> \
  --dpi 300 \
  --summary-csv <path/to/summary.csv> \
  --only 0ms_3pct,75ms_3pct \
  --format png \
  --title "HTTP/2 vs HTTP/3 Benchmark"
```
- **2段組みグラフ**: レスポンス時間比較 + パフォーマンス改善率
- **CSV解析**: カンマ・タブ区切り両対応
- **エラーバーなし**: クリーンなグラフ表示
- **出力形式**: PNG（高解像度300dpi）
 - **オプション**: `--only` で条件キーを絞り込み、`--summary-csv` で比較サマリーCSVを出力
 - **表示制御**: `--no-annotations` でグラフ上の改善率注釈（矢印）を抑制

注: 旧 `compute_percentiles.py` はサマリー出力へ統合済みです。

### 生成されるグラフ
- `performance_comparison_graph.png`: シンプルな比較グラフ
- `performance_summary_graph.png`: 2段組みの詳細分析グラフ

## 環境セットアップ

### ローカル環境
```bash
# 依存関係インストール
pip install -r requirements.txt

# コンテナビルド
docker-compose build

# 環境起動
docker-compose up -d

# ベンチマーク実行
./scripts/run_bench.sh
```


### Raspberry Pi 5環境（ネイティブインストール）
```bash
# サーバーセットアップ（Raspberry Pi 5上）
wget https://raw.githubusercontent.com/your-repo/gRPC_over_HTTP3/main/scripts/raspberry_pi_setup.sh
chmod +x raspberry_pi_setup.sh
sudo ./raspberry_pi_setup.sh

# または手動セットアップ（Docker不使用）
sudo apt update
sudo apt install -y nginx openssl build-essential cmake pkg-config libssl-dev

# 証明書生成
openssl req -x509 -newkey rsa:2048 -keyout /etc/ssl/private/grpc-server.key -out /etc/ssl/certs/grpc-server.crt -days 365 -nodes -subj "/CN=grpc-server-pi.local"

# nginx HTTP/3サーバー起動
sudo systemctl start nginx
```

**注意**: Raspberry Pi 5ではDockerを使用せず、ネイティブインストールのみです。

## 重要な発見・成果

### 1. ネットワーク条件による性能差
- **0ms遅延**: HTTP/2が1,469ms、HTTP/3が30,028ms
- **75ms遅延**: HTTP/2が優位、HTTP/3は約62%遅い
- **150ms遅延**: HTTP/2が優位、HTTP/3は約50%遅い
- **225ms遅延**: HTTP/2が優位、HTTP/3は約65%遅い

### 2. HTTP/3の特性
- **接続確立**: 0-RTT接続の利点
- **パケットロス耐性**: 3%パケットロス環境での安定性
- **遅延環境**: 高遅延環境での性能劣化

### 3. 実用的な知見
- **通常環境**: HTTP/2が一貫して優位
- **極端環境**: 特定条件下でのみHTTP/3が優位
- **選択指針**: 用途に応じたプロトコル選択の重要性

## 出力ファイル構成

### ベンチマーク結果
- `h2_*.log`: HTTP/2ベンチマークログ
- `h3_*.log`: HTTP/3ベンチマークログ
- `h2_*.csv`: HTTP/2測定データ（CSV形式）
- `h3_*.csv`: HTTP/3測定データ（CSV形式）

### 分析結果
- `performance_report.txt`: テキストベースの性能レポート
- `performance_comparison_graph.png`: 性能比較グラフ
- `performance_summary_graph.png`: 2段組み詳細分析グラフ
- `benchmark_params.txt`: ベンチマークパラメータ

## トラブルシューティング

### よくある問題
1. **CSVファイルが空**: 区切り文字の問題（タブ→カンマ変換）
2. **グラフ生成エラー**: matplotlib依存関係の問題
3. **HTTP/3接続失敗**: TLS証明書のIPアドレス不整合
4. **Docker接続エラー**: コンテナ間ネットワーク設定

### HTTP/3エラー問題

#### 発生するエラーの種類
HTTP/3では以下のエラーが高頻度で発生します：

**プロトコルエラー**:
- `InternalError`: HTTP/3スタック内部エラー
- `ExcessiveLoad`: 過負荷動作の検出
- `StreamCreationError`: 受け入れられないストリームの作成
- `ClosedCriticalStream`: 必須クリティカルストリームの切断
- `MissingSettings`: SETTINGSフレームの欠落
- `FrameUnexpected`: 不正なフレーム受信
- `FrameError`: フレームレイアウト違反

**ネットワーク条件によるエラー**:
- **高遅延環境**: 225ms遅延で50%以上のリクエスト失敗
- **パケット損失**: 3%損失でQUICの信頼性メカニズムが過負荷
- **接続タイムアウト**: 高遅延環境での接続確立失敗
- **UDP制限**: ファイアウォールやNATでの制限

**h2loadの制限**:
- HTTP/3サポートの不完全性
- QUIC実装の制限
- 高負荷時の接続プール管理問題

#### エラー発生パターン
```
requests: 30000 total, 14700 started, 14700 done, 14700 succeeded, 15300 failed, 15300 errored, 0 timeout
```

**対策**:
- ネットワーク条件を緩和（遅延・損失率を下げる）
- リクエスト数を削減して負荷を軽減
- HTTP/2フォールバックの活用
- quiche-clientの使用（h2loadより安定）

### 解決方法
- CSV区切り文字の統一
- Python仮想環境の使用
- 証明書のSubjectAltName設定
- Docker Compose設定の確認
- HTTP/3エラー時はHTTP/2フォールバックを活用

## ドキュメント

### 技術ドキュメント
- [Raspberry Pi 5 セットアップガイド](RASPBERRY_PI_SETUP.md) - 詳細なセットアップ手順
- [Raspberry Pi 5 プロジェクトREADME](README_RASPBERRY_PI.md) - Raspberry Pi 5専用ドキュメント
- [無線LAN設定ガイド](WIRELESS_SETUP.md) - 無線LAN接続時の設定手順
- [ネットワークアーキテクチャ](NETWORK_ARCHITECTURE.md) - 通信の仕組み詳細

### Cursor用ドキュメント
- [Cursor用 セットアップガイド](CURSOR_RASPBERRY_PI_SETUP.md) - Cursorで構築するための詳細手順
- [Cursor用 プロンプト集](CURSOR_PROMPTS.md) - 構築用プロンプトの完全版
- [Cursor用 クイックスタート](CURSOR_QUICK_START.md) - 即座に使用できるプロンプト
- [Cursor用 トラブルシューティング](CURSOR_TROUBLESHOOTING.md) - 問題解決ガイド

### プロジェクト概要
- [プロジェクトの目的](PROJECT_PURPOSE.md) - プロジェクトの目的と概要の詳細
- [ベンチマークガイド](BENCHMARK_GUIDE.md) - Raspberry Pi 5サーバー検証・ベンチマーク実行ガイド

## 今後の開発予定

### 仮装環境の大規模見直し（進行中）
現在、仮装環境（Docker環境）の大幅な見直しを実施しています：

#### 見直しの背景
- **HTTP/3エラー問題**: 高遅延・高損失環境での接続失敗率が50%以上
- **h2loadの制限**: HTTP/3サポートの不完全性による測定精度の低下
- **ネットワークエミュレーション**: tc/netemの設定最適化が必要
- **ベンチマークツール**: より安定したHTTP/3対応ツールへの移行検討

#### 見直し内容
- [ ] **ベンチマークツールの刷新**: h2loadからquiche-clientやcurl HTTP/3への移行
- [ ] **ネットワークエミュレーション最適化**: より現実的なネットワーク条件の設定
- [ ] **Docker構成の見直し**: コンテナ間通信の最適化とリソース制限の調整
- [ ] **エラーハンドリング強化**: HTTP/3エラー時の自動フォールバック機能
- [ ] **測定精度向上**: 統計的有意性を確保するためのサンプル数調整
- [ ] **ログ分析機能強化**: エラー原因の詳細分析と可視化

#### 影響範囲
- 既存のベンチマークスクリプトの大幅改修
- 新しいベンチマークツールの統合
- Docker Compose設定の更新
- 分析スクリプトの対応

### 短期目標
- [ ] 仮装環境見直しの完了
- [ ] 新しいベンチマークツールでの検証
- [ ] エラー率の大幅削減（目標: 10%以下）
- [ ] Raspberry Pi 5実機環境での性能比較

### 長期目標
- [ ] クラウド環境での大規模テスト
- [ ] 機械学習による性能予測
- [ ] 他のQUIC実装との比較
- [ ] 複数デバイスでの負荷分散テスト

## ライセンス
MIT License