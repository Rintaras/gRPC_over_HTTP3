# Raspberry Pi 5 ベンチマークガイド

## 概要

Raspberry Pi 5サーバーが構築された後の検証とベンチマーク実行のための包括的なガイドです。

## 利用可能なベンチマークスクリプト

### 1. **verify_raspberry_pi_server.sh** - サーバー検証スクリプト
構築されたサーバーの基本的な動作確認を行います。

```bash
./scripts/verify_raspberry_pi_server.sh
```

**機能:**
- 基本的な接続テスト（Ping、ポート443）
- SSL証明書の確認
- HTTP/2接続テスト
- HTTP/3接続テスト
- パフォーマンステスト
- ネットワーク統計収集
- 軽量ベンチマーク実行

### 2. **quick_benchmark_raspberry_pi.sh** - クイックベンチマーク
軽量なベンチマークを実行してサーバーの性能を確認します。

```bash
./scripts/quick_benchmark_raspberry_pi.sh
```

**機能:**
- 軽量版ベンチマーク（5,000リクエスト）
- 3つのネットワーク条件でのテスト
- HTTP/2とHTTP/3の両方でテスト
- 結果サマリーの自動生成

### 3. **run_bench_raspberry_pi.sh** - 本格ベンチマーク
完全なベンチマークを実行して詳細な性能分析を行います。

```bash
./scripts/run_bench_raspberry_pi.sh
```

**機能:**
- 本格的なベンチマーク（50,000リクエスト）
- 4つのネットワーク条件でのテスト
- グラフ生成まで完全自動化
- 詳細な性能レポート

### 4. **raspberry_pi_benchmark_suite.sh** - ベンチマークスイート
包括的なベンチマークとテストを実行するインタラクティブなスイートです。

```bash
./scripts/raspberry_pi_benchmark_suite.sh
```

**機能:**
- インタラクティブメニュー
- 複数のテストオプション
- カスタムベンチマーク設定
- ネットワーク診断
- パフォーマンス分析

## 実行手順

### ステップ1: 事前準備

```bash
# Docker環境の起動
docker-compose up -d

# コンテナの確認
docker ps
```

### ステップ2: サーバー検証

```bash
# 基本的な動作確認
./scripts/verify_raspberry_pi_server.sh
```

**期待される結果:**
- ✅ Ping to Raspberry Pi 5: SUCCESS
- ✅ Port 443 on Raspberry Pi 5: OPEN
- ✅ HTTP/2 local connection: SUCCESS
- ✅ HTTP/2 Docker client connection: SUCCESS

### ステップ3: クイックベンチマーク

```bash
# 軽量なベンチマーク実行
./scripts/quick_benchmark_raspberry_pi.sh
```

**期待される結果:**
- HTTP/2ベンチマーク: SUCCESS
- HTTP/3ベンチマーク: SUCCESS（またはNOT SUPPORTED）
- パフォーマンス数値の表示

### ステップ4: 本格ベンチマーク

```bash
# 完全なベンチマーク実行
./scripts/run_bench_raspberry_pi.sh
```

**期待される結果:**
- 4つのネットワーク条件でのテスト完了
- グラフファイルの生成
- 詳細な性能レポート

## トラブルシューティング

### よくある問題

#### 1. 接続できない
```bash
# 接続確認
ping 172.30.0.2

# ポート確認
telnet 172.30.0.2 443
```

#### 2. HTTP/2接続失敗
```bash
# ローカル接続テスト
curl -k --http2 https://172.30.0.2/health

# Dockerクライアント接続テスト
docker exec grpc-client curl -k --http2 https://172.30.0.2/health
```

#### 3. HTTP/3接続失敗
```bash
# HTTP/3接続テスト
curl -k --http3 https://172.30.0.2/health
```

#### 4. ベンチマーク失敗
```bash
# ログ確認
tail -f logs/verification_*/h2_benchmark.log
tail -f logs/verification_*/h3_benchmark.log
```

### 診断コマンド

#### ネットワーク診断
```bash
# ネットワーク統計
docker exec grpc-client ss -tuln
docker exec grpc-router ss -tuln

# 接続テスト
docker exec grpc-client ping -c 5 172.30.0.2
```

#### サーバー診断
```bash
# サービス状態確認
ssh pi@172.30.0.2 'sudo systemctl status nginx'

# ポート確認
ssh pi@172.30.0.2 'sudo ss -tuln | grep :443'

# ログ確認
ssh pi@172.30.0.2 'sudo tail -f /var/log/nginx/access.log'
```

## 結果の解釈

### 成功の指標

#### 接続テスト
- **Ping**: 応答時間 < 100ms
- **Port 443**: 接続成功
- **SSL証明書**: 有効（自己署名でも可）

#### ベンチマーク
- **HTTP/2**: 成功率 100%
- **HTTP/3**: 成功率 100%（またはサポートなし）
- **スループット**: 環境に応じて適切な値

### パフォーマンス指標

#### レスポンス時間
- **良好**: < 100ms
- **許容範囲**: 100-500ms
- **要改善**: > 500ms

#### スループット
- **良好**: > 100 req/s
- **許容範囲**: 50-100 req/s
- **要改善**: < 50 req/s

## 次のステップ

### 1. 結果確認
```bash
# 最新の結果ディレクトリを確認
ls -la logs/

# 結果サマリーを確認
cat logs/verification_*/verification_summary.txt
cat logs/quick_benchmark_*/quick_benchmark_summary.txt
```

### 2. グラフ生成
```bash
# 本格ベンチマーク実行後、グラフが自動生成されます
ls -la logs/benchmark_raspberry_pi_*/*.png
```

### 3. 詳細分析
```bash
# ベンチマークスイートで詳細分析
./scripts/raspberry_pi_benchmark_suite.sh
```

## 注意事項

### セキュリティ
- 自己署名証明書を使用しているため、`--insecure`フラグが必要
- 本番環境では適切なSSL証明書を使用してください

### パフォーマンス
- 無線LAN環境では有線LANより性能が低下する可能性があります
- ネットワーク条件によって結果が大きく変動します

### リソース
- ベンチマーク実行中はRaspberry Pi 5のリソース使用量が高くなります
- 十分な冷却を確保してください

## サポート

問題が発生した場合は、以下の情報を収集してください：

1. **ログファイル**: `logs/` ディレクトリ内の関連ファイル
2. **システム情報**: `uname -a`, `docker version`
3. **ネットワーク情報**: `ip addr show`, `ss -tuln`
4. **エラーメッセージ**: 具体的なエラー内容

これらの情報とともに問題を報告してください。
