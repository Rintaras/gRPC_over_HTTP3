package common

import (
	"log"
	"runtime"
	"syscall"
	"time"
)

// ResourceManager リソース管理構造体
type ResourceManager struct {
	MaxProcs int
	Priority int
}

// NewResourceManager 新しいリソースマネージャーを作成
func NewResourceManager() *ResourceManager {
	return &ResourceManager{
		MaxProcs: runtime.NumCPU(),
		Priority: -10, // 高優先度
	}
}

// FixResources リソースを固定化
func (rm *ResourceManager) FixResources() error {
	log.Println("リソース固定化を開始...")

	// 1. GOMAXPROCSを固定
	runtime.GOMAXPROCS(rm.MaxProcs)
	log.Printf("GOMAXPROCSを%dに固定", rm.MaxProcs)

	// 2. プロセス優先度を設定
	if err := rm.setProcessPriority(); err != nil {
		log.Printf("プロセス優先度設定エラー: %v", err)
	}

	// 3. メモリ使用量を最適化
	rm.optimizeMemory()

	// 4. ガベージコレクションを実行
	runtime.GC()
	log.Println("ガベージコレクションを実行")

	// 5. システムリソース状態をログ出力
	rm.logResourceStatus()

	log.Println("リソース固定化完了")
	return nil
}

// setProcessPriority プロセス優先度を設定
func (rm *ResourceManager) setProcessPriority() error {
	// Unix系システムでのみ動作
	if runtime.GOOS == "linux" || runtime.GOOS == "darwin" {
		// プロセス優先度を設定
		err := syscall.Setpriority(syscall.PRIO_PROCESS, 0, rm.Priority)
		if err != nil {
			return err
		}
		log.Printf("プロセス優先度を%dに設定", rm.Priority)
	}
	return nil
}

// optimizeMemory メモリ使用量を最適化
func (rm *ResourceManager) optimizeMemory() {
	// メモリ使用量を制限
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	log.Printf("メモリ使用量: %d KB", m.Alloc/1024)
	log.Printf("システムメモリ: %d KB", m.Sys/1024)

	// メモリ使用量が大きい場合はガベージコレクションを実行
	if m.Alloc > 100*1024*1024 { // 100MB以上
		runtime.GC()
		log.Println("メモリ使用量が大きいため、ガベージコレクションを実行")
	}
}

// logResourceStatus リソース状態をログ出力
func (rm *ResourceManager) logResourceStatus() {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	log.Println("=== リソース状態 ===")
	log.Printf("GOMAXPROCS: %d", runtime.GOMAXPROCS(0))
	log.Printf("Goroutine数: %d", runtime.NumGoroutine())
	log.Printf("メモリ使用量: %d KB", m.Alloc/1024)
	log.Printf("システムメモリ: %d KB", m.Sys/1024)
	log.Printf("ガベージコレクション回数: %d", m.NumGC)
	log.Println("==================")
}

// SetMaxProcs 最大プロセス数を設定
func (rm *ResourceManager) SetMaxProcs(maxProcs int) {
	rm.MaxProcs = maxProcs
	runtime.GOMAXPROCS(maxProcs)
	log.Printf("GOMAXPROCSを%dに変更", maxProcs)
}

// SetPriority プロセス優先度を設定
func (rm *ResourceManager) SetPriority(priority int) {
	rm.Priority = priority
	if err := rm.setProcessPriority(); err != nil {
		log.Printf("プロセス優先度設定エラー: %v", err)
	}
}

// MonitorResources リソース監視を開始
func (rm *ResourceManager) MonitorResources(interval time.Duration) {
	ticker := time.NewTicker(interval)
	go func() {
		for range ticker.C {
			rm.logResourceStatus()
		}
	}()
}

// CleanupResources リソースクリーンアップ
func (rm *ResourceManager) CleanupResources() {
	log.Println("リソースクリーンアップを実行...")

	// ガベージコレクションを実行
	runtime.GC()

	// 最終的なリソース状態をログ出力
	rm.logResourceStatus()

	log.Println("リソースクリーンアップ完了")
}
