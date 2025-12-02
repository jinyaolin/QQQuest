# 重複設備 ID 問題修復總結

## 🐛 問題描述

**錯誤訊息**：
```
StreamlitDuplicateElementKey: There are multiple elements with the same `key='action_device_1764541839'`
```

**根本原因**：
設備 ID 使用時間戳生成（`device_id=f"device_{int(datetime.now().timestamp())}"`），在同一秒內創建多個設備時，會產生相同的 `device_id`，導致：
1. 資料庫中出現重複的設備記錄
2. Streamlit UI 渲染時，多個設備卡片使用相同的 button key
3. 導致 `StreamlitDuplicateElementKey` 錯誤

---

## ✅ 解決方案

### 1. **修改設備 ID 生成邏輯**

將時間戳改為 UUID（更唯一、更安全）：

**修改前**：
```python
device_id=f"device_{int(datetime.now().timestamp())}"
```

**修改後**：
```python
device_id=f"device_{uuid.uuid4().hex[:12]}"
```

**修改的檔案**：
- `pages/1_📱_設備管理.py`（第 151 行）
- `core/usb_monitor.py`（第 316 行）

### 2. **清理資料庫重複資料**

創建並運行 `cleanup_duplicates.py` 清理腳本：

**清理結果**：
```
📊 資料庫中有 3 筆設備資料
❌ 發現重複 serial: 2G97C5ZH4Z00CC (doc_id: 2)
❌ 發現重複 serial: 2G97C5ZH4Z00CC (doc_id: 3)
🗑️  移除重複設備 (2 筆)
✅ 清理完成！剩餘 1 台設備
```

### 3. **刪除舊的頁面檔案**

移除 `ui/pages/` 中的舊檔案（已遷移到 `pages/`）：
- `ui/pages/1_📱_設備管理.py`
- `ui/pages/2_🏠_房間管理.py`
- `ui/pages/3_⚡_動作管理.py`

---

## 🧪 測試

1. **啟動應用**：
   ```bash
   ./run.sh
   ```

2. **測試新增設備**：
   - 點擊「新增設備」
   - 輸入 IP 和 Port
   - 確認設備卡片正常顯示，無錯誤

3. **測試 USB 自動偵測**：
   - 插入 USB 設備
   - 確認對話框出現（3-6 秒後）
   - 設定設備代號並連接
   - 確認無重複 ID 錯誤

---

## 📊 影響範圍

### ✅ 已修復
- 設備 ID 唯一性保證（UUID）
- 資料庫重複資料清理
- Streamlit UI 渲染錯誤

### ✅ 附加優化
- 清理舊的重複頁面檔案
- 改進設備 ID 生成機制

---

## 🔄 未來建議

1. **資料庫遷移機制**：
   - 如果未來需要修改資料結構，應該建立遷移腳本
   - 版本化資料庫 schema

2. **設備 ID 驗證**：
   - 在 `Device` class 中添加 ID 唯一性驗證
   - 在保存前檢查 ID 是否已存在

3. **定期清理**：
   - 可以將 `cleanup_duplicates.py` 改為定期維護工具
   - 或在應用啟動時自動檢查並修復

---

## 📝 相關檔案

- `pages/1_📱_設備管理.py` - 主要設備管理 UI
- `core/usb_monitor.py` - USB 監控和設備創建
- `core/device_registry.py` - 設備資料庫管理
- `cleanup_duplicates.py` - 清理腳本（一次性使用）

---

**狀態**：✅ 已完成修復
**日期**：2025-12-01

