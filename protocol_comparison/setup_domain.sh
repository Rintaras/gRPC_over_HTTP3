#!/bin/bash

echo "=== HTTP/3用のローカルドメイン設定 ==="
echo ""
echo "ステップ1: hostsファイルにドメインを追加"
echo "以下のコマンドを実行してください（パスワードが必要）："
echo ""
echo "sudo sh -c 'echo \"127.0.0.1 http3test.local\" >> /etc/hosts'"
echo ""
echo "ステップ2: 確認"
echo "ping -c 1 http3test.local"
echo ""
echo "ステップ3: サーバーを再ビルドして起動"
echo "docker-compose down && docker-compose up --build -d"
echo ""
echo "ステップ4: ChromeをHTTP/3モードで起動"
echo "./start_chrome_http3.sh"
echo ""

