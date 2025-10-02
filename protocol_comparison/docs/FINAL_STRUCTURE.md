# 最終プロジェクト構成

## 📁 ディレクトリ構造

```
protocol_comparison/
├── server/            サーバー実装
├── router/            ルーター実装  
├── client/            クライアント実装
├── certs/             SSL証明書 🔐
├── logs/              ベンチマーク結果 📊
│   └── YYYYMMDD_HHMMSS/
│       ├── benchmark_results.csv
│       ├── response_time_comparison.png
│       ├── stability_comparison.png
│       ├── benchmark_visualization.png
│       └── benchmark_analysis.png
└── venv/              Python環境
```

## 📄 ルートファイル（17個）

### スクリプト（5個）
1. benchmark_latency.sh       メインベンチマーク ⭐
2. generate_all_graphs.sh     グラフ再生成
3. view_latest_results.sh     最新結果確認
4. tc_setup.sh                tc設定
5. tc_reset.sh                tcリセット

### Python（3個）
1. visualize_response_time.py  応答速度グラフ
2. visualize_stability.py      安定性グラフ
3. visualize_results.py        総合グラフ

### Docker（3個）
1. docker-compose.router_tc.yml
2. Dockerfile.router_tc
3. Dockerfile.http3_test

### ドキュメント（6個）
1. README.md                   プロジェクト説明
2. QUICK_START.md              5分ガイド 🚀
3. README_GRAPHS.md            グラフガイド
4. BENCHMARK_ANALYSIS.md       分析結果
5. EXPERIMENT_CONDITIONS.md    実験条件
6. RESULTS.md                  結果サマリー

## 🎯 主要な改善

### 整理前
- ❌ 48個のファイルが散乱
- ❌ 証明書がルートに露出
- ❌ ログが上書きされる
- ❌ グラフがルートに散乱

### 整理後  
- ✅ 17個のファイルに集約（削除率65%）
- ✅ certs/に証明書を隔離
- ✅ logs/に結果を自動整理
- ✅ タイムスタンプで履歴管理

## 🚀 ワークフロー

```bash
# 1. 実験実行
./benchmark_latency.sh

# 2. 結果確認
./view_latest_results.sh

# 完了！
```

## 📊 出力先

すべての実験結果は`logs/タイムスタンプ/`に保存：
- CSV生データ
- 4つのグラフ（自動生成）
- 統計サマリー

過去の実験も保持されるため、比較が容易です！
