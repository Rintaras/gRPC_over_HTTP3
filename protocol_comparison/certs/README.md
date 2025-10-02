# 証明書ディレクトリ

## 証明書の生成

このディレクトリにSSL/TLS証明書を配置します。

### mkcertを使用した証明書生成

```bash
# mkcertのインストール（初回のみ）
brew install mkcert
mkcert -install

# 証明書の生成
cd certs/
mkcert localhost 127.0.0.1 ::1

# 生成されるファイル
# - localhost+2.pem      証明書
# - localhost+2-key.pem  秘密鍵
```

## 必要なファイル

- `localhost+2.pem` - 公開鍵証明書
- `localhost+2-key.pem` - 秘密鍵

これらのファイルは`.gitignore`で除外されています（セキュリティのため）。

## 使用箇所

- **サーバー**: server/Dockerfile
- **ルーター**: Dockerfile.router_tc

両方のDockerイメージで使用されます。

