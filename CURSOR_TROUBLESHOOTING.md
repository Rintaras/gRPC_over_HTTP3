# Cursor用 Raspberry Pi 5 サーバー構築 トラブルシューティングガイド

## よくある問題と解決方法

### 1. 接続できない問題

#### 問題: Raspberry Pi 5に接続できない
```
Raspberry Pi 5に接続できない問題を解決してください。

## 症状
- pingが通らない
- SSH接続できない
- ベンチマーククライアントから接続できない

## 診断手順
1. ネットワーク接続確認
2. IPアドレス確認
3. ファイアウォール確認
4. サービス状態確認

## 解決方法
1. ネットワーク設定修正
2. ファイアウォール設定修正
3. サービス再起動
4. 設定確認

各手順の詳細なコマンドを提示してください。
```

#### 問題: 特定のポートに接続できない
```
Raspberry Pi 5の特定のポート（443）に接続できない問題を解決してください。

## 症状
- ポート443に接続できない
- SSL証明書エラー
- HTTP/2/HTTP/3接続失敗

## 診断手順
1. ポート開放確認
2. サービス状態確認
3. SSL証明書確認
4. ログ確認

## 解決方法
1. ファイアウォール設定修正
2. サービス再起動
3. SSL証明書再生成
4. 設定修正

各手順の詳細なコマンドを提示してください。
```

### 2. SSL証明書問題

#### 問題: SSL証明書エラー
```
Raspberry Pi 5のSSL証明書エラーを解決してください。

## 症状
- 証明書検証エラー
- 接続拒否
- セキュリティ警告

## 診断手順
1. 証明書存在確認
2. 証明書有効性確認
3. 権限確認
4. 設定確認

## 解決方法
1. 証明書再生成
2. 権限修正
3. 設定修正
4. クライアント側設定

各手順の詳細なコマンドを提示してください。
```

### 3. HTTP/3動作問題

#### 問題: HTTP/3が動作しない
```
Raspberry Pi 5のHTTP/3が動作しない問題を解決してください。

## 症状
- HTTP/3接続失敗
- プロトコルフォールバック
- エラーログ出力

## 診断手順
1. Nginx設定確認
2. ビルド設定確認
3. 依存関係確認
4. ログ確認

## 解決方法
1. Nginx再ビルド
2. 設定修正
3. 依存関係インストール
4. 設定再読み込み

各手順の詳細なコマンドを提示してください。
```

### 4. パフォーマンス問題

#### 問題: パフォーマンスが悪い
```
Raspberry Pi 5サーバーのパフォーマンスが悪い問題を解決してください。

## 症状
- レスポンス時間が長い
- スループットが低い
- リソース使用量が高い

## 診断手順
1. システムリソース確認
2. ネットワーク設定確認
3. Nginx設定確認
4. ログ確認

## 解決方法
1. カーネルパラメータ調整
2. Nginx設定最適化
3. システム設定最適化
4. ハードウェア確認

各手順の詳細なコマンドを提示してください。
```

### 5. サービス起動問題

#### 問題: Nginxサービスが起動しない
```
Raspberry Pi 5のNginxサービスが起動しない問題を解決してください。

## 症状
- サービス起動失敗
- エラーメッセージ出力
- 設定エラー

## 診断手順
1. サービス状態確認
2. ログ確認
3. 設定ファイル確認
4. 依存関係確認

## 解決方法
1. 設定ファイル修正
2. 依存関係インストール
3. 権限修正
4. サービス再設定

各手順の詳細なコマンドを提示してください。
```

## 診断コマンド集

### 1. システム状態確認
```bash
# システム情報
uname -a
cat /etc/os-release

# リソース使用量
htop
free -h
df -h

# ネットワーク状態
ip addr show
ip route show
ss -tuln
```

### 2. サービス状態確認
```bash
# サービス状態
systemctl status nginx
systemctl is-active nginx
systemctl is-enabled nginx

# プロセス確認
ps aux | grep nginx
pgrep nginx
```

### 3. ネットワーク確認
```bash
# ポート確認
netstat -tuln | grep :443
ss -tuln | grep :443
lsof -i :443

# 接続テスト
telnet 172.30.0.2 443
nc -zv 172.30.0.2 443
```

### 4. SSL証明書確認
```bash
# 証明書確認
openssl x509 -in /etc/ssl/certs/grpc-server.crt -text -noout
openssl rsa -in /etc/ssl/private/grpc-server.key -check

# 証明書接続テスト
openssl s_client -connect 172.30.0.2:443 -servername grpc-server-pi.local
```

### 5. ログ確認
```bash
# Nginxログ
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# システムログ
journalctl -u nginx
journalctl -f
```

## 緊急時の対処法

### 1. サービス停止
```bash
# Nginx停止
sudo systemctl stop nginx
sudo pkill nginx
```

### 2. 設定リセット
```bash
# 設定バックアップ
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# デフォルト設定復元
sudo apt install --reinstall nginx
```

### 3. ネットワークリセット
```bash
# ネットワーク設定リセット
sudo systemctl restart dhcpcd
sudo systemctl restart networking
```

### 4. システム再起動
```bash
# システム再起動
sudo reboot
```

## 予防策

### 1. 定期的な監視
```bash
# 監視スクリプト実行
/usr/local/bin/monitor_raspberry_pi.sh

# ログ確認
tail -f /var/log/nginx/access.log
```

### 2. 設定バックアップ
```bash
# 設定バックアップ
sudo tar -czf nginx_config_backup.tar.gz /etc/nginx/
sudo tar -czf ssl_cert_backup.tar.gz /etc/ssl/
```

### 3. ログローテーション
```bash
# ログローテーション設定確認
sudo logrotate -d /etc/logrotate.d/nginx
```

## 連絡先・サポート

### 1. ログ収集
```bash
# 問題発生時のログ収集
sudo journalctl -u nginx > nginx_error.log
sudo tail -100 /var/log/nginx/error.log > nginx_access_error.log
```

### 2. 設定確認
```bash
# 設定ファイル確認
sudo nginx -t
sudo nginx -T
```

### 3. システム情報収集
```bash
# システム情報収集
uname -a > system_info.log
ip addr show >> system_info.log
systemctl status nginx >> system_info.log
```

このトラブルシューティングガイドを使用して、Raspberry Pi 5サーバーの問題を効率的に解決してください。
