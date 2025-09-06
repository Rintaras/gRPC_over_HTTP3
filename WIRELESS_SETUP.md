# Raspberry Pi 5 無線LAN設定ガイド

## 概要

Raspberry Pi 5が無線LANで接続されている場合の設定手順と注意点を説明します。

## 無線LAN設定の特徴

### 1. ネットワークインターフェース
- **有線LAN**: `eth0`
- **無線LAN**: `wlan0`
- **設定ファイル**: `/etc/dhcpcd.conf`

### 2. 無線LAN特有の考慮事項
- **信号強度**: 無線信号の品質が性能に影響
- **干渉**: 他の無線デバイスとの干渉
- **セキュリティ**: WPA2/WPA3暗号化
- **安定性**: 有線LANより不安定な可能性

## 設定手順

### 1. 無線LAN接続の確認

```bash
# 無線インターフェースの確認
ip link show wlan0

# 無線接続状態の確認
iwconfig wlan0

# IPアドレスの確認
ip addr show wlan0
```

### 2. 固定IP設定

```bash
# 設定ファイルを編集
sudo nano /etc/dhcpcd.conf

# 以下を追加（無線LAN用）
interface wlan0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8
```

### 3. 設定の適用

```bash
# 設定を再読み込み
sudo systemctl restart dhcpcd

# または、システム再起動
sudo reboot
```

## 無線LAN特有の設定

### 1. 無線信号の最適化

```bash
# 無線信号強度の確認
iwconfig wlan0 | grep -E "(ESSID|Signal|Quality)"

# 無線チャンネルの確認
iwlist wlan0 channel

# 無線設定の確認
cat /etc/wpa_supplicant/wpa_supplicant.conf
```

### 2. パフォーマンス最適化

```bash
# 無線LANのパフォーマンス設定
sudo nano /etc/sysctl.conf

# 以下を追加
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
```

### 3. 無線LANの監視

```bash
# 無線LAN統計の確認
cat /proc/net/wireless

# 無線LAN接続の詳細
iwconfig wlan0

# 無線LANのログ
sudo journalctl -u wpa_supplicant
```

## トラブルシューティング

### 1. 接続できない場合

```bash
# 無線LANサービスの確認
sudo systemctl status wpa_supplicant

# 無線LANサービスの再起動
sudo systemctl restart wpa_supplicant

# 無線LANインターフェースの再起動
sudo ip link set wlan0 down
sudo ip link set wlan0 up
```

### 2. 信号強度が弱い場合

```bash
# 無線LAN設定の確認
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf

# 以下を追加（必要に応じて）
country=JP
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="your_wifi_name"
    psk="your_wifi_password"
    key_mgmt=WPA-PSK
    priority=1
}
```

### 3. パフォーマンスが悪い場合

```bash
# 無線LANのパワーマネジメントを無効化
sudo iwconfig wlan0 power off

# 無線LANの設定を確認
iwconfig wlan0

# 無線LANの再設定
sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
```

## ベンチマーク実行時の注意点

### 1. 無線LAN環境での考慮事項

- **信号強度**: 十分な信号強度を確保
- **干渉**: 他の無線デバイスとの干渉を最小化
- **距離**: アクセスポイントとの距離を適切に保つ
- **チャンネル**: 混雑していないチャンネルを使用

### 2. パフォーマンス測定の精度

- **有線LANとの比較**: 無線LANの特性を考慮
- **複数回測定**: 無線LANの不安定性を考慮
- **信号強度記録**: 測定時の信号強度を記録

### 3. ログ記録

```bash
# 無線LAN信号強度の記録
iwconfig wlan0 | grep -E "(ESSID|Signal|Quality)" >> /var/log/wireless_signal.log

# 無線LAN統計の記録
cat /proc/net/wireless >> /var/log/wireless_stats.log
```

## 設定例

### 1. 基本的な無線LAN設定

```bash
# /etc/dhcpcd.conf
interface wlan0
static ip_address=172.30.0.2/24
static routers=172.30.0.254
static domain_name_servers=8.8.8.8
```

### 2. 無線LAN最適化設定

```bash
# /etc/sysctl.conf
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
```

### 3. 無線LAN監視設定

```bash
# /usr/local/bin/monitor_wireless.sh
#!/bin/bash
echo "=== Wireless LAN Status ==="
iwconfig wlan0 | grep -E "(ESSID|Signal|Quality)"
cat /proc/net/wireless
```

## まとめ

無線LAN環境でのRaspberry Pi 5設定では、信号強度、干渉、セキュリティなどの要素を考慮する必要があります。適切な設定により、有線LANと同等の性能を発揮できる場合があります。
