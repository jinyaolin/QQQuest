# 重新連線功能修復

## 🐛 問題描述

用戶反饋：點擊「重新連線」按鈕後，設備沒有重新上線。

## 🔍 問題分析

### 原本的代碼：

```python
if st.button("🔌 重新連線", ...):
    if device.ip:
        success, output = st.session_state.adb_manager.connect(device.ip, device.port)
        if success or "already connected" in output.lower():
            st.success("已重新連線")
            device.status = DeviceStatus.ONLINE
            device.last_seen = datetime.now()
            st.session_state.device_registry.save_device(device)
            st.rerun()
```

### 問題點：

1. ❌ **缺少日誌記錄**：無法診斷連線失敗的原因
2. ❌ **缺少錯誤提示**：連線失敗時用戶不知道發生了什麼
3. ❌ **缺少 IP 檢查提示**：沒有 IP 時沒有提示
4. ❌ **缺少延遲**：立即 rerun 可能導致狀態未更新

---

## ✅ 修復內容

### 1. **增強重新連線邏輯**

```python
if st.button("🔌 重新連線", key=f"reconnect_{device.device_id}", use_container_width=True):
    if device.ip:
        # 添加日誌記錄
        logger.info(f"🔄 嘗試重新連線: {device.display_name} ({device.ip}:{device.port})")
        success, output = st.session_state.adb_manager.connect(device.ip, device.port)
        logger.info(f"🔄 連線結果: success={success}, output={output}")
        
        if success or "already connected" in output.lower():
            # 成功提示更詳細
            st.success(f"✅ 已重新連線：{device.ip}:{device.port}")
            device.status = DeviceStatus.ONLINE
            device.last_seen = datetime.now()
            st.session_state.device_registry.save_device(device)
            logger.info(f"✅ 設備 {device.display_name} 已標記為在線")
            # 添加延遲確保狀態更新
            time.sleep(0.5)
            st.rerun()
        else:
            # 添加錯誤提示
            st.error(f"❌ 連線失敗：{output}")
            logger.error(f"❌ 重新連線失敗: {device.display_name} - {output}")
    else:
        # 添加 IP 缺失提示
        st.warning("⚠️ 設備沒有 IP 地址，無法重新連線")
        logger.warning(f"⚠️ 設備 {device.display_name} 沒有 IP 地址")
```

### 2. **同步增強中斷連線邏輯**

```python
if st.button("🔌 中斷連線", key=f"disconnect_{device.device_id}", use_container_width=True):
    logger.info(f"🔌 嘗試中斷連線: {device.display_name} ({device.connection_string})")
    success, output = st.session_state.adb_manager.disconnect(device.connection_string)
    logger.info(f"🔌 中斷結果: success={success}, output={output}")
    
    if success:
        st.success(f"✅ 已中斷連線：{device.connection_string}")
        device.status = DeviceStatus.OFFLINE
        st.session_state.device_registry.save_device(device)
        logger.info(f"✅ 設備 {device.display_name} 已標記為離線")
        time.sleep(0.5)
        st.rerun()
    else:
        st.error(f"❌ 中斷連線失敗：{output}")
        logger.error(f"❌ 中斷連線失敗: {device.display_name} - {output}")
```

### 3. **添加 `time` 模組導入**

```python
import time
```

---

## 🧪 測試方法

### 方法 1：使用測試腳本

```bash
cd /Users/jinyaolin/QQquest
source venv/bin/activate
python test_reconnect.py
```

這個腳本會：
- 列出所有設備
- 嘗試連線到每台設備
- 顯示詳細的連線結果
- 驗證設備是否真的在 `adb devices` 中

### 方法 2：在 UI 中測試

1. **重新啟動應用**：
   ```bash
   ./run.sh
   ```

2. **測試重新連線**：
   - 找到一台離線的設備
   - 點擊設備卡片右上角的「⋮」
   - 點擊「🔌 重新連線」
   - 觀察提示訊息：
     - ✅ 成功：「✅ 已重新連線：192.168.1.100:5555」
     - ❌ 失敗：「❌ 連線失敗：[錯誤訊息]」
     - ⚠️ 無 IP：「⚠️ 設備沒有 IP 地址，無法重新連線」

3. **查看日誌**：
   ```bash
   tail -f logs/qqquest_2025-12-01.log | grep -E "重新連線|連線結果"
   ```

   應該看到：
   ```
   🔄 嘗試重新連線: Q02 (192.168.1.100:5555)
   🔄 連線結果: success=True, output=connected to 192.168.1.100:5555
   ✅ 設備 Q02 已標記為在線
   ```

---

## 🔧 可能的連線失敗原因

### 1. **設備 IP 錯誤或已改變**
- **症狀**：`connection refused` 或 `cannot connect`
- **解決**：
  - 在 Quest 中確認 IP 地址（設定 → WiFi → 查看 IP）
  - 編輯設備資料，更新正確的 IP

### 2. **設備未啟用 ADB 調試**
- **症狀**：`connection refused`
- **解決**：
  - 在 Quest 中啟用開發者模式
  - 啟用 USB 調試

### 3. **設備與電腦不在同一網路**
- **症狀**：`connection timeout` 或 `no route to host`
- **解決**：
  - 確保 Quest 和電腦連接到同一個 WiFi

### 4. **ADB 服務未運行**
- **症狀**：`adb server is out of date` 或 `cannot connect to daemon`
- **解決**：
  ```bash
  adb kill-server
  adb start-server
  ```

### 5. **防火牆阻擋**
- **症狀**：`connection timeout`
- **解決**：
  - 關閉防火牆或允許 ADB 端口（5555）

---

## 📊 改進效果

| 項目 | 修改前 | 修改後 |
|------|--------|--------|
| 錯誤提示 | ❌ 無 | ✅ 詳細錯誤訊息 |
| 日誌記錄 | ❌ 無 | ✅ 完整日誌 |
| IP 檢查 | ❌ 無提示 | ✅ 警告提示 |
| 成功提示 | 🟡 簡單 | ✅ 詳細（含 IP） |
| 可診斷性 | 🔴 低 | 🟢 高 |

---

## 📝 相關文件

- `pages/1_📱_設備管理.py` - 設備管理頁面（已修復）
- `core/adb_manager.py` - ADB 管理器（connect/disconnect 方法）
- `test_reconnect.py` - 重新連線測試腳本

---

**狀態**：✅ 修復完成
**日期**：2025-12-01
**測試狀態**：待用戶測試

