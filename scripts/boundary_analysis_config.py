#!/usr/bin/env python3
"""
HTTP/2 vs HTTP/3 Performance Boundary Analysis Configuration
性能境界値分析のための詳細なテスト設定
"""

# 基本テストパラメータ
BASE_PARAMS = {
    'requests': 10000,
    'connections': 50,
    'threads': 10,
    'warmup_requests': 2000,
    'measurement_requests': 8000,
    'warmup_time': 5
}

# 遅延テスト範囲（ms）
DELAY_RANGE = {
    'fine_grain': list(range(0, 51, 2)),      # 0-50ms (2ms刻み)
    'medium_grain': list(range(50, 201, 5)),  # 50-200ms (5ms刻み) 
    'coarse_grain': list(range(200, 501, 10)) # 200-500ms (10ms刻み)
}

# パケット損失率テスト範囲（%）
LOSS_RANGE = {
    'low_loss': [0.0, 0.1, 0.2, 0.5, 1.0],           # 低損失
    'medium_loss': [1.0, 2.0, 3.0, 4.0, 5.0],        # 中損失
    'high_loss': [5.0, 7.5, 10.0, 12.5, 15.0]        # 高損失
}

# 帯域制限テスト範囲（Mbps）
BANDWIDTH_RANGE = {
    'low_bandwidth': [0.5, 1.0, 2.0, 5.0, 10.0],     # 低帯域
    'medium_bandwidth': [10.0, 20.0, 50.0, 100.0],   # 中帯域
    'high_bandwidth': [100.0, 200.0, 500.0, 1000.0]  # 高帯域
}

# 境界値検出用の詳細テストケース
BOUNDARY_TEST_CASES = [
    # 低遅延環境での境界値検出
    {'delay_range': list(range(0, 21, 1)), 'loss': 0.0, 'bandwidth': 0},
    {'delay_range': list(range(0, 21, 1)), 'loss': 0.5, 'bandwidth': 0},
    {'delay_range': list(range(0, 21, 1)), 'loss': 1.0, 'bandwidth': 0},
    
    # 中遅延環境での境界値検出
    {'delay_range': list(range(20, 101, 2)), 'loss': 0.0, 'bandwidth': 0},
    {'delay_range': list(range(20, 101, 2)), 'loss': 1.0, 'bandwidth': 0},
    {'delay_range': list(range(20, 101, 2)), 'loss': 2.0, 'bandwidth': 0},
    
    # 高遅延環境での境界値検出
    {'delay_range': list(range(100, 301, 5)), 'loss': 0.0, 'bandwidth': 0},
    {'delay_range': list(range(100, 301, 5)), 'loss': 2.0, 'bandwidth': 0},
    {'delay_range': list(range(100, 301, 5)), 'loss': 5.0, 'bandwidth': 0},
    
    # 帯域制限環境での境界値検出
    {'delay': 50, 'loss': 1.0, 'bandwidth_range': [1, 2, 5, 10, 20, 50, 100]},
    {'delay': 100, 'loss': 2.0, 'bandwidth_range': [1, 2, 5, 10, 20, 50, 100]},
    {'delay': 150, 'loss': 3.0, 'bandwidth_range': [1, 2, 5, 10, 20, 50, 100]},
]

# 分析対象メトリクス
ANALYSIS_METRICS = [
    'throughput',           # スループット (req/s)
    'latency_mean',         # 平均レイテンシ (ms)
    'latency_p50',          # 50%ile レイテンシ (ms)
    'latency_p90',          # 90%ile レイテンシ (ms)
    'latency_p99',          # 99%ile レイテンシ (ms)
    'connect_time_mean',    # 平均接続時間 (ms)
    'ttfb_mean',           # 平均初回バイト時間 (ms)
    'error_rate',          # エラー率 (%)
    'timeout_rate'         # タイムアウト率 (%)
]

# 境界値判定基準
BOUNDARY_CRITERIA = {
    'throughput_threshold': 0.05,      # 5%以上の差で境界値とする
    'latency_threshold': 0.10,         # 10%以上の差で境界値とする
    'significance_level': 0.05,        # 統計的有意性の閾値
    'min_samples': 3,                  # 最小サンプル数
    'confidence_interval': 0.95       # 信頼区間
}

# 出力設定
OUTPUT_CONFIG = {
    'csv_output': True,
    'json_output': True,
    'graph_output': True,
    'detailed_log': True,
    'boundary_report': True
} 