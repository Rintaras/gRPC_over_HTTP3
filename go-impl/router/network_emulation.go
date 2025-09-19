package main

import (
	"fmt"
	"log"
	"os/exec"
	"strconv"
)

type NetworkEmulation struct {
	Delay     int // ms
	Loss      int // percentage
	Bandwidth int // Mbps (0 = unlimited)
}

func (ne *NetworkEmulation) Apply() error {
	// 既存のルールをクリア
	if err := ne.Clear(); err != nil {
		log.Printf("Warning: Failed to clear existing rules: %v", err)
	}

	// パラメータを構築
	var args []string
	args = append(args, "tc", "qdisc", "add", "dev", "eth0", "root", "netem")

	// 遅延設定（0msでも設定）
	if ne.Delay >= 0 {
		args = append(args, "delay", strconv.Itoa(ne.Delay)+"ms")
	}

	// 損失設定（0%の場合は設定しない）
	if ne.Loss > 0 {
		args = append(args, "loss", strconv.Itoa(ne.Loss)+"%")
	}

	// 帯域制限設定（0の場合は設定しない）
	if ne.Bandwidth > 0 {
		args = append(args, "rate", strconv.Itoa(ne.Bandwidth)+"mbit")
	}

	// 全てのパラメータが0の場合はnoqueueを使用
	if ne.Delay == 0 && ne.Loss == 0 && ne.Bandwidth == 0 {
		args = []string{"tc", "qdisc", "add", "dev", "eth0", "root", "noqueue"}
	}

	cmd := exec.Command(args[0], args[1:]...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to apply network emulation: %v, output: %s", err, string(output))
	}

	log.Printf("Applied network emulation: delay=%dms, loss=%d%%, bandwidth=%dMbps", ne.Delay, ne.Loss, ne.Bandwidth)
	return nil
}

func (ne *NetworkEmulation) Clear() error {
	// 既存のルールを削除
	cmd := exec.Command("tc", "qdisc", "del", "dev", "eth0", "root")
	output, err := cmd.CombinedOutput()
	if err != nil {
		// ルールが存在しない場合は正常
		log.Printf("No existing rules to clear: %s", string(output))
		return nil
	}

	log.Println("Cleared existing network emulation rules")
	return nil
}

func (ne *NetworkEmulation) GetStatus() (int, int, int, error) {
	// 現在のネットワーク設定を取得
	cmd := exec.Command("tc", "qdisc", "show", "dev", "eth0")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return 0, 0, 0, fmt.Errorf("failed to get network status: %v", err)
	}

	// 出力から遅延、損失、帯域を解析
	// 実際の実装では、より詳細な解析が必要
	log.Printf("Current network status: %s", string(output))
	return ne.Delay, ne.Loss, ne.Bandwidth, nil
}

func (ne *NetworkEmulation) SetDelay(delay int) error {
	ne.Delay = delay
	return ne.Apply()
}

func (ne *NetworkEmulation) SetLoss(loss int) error {
	ne.Loss = loss
	return ne.Apply()
}

func (ne *NetworkEmulation) SetBandwidth(bandwidth int) error {
	ne.Bandwidth = bandwidth
	return ne.Apply()
}

func (ne *NetworkEmulation) SetConditions(delay, loss int) error {
	ne.Delay = delay
	ne.Loss = loss
	return ne.Apply()
}

func (ne *NetworkEmulation) SetAllConditions(delay, loss, bandwidth int) error {
	ne.Delay = delay
	ne.Loss = loss
	ne.Bandwidth = bandwidth
	return ne.Apply()
}
