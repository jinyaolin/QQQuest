# 自動連接重試次數重置邏輯說明

## 📋 概述

當設備重新上線時，自動連接的重試次數應該被重置為 0，這樣下次斷線時才能重新開始計算重試次數。

## ✅ 重置重試次數的所有場景

### 1. **設備已在 ADB 列表中（自動檢測到已連接）**

**位置**：`core/adb_manager.py` - `check_and_auto_connect_device()` 方法

**場景**：
- Ping 通設備
- 檢查 ADB 設備列表
- 發現設備已在列表中且狀態為 `device`

**處理**：
```python
if adb_device['state'] == 'device':
    # 設備已連接，重置重試次數
    if retry_manager:
        retry_manager.reset_retry_count(device.device_id)
    return DeviceStatus.ONLINE, "設備已連接", ping_time
```

---

### 2. **自動連接成功**

**位置**：`core/adb_manager.py` - `check_and_auto_connect_device()` 方法

**場景**：
- Ping 通設備
- 設備不在 ADB 列表中
- 執行自動連接
- 連接成功

**處理**：
```python
if success or "already connected" in output.lower():
    if retry_manager:
        retry_manager.reset_retry_count(device.device_id)
    return DeviceStatus.ONLINE, "自動連接成功", ping_time
```

---

### 3. **設備狀態同步時檢測到上線**

**位置**：`pages/1_📱_設備管理.py` - 設備狀態同步邏輯

**場景**：
- 執行 `adb devices` 檢查
- 發現設備狀態從 `NOT_CONNECTED` 或 `ADB_NOT_ENABLED` 變為 `ONLINE`

**處理**：
```python
if device.status != DeviceStatus.ONLINE:
    device.status = DeviceStatus.ONLINE
    device.last_seen = datetime.now()
    
    # 設備重新上線，重置自動連接重試次數
    if 'auto_connect_manager' in st.session_state:
        st.session_state.auto_connect_manager.reset_retry_count(device.device_id)
```

---

### 4. **網路監控檢查時狀態變為 ONLINE**

**位置**：`pages/1_📱_設備管理.py` - 網路監控檢查邏輯

**場景**：
- 執行網路監控檢查（Ping + 自動連接）
- 設備狀態變為 `ONLINE`

**處理**：
```python
if new_status != device.status:
    device.status = new_status
    
    # 如果設備狀態變為 ONLINE，重置重試次數
    if new_status == DeviceStatus.ONLINE and retry_manager:
        retry_manager.reset_retry_count(device.device_id)
```

---

### 5. **手動重新連接成功**

**位置**：`pages/1_📱_設備管理.py` - 手動重新連接按鈕處理

**場景**：
- 用戶點擊「重新連線」按鈕
- 手動連接成功

**處理**：
```python
if success or "already connected" in output.lower():
    # 重置自動連接重試次數
    if 'auto_connect_manager' in st.session_state:
        st.session_state.auto_connect_manager.reset_retry_count(device.device_id)
```

---

### 6. **冷卻期結束後重置（準備重新嘗試）**

**位置**：`core/adb_manager.py` - `check_and_auto_connect_device()` 方法

**場景**：
- 重試次數已達上限（3 次）
- 冷卻期已結束
- 準備重新開始嘗試

**處理**：
```python
if retries >= max_retries:
    if retry_manager.is_in_cooldown(device.device_id, cooldown):
        # 還在冷卻期，不嘗試
        return DeviceStatus.ADB_NOT_ENABLED, "..."
    else:
        # 冷卻期結束，重置重試次數，重新開始
        retry_manager.reset_retry_count(device.device_id)
        retries = 0
```

---

## 🔄 重置邏輯流程圖

```
設備狀態檢查
    ↓
設備是否在 ADB 列表中？
    ├─ 是 → 重置重試次數 → 返回 ONLINE
    └─ 否 → Ping 設備
            ↓
        Ping 是否成功？
            ├─ 否 → 返回 NOT_CONNECTED（不重置）
            └─ 是 → 檢查重試次數
                    ↓
                是否達到上限？
                    ├─ 是 → 檢查冷卻期
                    │       ├─ 冷卻中 → 返回 ADB_NOT_ENABLED（不重置）
                    │       └─ 冷卻結束 → 重置重試次數 → 繼續嘗試
                    └─ 否 → 嘗試連接
                            ↓
                        連接是否成功？
                            ├─ 是 → 重置重試次數 → 返回 ONLINE
                            └─ 否 → 增加重試次數 → 返回 ADB_NOT_ENABLED
```

---

## 🎯 設計原則

### **重置時機**

✅ **應該重置的情況**：
1. 設備已連接（無論是自動還是手動）
2. 自動連接成功
3. 冷卻期結束，準備重新嘗試

❌ **不應該重置的情況**：
1. 連接失敗（應該累積重試次數）
2. Ping 失敗（設備可能關機）
3. 仍在冷卻期內

---

## 📝 總結

**重試次數會在以下情況被重置為 0**：

1. ✅ 設備已在 ADB 列表中（自動檢測到）
2. ✅ 自動連接成功
3. ✅ 設備狀態同步時檢測到上線
4. ✅ 網路監控檢查時狀態變為 ONLINE
5. ✅ 手動重新連接成功
6. ✅ 冷卻期結束後（準備重新嘗試）

這確保了每次設備重新上線後，重試計數都會被重置，下次斷線時可以重新開始計算重試次數。



