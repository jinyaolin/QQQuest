# 🐛 除錯指南

## 目前狀況

**問題**：顯示「監控中 (1 台)」但設備列表是空的

## 詳細日誌已啟用

我已經在以下模組添加了詳細的日誌記錄：

### 1. USB 監控器 (`core/usb_monitor.py`)
- 🔍 掃描設備時的詳細資訊
- 🆕 發現新設備的完整流程
- 📋 檢查註冊表的結果
- 📢 UI 回調的觸發狀態

### 2. 設備管理頁面 (`pages/1_📱_設備管理.py`)
- 🎯 UI 回調被調用時的狀態
- ✅ Session State 更新記錄
- 📝 對話框顯示狀態
- 📋 資料庫設備載入記錄

### 3. 設備註冊表 (`core/device_registry.py`)
- 📂 資料庫讀取詳情
- 🔍 設備識別檢查
- 📋 設備列表載入狀態

---

## 即時除錯步驟

### 步驟 1：清除並重啟

```bash
cd /Users/jinyaolin/QQquest

# 1. 停止應用程式（Ctrl+C）

# 2. 清空日誌查看新的
echo "" > logs/qqquest_2025-11-30.log

# 3. 拔掉所有 USB 設備

# 4. 重新啟動
source venv/bin/activate
streamlit run app.py
```

### 步驟 2：開啟日誌監控

**開啟第二個終端視窗**：

```bash
cd /Users/jinyaolin/QQquest

# 即時監控日誌
tail -f logs/qqquest_2025-11-30.log | grep --line-buffered -E "🔍|🆕|📋|🎯|✅|❌|⚠️|INFO|WARNING|ERROR"
```

### 步驟 3：測試新設備偵測

1. **前往「設備管理」頁面**
   
   日誌應該顯示：
   ```
   🚀 初始化 USB 監控器...
   USB 監控器已初始化
   ✅ USB 監控器已啟動並開始掃描
   ```

2. **插入 USB Quest 設備**

   日誌應該顯示（關鍵流程）：
   ```
   🔍 處理新連接: 2G97C5ZH4Z00CC (usb)
   📋 檢查註冊表: 2G97C5ZH4Z00CC 未註冊
   🆕 2G97C5ZH4Z00CC 是新設備，觸發 UI 回調
   📢 調用 on_new_device 回調: 2G97C5ZH4Z00CC
   🎯 [UI回調] on_new_device 被調用: 2G97C5ZH4Z00CC
   ✅ [UI回調] Session State 已更新
   ```

3. **等待 3-6 秒**（頁面自動刷新）

   日誌應該顯示：
   ```
   檢查對話框狀態: add=False, new=True
   📝 顯示新設備對話框: 2G97C5ZH4Z00CC
   ```

### 步驟 4：檢查資料庫

```bash
# 檢查設備資料庫
cat data/devices.json

# 檢查註冊表
cat data/device_registry.json
```

---

## 頁面內建除錯資訊

現在「設備管理」頁面有一個**「🔧 除錯資訊」**展開選項（預設收合），顯示：

- 資料庫設備數量
- USB 監控器狀態
- 當前追蹤設備數
- 追蹤設備列表
- Session State 鍵值
- 待處理新設備
- 對話框狀態

**使用方法**：
1. 在「設備管理」頁面
2. 找到「🔧 除錯資訊」
3. 點擊展開
4. 查看詳細狀態

---

## 常見問題診斷

### 問題 1：監控器顯示 (1 台) 但列表是空的

**可能原因**：
1. 設備被偵測但沒有添加到資料庫
2. UI 回調沒有正確觸發
3. 對話框沒有顯示
4. Session State 沒有同步

**診斷步驟**：

```bash
# 1. 查看最新日誌
tail -100 logs/qqquest_2025-11-30.log | grep "new_device\|on_new_device\|對話框"

# 2. 檢查是否有 UI 回調記錄
grep "🎯 \[UI回調\]" logs/qqquest_2025-11-30.log

# 3. 檢查資料庫
cat data/devices.json
cat data/device_registry.json

# 4. 檢查 ADB
adb devices
```

**預期看到**：
- ✅ UI 回調被調用
- ✅ Session State 更新
- ✅ 對話框狀態為 True

**如果沒看到**：
→ 說明 Streamlit 的執行緒同步有問題

---

### 問題 2：對話框沒有出現

**檢查點**：

```bash
# 查看對話框相關日誌
grep "對話框\|show_new_device_dialog" logs/qqquest_2025-11-30.log | tail -20
```

**預期流程**：
1. `show_new_device_dialog` 被設為 `True`
2. 頁面刷新時檢查這個狀態
3. 如果為 `True`，顯示對話框

**如果對話框一直不出現**：
- 檢查「🔧 除錯資訊」中的 `show_new_device_dialog` 值
- 如果是 `True` 但沒顯示 → UI 渲染問題
- 如果是 `False` → Session State 沒有正確更新

---

### 問題 3：設備一直在 _current_devices 中循環

**症狀**：
- 日誌持續顯示「發現 1 台設備」
- 但沒有「發現新連接」訊息

**原因**：
- 設備已經在 `_current_devices` 集合中
- 不會再次觸發 `_handle_new_connection`

**解決**：
```bash
# 1. 拔掉 USB
# 2. 等待 5 秒
# 3. 重新插入
```

日誌應該顯示：
```
🔌 發現斷線設備: {'2G97C5ZH4Z00CC'}
📊 設備數量變化: 1 → 0
（等待幾秒）
🆕 發現新連接: 2G97C5ZH4Z00CC
```

---

## 完整測試腳本

```bash
#!/bin/bash
# 完整測試腳本

echo "🧪 開始完整測試..."

# 1. 清理環境
echo "1️⃣ 清理環境..."
cd /Users/jinyaolin/QQquest
rm -f data/devices.json data/device_registry.json
echo '{"_default": {}}' > data/devices.json
echo '{"_default": {}}' > data/device_registry.json

# 2. 斷開所有 ADB 連接
echo "2️⃣ 斷開所有 ADB 連接..."
adb disconnect

# 3. 清空日誌
echo "3️⃣ 清空日誌..."
echo "" > logs/qqquest_2025-11-30.log

# 4. 檢查 ADB
echo "4️⃣ 檢查 ADB..."
adb version

echo ""
echo "✅ 準備完成！"
echo ""
echo "接下來："
echo "  1. 啟動應用：streamlit run app.py"
echo "  2. 前往「設備管理」頁面"
echo "  3. 插入 USB Quest"
echo "  4. 監控日誌：tail -f logs/qqquest_2025-11-30.log"
```

保存為 `test_setup.sh` 並執行：
```bash
chmod +x test_setup.sh
./test_setup.sh
```

---

## 日誌關鍵字說明

### Emoji 標記

- 🔍 = 掃描和檢查
- 🆕 = 新設備發現
- 📋 = 資料庫操作
- 🎯 = UI 回調觸發
- ✅ = 成功操作
- ❌ = 失敗錯誤
- ⚠️ = 警告
- 📢 = 通知觸發
- 🔌 = 連接/斷線
- 📊 = 狀態變化
- 📝 = UI 渲染

### 搜尋範例

```bash
# 查看所有重要事件
grep -E "🔍|🆕|📋|🎯|✅|❌" logs/qqquest_2025-11-30.log

# 只看新設備處理
grep "🆕\|new_device" logs/qqquest_2025-11-30.log

# 只看 UI 回調
grep "🎯" logs/qqquest_2025-11-30.log

# 只看錯誤
grep "❌\|ERROR" logs/qqquest_2025-11-30.log
```

---

## 下一步

1. **重新啟動應用**並查看新日誌
2. **測試 USB 插入**並監控日誌輸出
3. **查看「🔧 除錯資訊」**了解內部狀態
4. **提供日誌片段**如果還有問題

---

**詳細日誌現在已啟用！重新啟動應用後會看到完整的流程追蹤。** 🎯

