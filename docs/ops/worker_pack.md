# HONGSTR Worker Pack (macOS-only)

> **Operations / Compute Expansion**
> 本指南說明如何部署額外的 macOS 運算節點 (Worker) 來分流研究與回測運算。

---

## 1. Worker Role (運算節點定位)

Worker 的唯一職責是提供額外的運算資源（Research / Backtest Compute Expansion）。

- **支援的情境**: 多維度策略池掃描、多方向 (Direction) 模擬、多重 Regime Slicing 分析。
- **限制**: Worker 節點被嚴格限制為 **`report_only`**。它不可參與主引擎的實盤交易或行情聚合。

## 2. Data Flow & Connectivity

Worker 與 主機 (Mac mini) 之間的數據與連線限制如下：

### Connectivity (連線規範)

- **網路環境**: Worker 可以位於任何外部網路 (Different Network OK)。
- **VPN 穿透**: 推薦使用 **Tailscale**，或利用 WireGuard 組件建立安全連線。
- **身分驗證**: 節點間通訊一律使用受限的 SSH Key（非密碼），設定 Least Privilege User。

### Data Flow (數據流)

1. **Compute**: Worker 在本地端的 `data/backtests/` 生成非影響性的分析產物。
2. **Transfer**: 透過 `rsync` 或 `scp` 將運算結果 (例如 `summary.json`) 傳輸至 Main Host (Mac mini) 的特定收取目錄。
3. **Publish (SSOT)**: Main Host 透過定期的 `bash scripts/refresh_state.sh`，將收取的結果編寫成 SSOT 並發布至 `/daily` 報告。

## 3. Hard Constraints (安全紅線)

部署 Worker 必須嚴守以下紅線，確保核心系統的穩定性：

1. **No Git Push**: Worker 預設不可擁有上傳 (Push) 至主 repo 的權限。
2. **No Data Commits**: Worker 不得將任何 `data/**` 或 `reports/**` 目錄內的產出轉化為 Git 提交。所有產出檔案必須是在 `.gitignore` 規範內。
3. **No Exec in TG_CP**: Worker 若掛載 Telegram Control Plane 供遠端查詢狀態，該實例嚴禁使用任何 `subprocess`, `os.system` 或 `Popen` 執行非同步行為。

## 4. Security Checklist

部署前請由合夥人或系統維護者確認：

- [ ] Worker 採用獨立的 non-admin 帳戶運行系統任務。
- [ ] SSH Key 限制單一用途 (Restricted SSH Key)，並禁止 PTY allocation 若僅用作 rsync。
- [ ] Tailscale ACL 僅開放特定連接埠 22 給 Worker，禁止雙向隨意穿透。

## 5. Acceptance Criteria

啟動 Worker 後的驗收標準，請參考：

- **[Worker Acceptance Checklist (DoD)](worker_acceptance_checklist.md)**
