# 網路監控與自動連接功能評估報告

## 🎯 需求概述

1. **Ping 對象選擇**：針對未連接設備進行 Ping
2. **Network Config 設定頁**：可配置 Ping 的對象和自動連接選項
3. **自動連接功能**：設備未連接但 Ping 通時，自動嘗試連接（三次為限）
4. **新設備狀態**：設備開機但無法連線時，標記為「無法連線」（需要使用者開啟 WiFi ADB）

---

## ✅ 可行性評估

### 1. **技術可行性：✅ 完全可行**

所有需求都可以用現有技術實現：

| 功能 | 技術方案 | 可行性 | 難度 |
|------|----------|--------|------|
| Ping 未連接設備 | ICMP ping | ✅ 簡單 | 低 |
| 配置頁面 | Streamlit 頁面 | ✅ 簡單 | 低 |
| 自動連接 | 現有 `connect()` 方法 | ✅ 簡單 | 低 |
| 新狀態類型 | 擴展 `DeviceStatus` enum | ✅ 簡單 | 低 |
| 狀態判斷邏輯 | Ping + ADB connect 結果 | ✅ 中等 | 中 |

---

### 2. **架構可行性：✅ 完全可行**

現有架構支持所有需求：

- ✅ **設備狀態管理**：已有 `DeviceStatus` enum，可擴展
- ✅ **連接機制**：已有 `ADBManager.connect()` 方法
- ✅ **並發處理**：已有 `ThreadPoolExecutor` 批處理機制
- ✅ **配置管理**：已有 `get_user_config()` 和 `save_user_config()`
- ✅ **UI 框架**：已有 Streamlit 頁面結構

---

## 📋 詳細設計方案

### 1. **擴展設備狀態類型**

#### **新增狀態：`ADB_NOT_ENABLED`**

```python
# config/constants.py
class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    NOT_CONNECTED = "not_connected"
    ADB_NOT_ENABLED = "adb_not_enabled"  # 新增：WiFi ADB 未開啟
    BUSY = "busy"
    CONNECTING = "connecting"
    ERROR = "error"

# 狀態圖示
STATUS_ICONS = {
    DeviceStatus.ONLINE: "🟢",
    DeviceStatus.OFFLINE: "🟠",
    DeviceStatus.NOT_CONNECTED: "⚫",
    DeviceStatus.ADB_NOT_ENABLED: "🟡",  # 新增：黃色表示需要手動開啟
    # ...
}
```

**狀態邏輯**：
- `NOT_CONNECTED`：Ping 不通，設備可能關機或不在網路中
- `ADB_NOT_ENABLED`：Ping 通，但 ADB connect 失敗（WiFi ADB 未開啟）

---

### 2. **網路監控配置**

#### **配置結構**

```python
# config/settings.py
NETWORK_MONITORING_CONFIG: Dict[str, Any] = {
    "enabled": True,              # 是否啟用網路監控
    "ping_interval": 10,          # Ping 間隔（秒）
    "ping_timeout": 2,            # Ping 超時（秒）
    "auto_connect": True,         # 是否啟用自動連接
    "auto_connect_max_retries": 3,  # 自動連接最大重試次數
    "auto_connect_cooldown": 30,    # 失敗後冷卻時間（秒）
    "ping_targets": {              # Ping 目標配置
        "all_devices": True,        # Ping 所有設備
        "only_not_connected": True, # 僅 Ping 未連接設備
        "only_wifi_devices": True,  # 僅 Ping WiFi 設備
    }
}
```

---

### 3. **Ping 功能實作**

#### **核心方法**

```python
# core/adb_manager.py
class ADBManager:
    def ping_device(self, ip: str, timeout: int = 2) -> Optional[float]:
        """
        Ping 設備並返回響應時間（毫秒）
        
        Returns:
            None: Ping 失敗或超時
            float: Ping 響應時間（毫秒）
        """
        import subprocess
        import re
        
        try:
            # 檢測系統類型
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), ip]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 1
            )
            
            if result.returncode == 0:
                # 解析響應時間
                output = result.stdout
                if is_windows:
                    # Windows: "時間<1ms" 或 "時間=10ms"
                    match = re.search(r'時間[<=](\d+)ms', output)
                else:
                    # macOS/Linux: "time=10.123 ms" 或 "time<1.000 ms"
                    match = re.search(r'time[<=]([\d.]+)\s*ms', output)
                
                if match:
                    return float(match.group(1))
            
            return None
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Ping 失敗: {ip} - {e}")
            return None
    
    def ping_devices_batch(
        self,
        devices: List[Device],
        max_workers: int = 10
    ) -> Dict[str, Optional[float]]:
        """
        並發 Ping 多個設備
        
        Returns:
            {device_id: ping_time_ms or None}
        """
        results = {}
        
        if not devices:
            return results
        
        def ping_device_wrapper(device: Device):
            if not device.ip:
                return device.device_id, None
            ping_time = self.ping_device(device.ip)
            return device.device_id, ping_time
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(ping_device_wrapper, device): device
                for device in devices
            }
            
            for future in as_completed(futures):
                try:
                    device_id, ping_time = future.result()
                    results[device_id] = ping_time
                except Exception as e:
                    device = futures[future]
                    logger.error(f"Ping 設備異常: {device.device_id} - {e}")
                    results[device.device_id] = None
        
        return results
```

---

### 4. **自動連接邏輯**

#### **狀態判斷流程**

```python
# core/adb_manager.py
def check_and_auto_connect_device(
    self,
    device: Device,
    config: Dict[str, Any]
) -> Tuple[DeviceStatus, Optional[str]]:
    """
    檢查設備狀態並自動連接（如果需要）
    
    Returns:
        (new_status, message)
    """
    from config.constants import DeviceStatus
    
    # 1. 檢查是否需要 Ping（根據配置）
    ping_targets = config.get('ping_targets', {})
    should_ping = False
    
    if device.status == DeviceStatus.NOT_CONNECTED:
        should_ping = ping_targets.get('only_not_connected', True)
    elif ping_targets.get('all_devices', False):
        should_ping = True
    
    if not should_ping or not device.ip:
        return device.status, None
    
    # 2. Ping 設備
    ping_time = self.ping_device(device.ip, timeout=config.get('ping_timeout', 2))
    
    if ping_time is None:
        # Ping 不通：設備可能關機或不在網路中
        return DeviceStatus.NOT_CONNECTED, "設備無響應"
    
    # 3. Ping 通，檢查 ADB 連接狀態
    adb_devices = self.get_devices()
    connection_str = device.connection_string
    
    # 檢查是否已在 ADB 列表中
    for adb_device in adb_devices:
        if adb_device['serial'] == connection_str:
            if adb_device['state'] == 'device':
                return DeviceStatus.ONLINE, "設備已連接"
            elif adb_device['state'] == 'offline':
                return DeviceStatus.OFFLINE, "設備離線"
    
    # 4. 不在 ADB 列表中，但 Ping 通：嘗試自動連接
    auto_connect = config.get('auto_connect', False)
    
    if not auto_connect:
        # 未啟用自動連接，標記為需要手動連接
        return DeviceStatus.NOT_CONNECTED, f"設備在線（Ping: {ping_time:.1f}ms），但未連接"
    
    # 5. 檢查重試次數和冷卻時間
    retry_key = f'auto_connect_retries_{device.device_id}'
    cooldown_key = f'auto_connect_cooldown_{device.device_id}'
    
    # 從 session state 或配置中獲取重試記錄
    # （這裡需要實現重試記錄機制）
    
    # 6. 嘗試連接
    max_retries = config.get('auto_connect_max_retries', 3)
    retries = self._get_retry_count(device.device_id)
    
    if retries >= max_retries:
        # 超過最大重試次數，標記為需要手動介入
        return DeviceStatus.ADB_NOT_ENABLED, f"自動連接失敗（已重試 {retries} 次），請手動開啟 WiFi ADB"
    
    # 7. 執行連接
    success, output = self.connect(device.ip, device.port)
    
    if success or "already connected" in output.lower():
        # 連接成功
        self._reset_retry_count(device.device_id)
        return DeviceStatus.ONLINE, "自動連接成功"
    
    # 8. 連接失敗
    # 判斷失敗原因
    if "cannot connect" in output.lower() or "connection refused" in output.lower():
        # ADB 連接被拒絕：WiFi ADB 未開啟
        self._increment_retry_count(device.device_id)
        return DeviceStatus.ADB_NOT_ENABLED, f"無法連接：WiFi ADB 未開啟（Ping: {ping_time:.1f}ms）"
    else:
        # 其他錯誤
        self._increment_retry_count(device.device_id)
        return DeviceStatus.NOT_CONNECTED, f"連接失敗：{output}"
```

---

### 5. **重試記錄機制**

#### **方案 A：使用 Session State（推薦）**

```python
# 適合 Streamlit 應用
class AutoConnectManager:
    """自動連接重試管理器"""
    
    def __init__(self, session_state):
        self.session_state = session_state
        self.retry_prefix = 'auto_connect_retries_'
        self.cooldown_prefix = 'auto_connect_cooldown_'
    
    def get_retry_count(self, device_id: str) -> int:
        key = f'{self.retry_prefix}{device_id}'
        return self.session_state.get(key, 0)
    
    def increment_retry_count(self, device_id: str):
        key = f'{self.retry_prefix}{device_id}'
        self.session_state[key] = self.session_state.get(key, 0) + 1
    
    def reset_retry_count(self, device_id: str):
        key = f'{self.retry_prefix}{device_id}'
        if key in self.session_state:
            del self.session_state[key]
    
    def is_in_cooldown(self, device_id: str, cooldown_seconds: int) -> bool:
        key = f'{self.cooldown_prefix}{device_id}'
        last_attempt = self.session_state.get(key)
        
        if last_attempt is None:
            return False
        
        time_since = (datetime.now() - last_attempt).total_seconds()
        return time_since < cooldown_seconds
    
    def set_cooldown(self, device_id: str):
        key = f'{self.cooldown_prefix}{device_id}'
        self.session_state[key] = datetime.now()
```

#### **方案 B：使用資料庫持久化**

```python
# 如果需要在重啟後保留重試記錄
# 在 device_registry.json 中儲存重試記錄
```

---

### 6. **Network Config 設定頁**

#### **頁面結構**

```python
# pages/5_🌐_網路設定.py (新增)
"""
網路監控設定頁面
"""
import streamlit as st
from config.settings import get_user_config, save_user_config

def main():
    st.title("🌐 網路設定")
    
    user_config = get_user_config()
    network_config = user_config.get('network_monitoring', {})
    
    # 基本設定
    st.subheader("📡 網路監控")
    
    enabled = st.checkbox(
        "啟用網路監控",
        value=network_config.get('enabled', True),
        help="啟用後系統會定期 Ping 設備以監控網路狀況"
    )
    
    ping_interval = st.slider(
        "Ping 間隔（秒）",
        min_value=5,
        max_value=60,
        value=network_config.get('ping_interval', 10),
        help="每隔多少秒 Ping 一次設備"
    )
    
    ping_timeout = st.slider(
        "Ping 超時（秒）",
        min_value=1,
        max_value=5,
        value=network_config.get('ping_timeout', 2),
        help="Ping 請求的超時時間"
    )
    
    st.markdown("---")
    
    # Ping 目標設定
    st.subheader("🎯 Ping 目標")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ping_all = st.checkbox(
            "Ping 所有設備",
            value=network_config.get('ping_targets', {}).get('all_devices', False),
            help="對所有設備進行 Ping（包括已連接的設備）"
        )
        
        ping_not_connected = st.checkbox(
            "僅 Ping 未連接設備",
            value=network_config.get('ping_targets', {}).get('only_not_connected', True),
            help="僅對未連接的設備進行 Ping"
        )
    
    with col2:
        ping_wifi_only = st.checkbox(
            "僅 Ping WiFi 設備",
            value=network_config.get('ping_targets', {}).get('only_wifi_devices', True),
            help="僅對 WiFi 連接的設備進行 Ping（USB 設備不需要 Ping）"
        )
    
    st.markdown("---")
    
    # 自動連接設定
    st.subheader("🔄 自動連接")
    
    auto_connect = st.checkbox(
        "啟用自動連接",
        value=network_config.get('auto_connect', True),
        help="當設備 Ping 通但未連接時，自動嘗試連接"
    )
    
    if auto_connect:
        max_retries = st.number_input(
            "最大重試次數",
            min_value=1,
            max_value=10,
            value=network_config.get('auto_connect_max_retries', 3),
            help="自動連接失敗後的最大重試次數"
        )
        
        cooldown = st.number_input(
            "失敗後冷卻時間（秒）",
            min_value=10,
            max_value=300,
            value=network_config.get('auto_connect_cooldown', 30),
            help="連接失敗後等待多少秒再重試"
        )
    else:
        max_retries = network_config.get('auto_connect_max_retries', 3)
        cooldown = network_config.get('auto_connect_cooldown', 30)
    
    # 保存按鈕
    st.markdown("---")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("💾 保存設定", type="primary", use_container_width=True):
            network_config = {
                'enabled': enabled,
                'ping_interval': ping_interval,
                'ping_timeout': ping_timeout,
                'auto_connect': auto_connect,
                'auto_connect_max_retries': max_retries,
                'auto_connect_cooldown': cooldown,
                'ping_targets': {
                    'all_devices': ping_all,
                    'only_not_connected': ping_not_connected,
                    'only_wifi_devices': ping_wifi_only,
                }
            }
            
            user_config['network_monitoring'] = network_config
            
            if save_user_config(user_config):
                st.success("✅ 設定已保存")
            else:
                st.error("❌ 保存失敗")
    
    # 說明
    st.markdown("---")
    with st.expander("ℹ️ 使用說明"):
        st.markdown("""
        ### 網路監控功能說明
        
        1. **Ping 監控**
           - 系統會定期 Ping 設備的 IP 地址
           - 記錄響應時間來評估網路品質
           - 只有 WiFi 連接的設備需要 Ping
        
        2. **自動連接**
           - 當設備 Ping 通但未連接時，自動嘗試連接
           - 如果連接失敗，會重試指定次數
           - 超過重試次數後，標記為「需要手動介入」
        
        3. **設備狀態**
           - **在線**：已連接並可用
           - **離線**：已連接但狀態異常
           - **未連接**：Ping 不通，設備可能關機
           - **無法連線**：Ping 通但無法連接（WiFi ADB 未開啟）
        """)
```

---

### 7. **整合到現有狀態檢查流程**

#### **修改設備狀態同步邏輯**

```python
# pages/1_📱_設備管理.py
def sync_device_status_with_ping(devices: List[Device]):
    """同步設備狀態（包含 Ping 檢查）"""
    from config.settings import get_user_config
    
    user_config = get_user_config()
    network_config = user_config.get('network_monitoring', {})
    
    if not network_config.get('enabled', False):
        # 未啟用網路監控，使用原有邏輯
        return sync_device_status_original(devices)
    
    # 過濾需要 Ping 的設備
    ping_targets = network_config.get('ping_targets', {})
    devices_to_ping = []
    
    for device in devices:
        should_ping = False
        
        # 根據配置決定是否需要 Ping
        if device.status == DeviceStatus.NOT_CONNECTED:
            should_ping = ping_targets.get('only_not_connected', True)
        elif ping_targets.get('all_devices', False):
            should_ping = True
        
        # 僅 Ping WiFi 設備
        if should_ping and device.connection_type == ConnectionType.WIFI and device.ip:
            devices_to_ping.append(device)
    
    # 並發 Ping
    if devices_to_ping:
        ping_results = st.session_state.adb_manager.ping_devices_batch(devices_to_ping)
        
        # 根據 Ping 結果更新狀態
        for device in devices_to_ping:
            ping_time = ping_results.get(device.device_id)
            
            if ping_time is not None:
                # Ping 通，檢查是否需要自動連接
                new_status, message = st.session_state.adb_manager.check_and_auto_connect_device(
                    device,
                    network_config
                )
                
                if new_status != device.status:
                    device.status = new_status
                    # 更新資料庫...
            else:
                # Ping 不通，確認未連接狀態
                if device.status != DeviceStatus.NOT_CONNECTED:
                    device.status = DeviceStatus.NOT_CONNECTED
                    # 更新資料庫...
```

---

## 🔧 實作步驟

### **Phase 1：基礎功能（1-2 小時）**

1. ✅ 擴展 `DeviceStatus` enum，新增 `ADB_NOT_ENABLED`
2. ✅ 實作 `ping_device()` 方法
3. ✅ 實作 `ping_devices_batch()` 方法
4. ✅ 添加網路監控配置到 `settings.py`

### **Phase 2：自動連接邏輯（2-3 小時）**

5. ✅ 實作 `check_and_auto_connect_device()` 方法
6. ✅ 實作重試記錄機制（`AutoConnectManager`）
7. ✅ 整合到現有狀態同步流程

### **Phase 3：UI 和配置（2-3 小時）**

8. ✅ 創建「網路設定」頁面
9. ✅ 在設備卡片中顯示新狀態
10. ✅ 添加狀態說明和提示

### **Phase 4：測試和優化（1-2 小時）**

11. ✅ 測試不同場景（Ping 通/不通、連接成功/失敗）
12. ✅ 優化重試邏輯和冷卻機制
13. ✅ 性能測試（多設備並發）

---

## ⚠️ 注意事項和限制

### **1. Streamlit 單線程限制**

- **問題**：Streamlit 是單線程，背景 Ping 需要整合到現有刷新機制
- **解決**：在頁面刷新時執行 Ping（每 3-10 秒），而不是獨立背景線程

### **2. 權限問題**

- **問題**：某些系統可能需要 root 權限才能 Ping
- **解決**：使用 Python 的 `subprocess` 調用系統 `ping` 命令，大部分系統無需特殊權限

### **3. 跨平台兼容性**

- **問題**：不同系統的 `ping` 命令格式不同
- **解決**：檢測系統類型，使用對應的命令格式（Windows/macOS/Linux）

### **4. 網路負擔**

- **問題**：頻繁 Ping 可能造成網路負擔
- **解決**：
  - 僅 Ping 未連接設備（默認）
  - 合理的 Ping 間隔（10 秒）
  - 並發限制（max_workers=10）

### **5. 自動連接的誤判**

- **問題**：Ping 通但無法連接可能是其他原因（防火牆、端口改變等）
- **解決**：
  - 明確的錯誤訊息
  - 重試機制避免頻繁嘗試
  - 提供手動連接選項

---

## 📊 預期效果

### **優點**

1. ✅ **自動化**：減少手動連接操作
2. ✅ **狀態清晰**：明確區分「未連接」和「無法連線」
3. ✅ **網路監控**：了解設備網路狀況
4. ✅ **用戶體驗**：自動處理常見情況

### **缺點**

1. ⚠️ **增加複雜度**：需要維護重試記錄和狀態邏輯
2. ⚠️ **可能誤判**：無法連接的原因可能不是 WiFi ADB 未開啟
3. ⚠️ **資源消耗**：額外的 Ping 操作（但負擔很小）

---

## ✅ 總結

### **可行性：✅ 完全可行**

所有功能都可以用現有技術實現，技術難度中等。

### **建議實作順序**

1. **第一階段**：基礎 Ping 功能 + 新狀態類型
2. **第二階段**：自動連接邏輯
3. **第三階段**：配置頁面和完善 UI

### **預估工作量**

- **總計**：6-10 小時
- **代碼量**：約 500-800 行
- **測試**：需要測試多種場景

### **風險評估**

- **技術風險**：低
- **性能風險**：低（負擔很小）
- **維護風險**：中等（需要維護狀態邏輯）

---

## 📝 後續改進

1. **智能頻率調整**：根據設備狀態動態調整 Ping 頻率
2. **網路品質評估**：基於響應時間和丟包率評估網路品質
3. **歷史記錄**：記錄 Ping 歷史和連接嘗試歷史
4. **通知功能**：當設備自動連接成功時發送通知



