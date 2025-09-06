# HTTP/3 vs HTTP/2 Performance Benchmark

## 概要
このプロジェクトは、HTTP/3とHTTP/2の性能比較をDocker環境で実施するベンチマークツールです。Docker環境とRaspberry Pi 5実機サーバーとの比較実験も含む包括的な性能評価システムです。

## 技術スタック

### コンテナ化・オーケストレーション
- **Docker Compose**: マルチコンテナ環境の管理（client, router, server）
- **Docker**: コンテナ化による環境の再現性確保
- **GitHub Actions**: CI/CDによるDockerイメージの自動ビルド

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

### CI/CD
- **GitHub Actions**: CI（Python flake8/Rust build・clippy/Docker build）と CD（GHCR push、任意の SSH デプロイ）

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

## CI/CD の使い方

### CI
- `main` ブランチへの push または PR で自動実行
- flake8、Rust ビルド/Clippy、Docker イメージビルドを検証

### CD（GHCR）
- `main` へ push で `server/client/router` を GHCR に push
- タグは `latest` とコミット短縮 SHA

### 任意の SSH デプロイ
GitHub リポジトリの Secrets に以下を設定すると、`docker compose pull && up -d` を自動実行します。

- `DEPLOY_HOST`: ホスト
- `DEPLOY_USER`: ユーザー
- `DEPLOY_KEY`: OpenSSH 秘密鍵（`id_ed25519` 推奨）

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

### 解決方法
- CSV区切り文字の統一
- Python仮想環境の使用
- 証明書のSubjectAltName設定
- Docker Compose設定の確認

## ドキュメント

- [Raspberry Pi 5 セットアップガイド](RASPBERRY_PI_SETUP.md) - 詳細なセットアップ手順
- [Raspberry Pi 5 プロジェクトREADME](README_RASPBERRY_PI.md) - Raspberry Pi 5専用ドキュメント

## 今後の開発予定

### 短期目標
- [ ] より多くのネットワーク条件でのテスト
- [ ] 統計的有意性検定の実装
- [ ] リアルタイムモニタリングの追加
- [ ] Raspberry Pi 5実機環境での性能比較

### 長期目標
- [ ] クラウド環境での大規模テスト
- [ ] 機械学習による性能予測
- [ ] 他のQUIC実装との比較
- [ ] 複数デバイスでの負荷分散テスト

## ライセンス
MIT License