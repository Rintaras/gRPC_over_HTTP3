import os
import re
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
from matplotlib.font_manager import FontProperties, findSystemFonts

# --- 日本語フォント自動検出 ---
def detect_japanese_font():
    candidates = [
        'Noto Sans CJK JP', 'Noto Serif CJK JP', 'IPAPGothic', 'IPA明朝', 'IPAMincho',
        'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'VL PGothic', 'DejaVu Sans'
    ]
    available = [os.path.basename(f) for f in findSystemFonts()]
    for font in candidates:
        for f in findSystemFonts():
            if font in f:
                return font
    return 'DejaVu Sans'

jp_font = FontProperties(family=detect_japanese_font())
matplotlib.rcParams['font.family'] = [detect_japanese_font()]
matplotlib.rcParams['axes.unicode_minus'] = False

# 区間名とファイル名の対応
sections = [
    ("クライアント→ルーター", "ping_client_to_router.txt", "ip_client_eth0.txt"),
    ("ルーター→サーバー", "ping_router_to_server.txt", "ip_router_eth0.txt"),
    ("サーバー→ルーター", "ping_server_to_router.txt", "ip_server_eth0.txt"),
    ("ルーター→クライアント", "ping_router_to_client.txt", "ip_client_eth0_after.txt"),
]

def parse_ping(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8', errors='ignore') as f:
        text = f.read()
    # 平均遅延（rttまたはround-trip両対応）
    m = re.search(r'(?:rtt|round-trip)[^=]*= [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+ ms', text)
    avg = float(m.group(1)) if m else None
    # パケットロス
    m2 = re.search(r'(\d+)% packet loss', text)
    loss = float(m2.group(1)) if m2 else None
    return avg, loss

def parse_ip_link(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    # TX:行を探し、その次の行から値を取得
    for i, line in enumerate(lines):
        if line.strip().startswith('TX:') and i+1 < len(lines):
            value_line = lines[i+1].strip()
            parts = value_line.split()
            # bytes packets errors dropped carrier collsns
            if len(parts) >= 6:
                tx_packets = int(parts[1])
                tx_errors = int(parts[2])
                tx_dropped = int(parts[3])
                return tx_packets, tx_errors, tx_dropped
    return None

def main(log_dir):
    ping_avgs, ping_losses, ip_packets, ip_errors, ip_drops = [], [], [], [], []
    section_labels = []
    for name, ping_file, ip_file in sections:
        ping = parse_ping(os.path.join(log_dir, ping_file))
        ipstat = parse_ip_link(os.path.join(log_dir, ip_file))
        section_labels.append(name)
        ping_avgs.append(ping[0] if ping else np.nan)
        ping_losses.append(ping[1] if ping else np.nan)
        ip_packets.append(ipstat[0] if ipstat else np.nan)
        ip_errors.append(ipstat[1] if ipstat else np.nan)
        ip_drops.append(ipstat[2] if ipstat else np.nan)

    def safe_val(val):
        return 0 if val is None or (isinstance(val, float) and np.isnan(val)) else val

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('ネットワーク4区間の統計可視化', fontsize=16, fontproperties=jp_font)

    # ping遅延
    axes[0,0].bar(section_labels, [safe_val(v) for v in ping_avgs], color='skyblue')
    axes[0,0].set_ylabel('平均遅延 (ms)', fontproperties=jp_font)
    axes[0,0].set_title('pingによる平均遅延', fontproperties=jp_font)
    for i, v in enumerate(ping_avgs):
        axes[0,0].text(i, safe_val(v), f'{v:.1f}' if v is not None and not np.isnan(v) else '-', ha='center', va='bottom', fontproperties=jp_font)

    # pingロス
    axes[0,1].bar(section_labels, [safe_val(v) for v in ping_losses], color='salmon')
    axes[0,1].set_ylabel('パケットロス率 (%)', fontproperties=jp_font)
    axes[0,1].set_title('pingによるパケットロス率', fontproperties=jp_font)
    for i, v in enumerate(ping_losses):
        axes[0,1].text(i, safe_val(v), f'{v:.1f}%' if v is not None and not np.isnan(v) else '-', ha='center', va='bottom', fontproperties=jp_font)

    # ipによる送信パケット数
    axes[1,0].bar(section_labels, [safe_val(v) for v in ip_packets], color='lightgreen')
    axes[1,0].set_ylabel('送信パケット数', fontproperties=jp_font)
    axes[1,0].set_title('ipによる送信パケット数', fontproperties=jp_font)
    for i, v in enumerate(ip_packets):
        axes[1,0].text(i, safe_val(v), f'{v}' if v is not None and not np.isnan(v) else '-', ha='center', va='bottom', fontproperties=jp_font)

    # ipによる送信エラー・ドロップ
    axes[1,1].bar(section_labels, [safe_val(v) for v in ip_drops], color='orange')
    axes[1,1].set_ylabel('送信ドロップ数', fontproperties=jp_font)
    axes[1,1].set_title('ipによる送信ドロップ数', fontproperties=jp_font)
    for i, v in enumerate(ip_drops):
        axes[1,1].text(i, safe_val(v), f'{v}' if v is not None and not np.isnan(v) else '-', ha='center', va='bottom', fontproperties=jp_font)

    plt.tight_layout(rect=[0,0,1,0.95])
    outpath = os.path.join(log_dir, 'network_section_stats.png')
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    plt.savefig(outpath, dpi=200)
    plt.close()
    print(f'可視化結果: {outpath}')

def plot_router_interfaces(log_dir):
    path = os.path.join(log_dir, 'ip_router_all.txt')
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    iface_names = []
    tx_packets = []
    tx_drops = []
    for i, line in enumerate(lines):
        m = re.match(r'\d+: ([^:]+):', line)
        if m:
            iface = m.group(1)
            # 次のTX:行を探す
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip().startswith('TX:') and j+1 < len(lines):
                    vals = lines[j+1].strip().split()
                    if len(vals) >= 6:
                        iface_names.append(iface)
                        tx_packets.append(int(vals[1]))
                        tx_drops.append(int(vals[3]))
                    break
    if iface_names:
        fig, ax1 = plt.subplots(figsize=(8,4))
        ax1.bar(iface_names, tx_packets, color='lightblue', label='送信パケット数')
        for i, v in enumerate(tx_packets):
            ax1.text(i, v, f'{v}', ha='center', va='bottom')
        ax1.set_ylabel('送信パケット数')
        ax1.set_title('ルーター全インターフェースの送信パケット数')
        plt.tight_layout()
        plt.savefig(os.path.join(log_dir, 'router_interfaces_packets.png'), dpi=200)
        plt.close()
        fig, ax2 = plt.subplots(figsize=(8,4))
        ax2.bar(iface_names, tx_drops, color='orange', label='送信ドロップ数')
        for i, v in enumerate(tx_drops):
            ax2.text(i, v, f'{v}', ha='center', va='bottom')
        ax2.set_ylabel('送信ドロップ数')
        ax2.set_title('ルーター全インターフェースの送信ドロップ数')
        plt.tight_layout()
        plt.savefig(os.path.join(log_dir, 'router_interfaces_drops.png'), dpi=200)
        plt.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python3 visualize_network_stats.py <log_dir>')
        exit(1)
    main(sys.argv[1])
    plot_router_interfaces(sys.argv[1]) 