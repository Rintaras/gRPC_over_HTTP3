#!/bin/bash

echo "=== ChromeをHTTP/3モードで起動 ==="

killall "Google Chrome" 2>/dev/null
sleep 1

echo "Chromeを起動中..."

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --quic-version=h3-29 \
  --origin-to-force-quic-on=http3test.local:8443 \
  --ignore-certificate-errors-spki-list=l+jq5Bk6aUQgBaYfw6r+CfrJvjwNPDa6FVIccqK9FrY= \
  --user-data-dir=/tmp/chrome-http3-$(date +%s) \
  https://http3test.local:8443 &

echo ""
echo "✅ HTTP/3モードで起動完了！"
echo ""
echo "使用されているドメイン: http3test.local"
echo ""
echo "使用されているフラグ:"
echo "  --quic-version=h3-29: HTTP/3バージョン29を使用"
echo "  --origin-to-force-quic-on=http3test.local:8443: このオリジンでQUICを強制"
echo "  --ignore-certificate-errors-spki-list: 証明書のSPKIハッシュで信頼"
echo ""
echo "サーバーログを監視するには:"
echo "  docker logs http3-server -f"
echo ""
echo "✨ Chromeの開発者ツール（F12）で Protocol 列を確認してください"
echo "   h3 と表示されていればHTTP/3接続成功です！"
