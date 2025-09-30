# HTTP/3 サーバー

このプロジェクトは、Dockerを使用してHTTP/3サーバーをローカルに構築し、Google ChromeからHTTP/3でアクセスできる環境を提供します。

## 技術スタック

- **Go 1.21**: プログラミング言語
- **quic-go v0.40.1**: HTTP/3実装ライブラリ
- **Docker**: コンテナ化
- **Docker Compose**: コンテナオーケストレーション
- **OpenSSL**: SSL証明書生成
- **Alpine Linux**: 軽量なベースイメージ

## 機能

- HTTP/3プロトコルでの通信
- TLS暗号化
- Dockerコンテナでの実行
- ローカル開発環境でのテスト

## ファイル構成

```
.
├── main.go              # HTTP/3サーバーのメインコード
├── go.mod               # Go依存関係管理
├── Dockerfile           # Dockerイメージ定義
├── docker-compose.yml   # Docker Compose設定
├── fullchain1.pem       # SSL証明書
├── privkey1.pem         # SSL秘密鍵
└── README.md            # このファイル
```

## セットアップ

1. リポジトリをクローン
2. DockerとDocker Composeがインストールされていることを確認
3. 以下のコマンドでサーバーを起動:

```bash
docker-compose up --build -d
```

## アクセス方法

### HTTP/1.1 / HTTP/2でアクセス

通常のChromeで以下のURLにアクセス:

```
https://localhost:8443
```

### HTTP/3でアクセス

HTTP/3プロトコルを使用するには、専用のスクリプトでChromeを起動:

```bash
./start_chrome_http3.sh
```

または、直接コマンドで起動:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --quic-version=h3-29 \
  --origin-to-force-quic-on=0.0.0.0:8443 \
  --ignore-certificate-errors-spki-list=tPefRj8ElIAExLRxhQD02miu1TJntrxz7eifF3+XgGo= \
  https://localhost:8443
```

このスクリプトは以下のフラグでChromeを起動します:
- `--quic-version=h3-29`: HTTP/3バージョン29を使用
- `--origin-to-force-quic-on=0.0.0.0:8443`: 0.0.0.0:8443でQUICを強制
- `--ignore-certificate-errors-spki-list`: 証明書のSPKIハッシュで信頼

**確認方法**: 開発者ツール（F12）のNetworkタブでProtocol列を確認。`h3`と表示されればHTTP/3接続成功！

## サーバー管理

### 起動
```bash
docker-compose up -d
```

### 停止
```bash
docker-compose down
```

### ログ確認
```bash
docker logs http3-server
```

### 再ビルド
```bash
docker-compose up --build -d
```

## 技術詳細

### HTTP/3について
HTTP/3は、QUICプロトコルを基盤とした次世代HTTPプロトコルです。主な特徴:
- UDPベースの通信
- マルチプレクシング
- 0-RTT接続確立
- パケットロス耐性

### quic-goライブラリ
- Go言語でQUICプロトコルを実装
- HTTP/3サポート
- 高パフォーマンス
- アクティブにメンテナンスされている

### Docker設定
- マルチステージビルドで軽量化
- UDP/TCP両方のポートを公開
- システムカーネルパラメータを最適化

## トラブルシューティング

### UDPバッファサイズの警告
サーバー起動時にUDPバッファサイズの警告が表示される場合があります。これは動作には影響しませんが、パフォーマンス向上のためにシステム設定を調整できます。

### 証明書エラー
自己署名証明書を使用しているため、ブラウザで警告が表示されます。開発環境では問題ありませんが、本番環境では適切な証明書を使用してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
