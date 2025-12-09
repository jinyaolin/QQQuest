# 網路狀況監控（Ping）評估報告

## 🎯 需求說明

在系統端針對所有設備每隔幾秒發送一個 ping，並記錄 ping 的 response time 來評估網路狀況。

## 📊 負擔評估

### 1. **資源消耗分析**

#### **CPU 負擔**
- **單次 Ping 成本**：約 0.1-1ms CPU 時間（ICMP ping 是輕量級操作）
- **並發處理**：使用現有的 `ThreadPoolExecutor`（max_workers=10）可有效並發
- **評估**：✅ **負擔極低**

#### **網路負擔**
- **單次 Ping 包大小**：約 32-64 bytes（ICMP echo request）
- **響應包大小**：約 32-64 bytes（ICMP echo reply）
- **總流量**：每個設備每次約 64-128 bytes
- **評估**：✅ **負擔極低**（即使 100 台設備，每次也只約 12.8 KB）

#### **記憶體負擔**
- **每次 Ping**：約 1-2 KB（Python socket 對象、結果記錄）
- **並發記憶體**：取決於並發數（max_workers=10 = 約 10-20 KB）
- **評估**：✅ **負擔極低**

#### **I/O 負擔（資料庫寫入）**
- **每次記錄**：需要寫入響應時間到資料庫
- **頻率控制**：可以與現有狀態更新機制整合
- **評估**：⚠️ **中等負擔**（取決於頻率和設備數量）

---

### 2. **不同場景下的負擔計算**

#### **場景 A：10 台設備，每 5 秒 Ping 一次**

| 項目 | 計算 | 結果 |
|------|------|------|
| 每秒 Ping 數 | 10 ÷ 5 | 2 次/秒 |
| CPU 使用率 | 2 × 0.5ms | < 0.1% |
| 網路流量 | 2 × 128 bytes | 256 bytes/秒 |
| 資料庫寫入 | 2 次/秒 | 可忽略 |

**評估**：✅ **負擔極小，完全可以接受**

---

#### **場景 B：50 台設備，每 3 秒 Ping 一次**

| 項目 | 計算 | 結果 |
|------|------|------|
| 每秒 Ping 數 | 50 ÷ 3 | ~16.7 次/秒 |
| CPU 使用率 | 16.7 × 0.5ms | ~0.8% |
| 網路流量 | 16.7 × 128 bytes | ~2.1 KB/秒 |
| 資料庫寫入 | 16.7 次/秒 | 中等 |

**評估**：✅ **負擔很小，完全可接受**

---

#### **場景 C：100 台設備，每 2 秒 Ping 一次**

| 項目 | 計算 | 結果 |
|------|------|------|
| 每秒 Ping 數 | 100 ÷ 2 | 50 次/秒 |
| CPU 使用率 | 50 × 0.5ms | ~2.5% |
| 網路流量 | 50 × 128 bytes | ~6.4 KB/秒 |
| 資料庫寫入 | 50 次/秒 | 較高 |

**評估**：⚠️ **負擔中等，需要優化資料庫寫入策略**

---

#### **場景 D：200 台設備，每 1 秒 Ping 一次**

| 項目 | 計算 | 結果 |
|------|------|------|
| 每秒 Ping 數 | 200 ÷ 1 | 200 次/秒 |
| CPU 使用率 | 200 × 0.5ms | ~10% |
| 網路流量 | 200 × 128 bytes | ~25.6 KB/秒 |
| 資料庫寫入 | 200 次/秒 | **很高** |

**評估**：❌ **負擔較大，不建議如此頻繁**

---

### 3. **與現有系統整合**

#### **現有架構優勢**

✅ **已有並發處理機制**
- 使用 `ThreadPoolExecutor(max_workers=10)` 進行並發
- 已實現批處理（`get_status_batch`）
- 可以復用現有架構

✅ **已有頻率控制機制**
- 現有狀態查詢有 10 秒緩存限制
- 可以與 ping 機制整合，避免重複查詢

✅ **已有資料庫寫入優化**
- 使用 TinyDB（輕量級 JSON 資料庫）
- 可以批量寫入減少 I/O

---

### 4. **優化建議**

#### **建議 1：智能頻率調整**

```python
# 根據設備狀態調整 Ping 頻率
- 在線設備：每 5 秒 Ping 一次
- 離線設備：每 30 秒 Ping 一次（嘗試重連）
- 未連接設備：每 60 秒 Ping 一次
```

**效果**：減少 50-80% 的不必要 Ping

---

#### **建議 2：批量資料庫寫入**

```python
# 收集多個結果後批量寫入，而不是每次立即寫入
- 每 10 秒或收集 20 個結果後批量寫入
- 使用異步寫入，不阻塞主流程
```

**效果**：減少資料庫 I/O 負擔 80-90%

---

#### **建議 3：響應時間閾值過濾**

```python
# 只在響應時間有明顯變化時記錄
- 記錄歷史平均響應時間
- 只在變化超過 10% 時寫入資料庫
```

**效果**：減少資料庫寫入 70-90%

---

#### **建議 4：使用現有並發機制**

```python
# 復用現有的批處理架構
def ping_devices_batch(
    devices: List[str],
    max_workers: int = 10
) -> Dict[str, float]:
    """並發 Ping 多個設備"""
    # 使用 ThreadPoolExecutor
    # 返回 {device_ip: response_time_ms}
```

**效果**：充分利用現有架構，無需額外開發

---

### 5. **實作建議**

#### **方案 A：輕量級實作（推薦）**

```python
# 整合到現有狀態查詢中
# 在 get_status_batch 中同時進行 Ping
def get_device_status_with_ping(self, device: str) -> Dict[str, Any]:
    status = self.get_device_status(device)
    ping_time = self.ping_device(device)
    status['ping_ms'] = ping_time
    status['network_quality'] = self._assess_network_quality(ping_time)
    return status
```

**優點**：
- ✅ 復用現有機制
- ✅ 頻率已受控（10 秒一次）
- ✅ 負擔極小

**缺點**：
- ⚠️ Ping 頻率受限於狀態查詢頻率

---

#### **方案 B：獨立 Ping 服務（進階）**

```python
# 獨立的背景 Ping 服務
class NetworkMonitor:
    def __init__(self):
        self.ping_interval = 5  # 秒
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    def start_monitoring(self, devices: List[str]):
        # 在背景線程中定期 Ping
        while True:
            self.ping_batch(devices)
            time.sleep(self.ping_interval)
```

**優點**：
- ✅ 獨立控制 Ping 頻率
- ✅ 不影響現有功能

**缺點**：
- ⚠️ 需要額外的背景線程
- ⚠️ 需要處理 Streamlit 的單線程限制

---

### 6. **結論與建議**

#### **✅ 結論：負擔很小，建議實作**

1. **資源消耗極低**
   - CPU、網路、記憶體負擔都可忽略
   - 即使 100 台設備，負擔也在可接受範圍內

2. **資料庫寫入是唯一需要關注的點**
   - 可以通過批量寫入、閾值過濾優化
   - 建議整合到現有狀態查詢中

3. **建議採用「方案 A：輕量級實作」**
   - 整合到現有的 `get_status_batch` 中
   - 復用現有的頻率控制機制（10 秒一次）
   - 負擔最小，實作最簡單

---

### 7. **實作步驟**

#### **步驟 1：實作 Ping 功能**

```python
import subprocess
import time

def ping_device(self, device_ip: str, timeout: int = 2) -> Optional[float]:
    """Ping 設備並返回響應時間（毫秒）"""
    try:
        # 使用系統 ping 命令
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), device_ip],
            capture_output=True,
            text=True,
            timeout=timeout + 1
        )
        
        if result.returncode == 0:
            # 解析響應時間（不同系統格式可能不同）
            # macOS/Linux: "time=10.123 ms"
            # Windows: "time=10ms" 或 "time<1ms"
            output = result.stdout
            # ... 解析邏輯 ...
            return ping_time_ms
        return None
    except Exception:
        return None
```

---

#### **步驟 2：整合到現有狀態查詢**

```python
def get_device_status(self, device: str) -> Dict[str, Any]:
    status = {
        # ... 現有狀態 ...
    }
    
    # 添加 Ping 結果（如果設備有 IP）
    if ':' in device:
        device_ip = device.split(':')[0]
        ping_time = self.ping_device(device_ip)
        if ping_time:
            status['ping_ms'] = ping_time
            status['network_quality'] = self._assess_network_quality(ping_time)
    
    return status
```

---

#### **步驟 3：優化資料庫寫入**

```python
# 在 Device 模型中添加網路狀態欄位
class Device(BaseModel):
    # ... 現有欄位 ...
    ping_ms: Optional[float] = None
    network_quality: Optional[str] = None  # "excellent", "good", "fair", "poor"
```

---

### 8. **效能基準測試建議**

實作後建議進行以下測試：

1. **10 台設備測試**：驗證基本功能
2. **50 台設備測試**：驗證並發處理
3. **100 台設備測試**：驗證系統負載
4. **長期運行測試**：驗證穩定性

---

### 9. **風險評估**

| 風險 | 可能性 | 影響 | 應對措施 |
|------|--------|------|----------|
| Ping 過於頻繁導致網路擁塞 | 低 | 中 | 使用頻率控制、批量處理 |
| 資料庫寫入過多導致效能下降 | 中 | 中 | 批量寫入、閾值過濾 |
| 某些設備不響應 Ping | 高 | 低 | 設置超時、錯誤處理 |
| 背景線程與 Streamlit 衝突 | 低 | 中 | 使用現有機制，避免背景線程 |

---

## 📝 總結

**結論**：為所有設備定期 Ping 並記錄響應時間的負擔**極小**，完全可以實作。

**建議**：
1. ✅ 整合到現有狀態查詢機制中（方案 A）
2. ✅ 復用現有的並發和頻率控制機制
3. ✅ 實作批量寫入和閾值過濾優化
4. ✅ 先小規模測試（10 台設備），再逐步擴大

**預期負擔**：
- 10-50 台設備：**幾乎無負擔**（< 1% CPU）
- 50-100 台設備：**負擔很小**（1-3% CPU）
- 100+ 台設備：**需要優化**（批量寫入、智能頻率）





