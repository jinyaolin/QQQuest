# 設備狀態查詢超時問題修復

## 🐛 問題描述

用戶報告日誌中出現大量錯誤：

```
ERROR | 命令超時: shell dumpsys battery | grep -E 'level:|temperature:|powered:' && ...
WARNING | 命令失敗: error: closed
WARNING | 命令失敗: adb: device offline
WARNING | 獲取設備狀態失敗: 192.168.50.201:5555
```

---

## 🔍 問題分析

### 1. **命令超時（Timeout）**

**原因**：
- `get_device_status()` 使用複雜的 shell 命令
- Quest 設備響應較慢（特別是在休眠或高負載時）
- 原本超時設置為 5 秒，不足以完成查詢

**影響**：
- 每 3 秒自動刷新時都會嘗試查詢
- 頻繁超時導致日誌泛濫
- 用戶體驗不佳（看到很多錯誤）

### 2. **設備連接不穩定**

**原因**：
- `error: closed` - ADB 連接被關閉
- `adb: device offline` - 設備離線或休眠
- WiFi ADB 連接本身就不如 USB 穩定

**影響**：
- 命令執行失敗
- 狀態資訊無法更新
- 重複嘗試導致更多錯誤

---

## ✅ 修復措施

### 1. **增加超時時間**

**修改文件**：`core/adb_manager.py`

```python
# 修改前
success, output = self.execute_shell_command(command, device, timeout=5)

# 修改後
success, output = self.execute_shell_command(command, device, timeout=15)
```

**原因**：Quest 設備需要更長的響應時間

---

### 2. **添加查詢頻率限制**

**修改文件**：`pages/1_📱_設備管理.py`

**新增緩存機制**：
```python
# 檢查上次更新時間，避免過於頻繁的查詢
if 'device_status_last_fetch' not in st.session_state:
    st.session_state.device_status_last_fetch = {}

last_fetch = st.session_state.device_status_last_fetch.get(device.device_id)
if last_fetch:
    time_since_fetch = (datetime.now() - last_fetch).total_seconds()
    # 如果上次查詢在 10 秒內，跳過
    should_update = time_since_fetch > 10
```

**效果**：
- 每個設備**最多 10 秒查詢一次**
- 即使頁面每 3 秒刷新，也不會頻繁查詢
- 大幅減少超時發生次數

---

### 3. **減少錯誤日誌泛濫**

**修改文件**：`pages/1_📱_設備管理.py`

```python
# 只在首次失敗時記錄警告，避免日誌泛濫
if not st.session_state.get(f'device_status_error_{device.device_id}'):
    logger.warning(f"⚠️ 獲取設備狀態失敗: {device.display_name} - {e}")
    st.session_state[f'device_status_error_{device.device_id}'] = True
else:
    logger.debug(f"⚠️ 獲取設備狀態失敗（跳過日誌）: {device.display_name}")
```

**效果**：
- 每個設備只記錄**首次錯誤**
- 重複錯誤僅記錄為 DEBUG 級別
- 日誌更清爽，易於閱讀

---

### 4. **更新配置默認值**

**修改文件**：`config/settings.py`

```python
# 修改前
ADB_CONNECTION_TIMEOUT = 10  # 連線超時（秒）

# 修改後
ADB_CONNECTION_TIMEOUT = 15  # 連線超時（秒）- Quest 設備響應較慢，需要更長時間
```

---

## 📊 修復前後對比

### **修復前**：

```
每 3 秒：
  → 查詢設備狀態（5秒超時）
  → 超時失敗 ❌
  → 記錄 ERROR 日誌
  → 3 秒後重複...
  
日誌：
ERROR | 命令超時 (每 3 秒一次)
WARNING | 獲取設備狀態失敗 (每 3 秒一次)
... 大量重複錯誤 ...
```

### **修復後**：

```
每 3 秒：
  → 檢查上次查詢時間
  → 如果 < 10 秒，跳過 ✅
  → 如果 > 10 秒，查詢（15秒超時）
  → 成功 ✅ 或失敗（僅首次記錄）
  
日誌：
DEBUG | 設備狀態更新成功 (每 10+ 秒一次)
WARNING | 獲取設備狀態失敗 (僅首次)
... 清爽 ...
```

---

## 🎯 改進效果

| 項目 | 修改前 | 修改後 |
|------|--------|--------|
| 超時時間 | 5 秒 | 15 秒 |
| 查詢頻率 | 每 3 秒 | 每 10+ 秒 |
| 錯誤日誌 | 每次都記錄 | 僅首次記錄 |
| 日誌數量 | 🔴 大量 | 🟢 適中 |
| 成功率 | 🔴 低（頻繁超時） | 🟢 高 |
| 性能影響 | 🟡 中等 | 🟢 低 |

---

## 🧪 測試建議

### 測試場景 1：設備在線且穩定

**預期結果**：
- ✅ 每 10 秒成功查詢一次
- ✅ 狀態正常更新（電量、溫度等）
- ✅ 日誌中僅有 DEBUG 級別的成功訊息

### 測試場景 2：設備連接不穩定

**預期結果**：
- ⚠️ 首次查詢失敗時記錄 WARNING
- ✅ 後續失敗僅記錄 DEBUG（不會泛濫）
- ✅ 設備恢復後能正常查詢

### 測試場景 3：設備休眠

**預期結果**：
- ⚠️ 查詢可能超時或失敗（正常）
- ✅ 不會頻繁重試
- ✅ 日誌不會泛濫

---

## 💡 使用建議

### 1. **監控日誌**

**正常日誌（每 10+ 秒）**：
```
DEBUG | 📊 Q02: 🔋85% 🌡️32.5°C ⚡充電中 👁️清醒
```

**異常日誌（僅首次）**：
```
WARNING | ⚠️ 獲取設備狀態失敗: Q02 - Command timeout
```

### 2. **設備連接穩定性**

如果經常看到超時：
- 檢查 WiFi 信號強度
- 確認設備未進入深度休眠
- 考慮使用 USB 連接（更穩定）

### 3. **調整查詢頻率**

如果需要更頻繁的更新，可修改：

```python
# pages/1_📱_設備管理.py
# 將 10 秒改為您需要的間隔（建議 ≥ 10 秒）
should_update = time_since_fetch > 10  # 改為 5, 15, 20 等
```

---

## 🔧 進階優化（可選）

### 選項 1：僅在對話框關閉時查詢

```python
# 僅在沒有對話框開啟時查詢狀態
if not has_dialog_open and should_update:
    # 查詢狀態...
```

### 選項 2：使用異步查詢

```python
# 使用線程池異步查詢，不阻塞 UI
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    future = executor.submit(adb_manager.get_device_status, device)
    # 不等待結果，下次刷新時使用
```

### 選項 3：降級策略

```python
# 如果連續失敗 N 次，降低查詢頻率
if failure_count > 3:
    query_interval = 30  # 從 10 秒延長到 30 秒
```

---

## 📄 相關文件

- `core/adb_manager.py` - ADB 命令執行和狀態查詢
- `pages/1_📱_設備管理.py` - UI 和狀態更新邏輯
- `config/settings.py` - 系統配置
- `DEVICE_STATUS_FEATURE.md` - 設備狀態功能說明

---

**狀態**：✅ 修復完成  
**測試狀態**：待用戶測試  
**預期效果**：大幅減少超時錯誤，日誌更清爽  
**日期**：2025-12-01

