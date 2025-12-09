"""
Ping 服務管理器（後台執行，不阻塞主流程）
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import threading
from utils.logger import get_logger
from config.constants import DeviceStatus

logger = get_logger(__name__)


class PingService:
    """Ping 服務管理器（異步執行）"""
    
    def __init__(self, session_state, adb_manager):
        self.session_state = session_state
        self.adb_manager = adb_manager
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="ping")
        # 使用線程安全的字典存儲結果（避免在後台線程中訪問 Streamlit context）
        self._results_lock = threading.Lock()
        self._results: Dict[str, Dict[str, Any]] = {}
        self._futures: Dict[str, Future] = {}
    
    def submit_ping_tasks(
        self,
        devices: List[Any],
        network_config: Dict[str, Any],
        retry_manager: Optional[Any]
    ):
        """
        提交 Ping 任務到後台執行（非阻塞）
        
        Args:
            devices: 需要 Ping 的設備列表
            network_config: 網路監控配置
            retry_manager: 重試管理器
        """
        if not devices:
            return
        
        logger.debug(f"📡 提交 {len(devices)} 台設備的 Ping 任務（後台執行）")
        
        for device in devices:
            device_id = device.device_id
            
            # 檢查是否已有正在執行的任務（使用線程安全的字典）
            with self._results_lock:
                if device_id in self._futures:
                    future = self._futures[device_id]
                    if not future.done():
                        # 任務還在執行中，跳過
                        continue
            
            # 提交新的 Ping 任務
            future = self.executor.submit(
                self._ping_device_task,
                device, network_config, retry_manager
            )
            
            # 存儲到線程安全的字典
            with self._results_lock:
                self._futures[device_id] = future
    
    def _ping_device_task(
        self,
        device: Any,
        network_config: Dict[str, Any],
        retry_manager: Optional[Any]
    ):
        """
        執行 Ping 操作（在後台線程中執行）
        
        Returns:
            (device_id, new_status, message, ping_time)
        """
        try:
            new_status, message, ping_time = self.adb_manager.check_and_auto_connect_device(
                device, network_config, retry_manager
            )
            
            # 保存結果到線程安全的字典（避免在後台線程中訪問 Streamlit context）
            device_id = device.device_id
            with self._results_lock:
                self._results[device_id] = {
                    'status': new_status,
                    'message': message,
                    'ping_time': ping_time,
                    'timestamp': datetime.now(),
                    'device_id': device_id
                }
            
            logger.debug(f"📡 Ping 完成: {device.display_name} -> {new_status} ({ping_time:.1f}ms)" if ping_time else f"📡 Ping 完成: {device.display_name} -> {new_status}")
            
            return device.device_id, new_status, message, ping_time
            
        except Exception as e:
            logger.error(f"📡 Ping 任務失敗: {device.device_id} - {e}")
            return device.device_id, None, None, None
    
    def check_and_apply_results(
        self,
        devices: List[Any],
        retry_manager: Optional[Any] = None
    ) -> List[Any]:
        """
        檢查並應用已完成的 Ping 結果（非阻塞檢查）
        
        Returns:
            更新了狀態的設備列表
        """
        updated_devices = []
        completed_futures = []
        
        # 檢查所有設備的 Ping 結果（從線程安全的字典讀取）
        with self._results_lock:
            for device in devices:
                device_id = device.device_id
                processed = False
                
                # 優先檢查是否有完成的任務（最新的結果）
                if device_id in self._futures:
                    future = self._futures[device_id]
                    
                    if future.done():
                        # 任務已完成，處理結果
                        try:
                            _, new_status, message, ping_time = future.result(timeout=0.1)
                            
                            # 應用結果
                            if new_status and new_status != device.status:
                                old_status = device.status
                                device.status = new_status
                                logger.info(f"🔄 設備狀態變更: {device.display_name} {old_status} → {new_status} ({message})")
                                
                                if new_status == DeviceStatus.ONLINE and retry_manager:
                                    retry_manager.reset_retry_count(device_id)
                                
                                updated_devices.append(device)
                                processed = True
                            
                            if ping_time is not None:
                                device.ping_ms = ping_time
                                if device not in updated_devices:
                                    updated_devices.append(device)
                            
                        except Exception as e:
                            logger.error(f"處理 Ping 結果失敗: {device_id} - {e}")
                        
                        completed_futures.append(device_id)
                
                # 如果沒有完成的 future，檢查緩存的結果
                if not processed and device_id in self._results:
                    result = self._results[device_id]
                    
                    timestamp = result.get('timestamp')
                    if timestamp:
                        if isinstance(timestamp, str):
                            timestamp = datetime.fromisoformat(timestamp)
                        
                        age = (datetime.now() - timestamp).total_seconds()
                        if age < 30:
                            new_status = result.get('status')
                            ping_time = result.get('ping_time')
                            
                            if new_status and new_status != device.status:
                                device.status = new_status
                                if device not in updated_devices:
                                    updated_devices.append(device)
                            
                            if ping_time is not None:
                                device.ping_ms = ping_time
                                if device not in updated_devices:
                                    updated_devices.append(device)
            
            # 清理已完成的任務
            for device_id in completed_futures:
                self._futures.pop(device_id, None)
        
        return updated_devices
    
    def cleanup_old_results(self, max_age_seconds: int = 60):
        """清理過期的 Ping 結果"""
        current_time = datetime.now()
        keys_to_remove = []
        
        with self._results_lock:
            for device_id, result in list(self._results.items()):
                timestamp = result.get('timestamp')
                if timestamp:
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp)
                    age = (current_time - timestamp).total_seconds()
                    if age > max_age_seconds:
                        keys_to_remove.append(device_id)
            
            for device_id in keys_to_remove:
                self._results.pop(device_id, None)
                logger.debug(f"清理過期的 Ping 結果: {device_id}")
    
    def shutdown(self, wait: bool = True, timeout: Optional[float] = None):
        """
        關閉 Ping 服務並清理資源
        
        Args:
            wait: 是否等待所有任務完成
            timeout: 等待超時時間（秒）
        """
        logger.info("正在關閉 Ping 服務...")
        
        # 關閉 executor
        self.executor.shutdown(wait=wait, timeout=timeout)
        
        # 清理數據
        with self._results_lock:
            self._results.clear()
            self._futures.clear()
        
        logger.info("Ping 服務已關閉")

