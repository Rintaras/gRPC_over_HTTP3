package main

import (
	"fmt"
	"log"
	"os/exec"
	"strconv"
)

type NetworkEmulation struct {
	Delay int // ms
	Loss  int // percentage
}

func (ne *NetworkEmulation) Apply() error {
	// 既存のルールをクリア
	if err := ne.Clear(); err != nil {
		log.Printf("Warning: Failed to clear existing rules: %v", err)
	}

	// tc netem ルールを適用
	cmd := exec.Command("tc", "qdisc", "add", "dev", "eth0", "root", "netem",
		"delay", strconv.Itoa(ne.Delay)+"ms",
		"loss", strconv.Itoa(ne.Loss)+"%")

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to apply network emulation: %v, output: %s", err, string(output))
	}

	log.Printf("Applied network emulation: delay=%dms, loss=%d%%", ne.Delay, ne.Loss)
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

func (ne *NetworkEmulation) GetStatus() (int, int, error) {
	// 現在のネットワーク設定を取得
	cmd := exec.Command("tc", "qdisc", "show", "dev", "eth0")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return 0, 0, fmt.Errorf("failed to get network status: %v", err)
	}

	// 出力から遅延と損失を解析
	// 実際の実装では、より詳細な解析が必要
	log.Printf("Current network status: %s", string(output))
	return ne.Delay, ne.Loss, nil
}

func (ne *NetworkEmulation) SetDelay(delay int) error {
	ne.Delay = delay
	return ne.Apply()
}

func (ne *NetworkEmulation) SetLoss(loss int) error {
	ne.Loss = loss
	return ne.Apply()
}

func (ne *NetworkEmulation) SetConditions(delay, loss int) error {
	ne.Delay = delay
	ne.Loss = loss
	return ne.Apply()
}
