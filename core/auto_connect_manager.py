"""
自動連接重試管理器
"""
from datetime import datetime
from typing import Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class AutoConnectManager:
    """自動連接重試管理器"""
    
    def __init__(self, session_state):
        self.session_state = session_state
        self.retry_prefix = 'auto_connect_retries_'
        self.cooldown_prefix = 'auto_connect_cooldown_'
    
    def get_retry_count(self, device_id: str) -> int:
        """獲取重試次數"""
        key = f'{self.retry_prefix}{device_id}'
        return self.session_state.get(key, 0)
    
    def increment_retry_count(self, device_id: str):
        """增加重試次數"""
        key = f'{self.retry_prefix}{device_id}'
        self.session_state[key] = self.session_state.get(key, 0) + 1
        logger.debug(f"設備 {device_id} 重試次數: {self.session_state[key]}")
    
    def reset_retry_count(self, device_id: str):
        """重置重試次數"""
        key = f'{self.retry_prefix}{device_id}'
        if key in self.session_state:
            del self.session_state[key]
    
    def is_in_cooldown(self, device_id: str, cooldown_seconds: int) -> bool:
        """檢查是否在冷卻期"""
        key = f'{self.cooldown_prefix}{device_id}'
        last_attempt = self.session_state.get(key)
        
        if last_attempt is None:
            return False
        
        if isinstance(last_attempt, str):
            last_attempt = datetime.fromisoformat(last_attempt)
        
        time_since = (datetime.now() - last_attempt).total_seconds()
        is_cooldown = time_since < cooldown_seconds
        
        if is_cooldown:
            remaining = cooldown_seconds - time_since
            logger.debug(f"設備 {device_id} 冷卻中，剩餘 {remaining:.0f} 秒")
        
        return is_cooldown
    
    def set_cooldown(self, device_id: str):
        """設置冷卻時間"""
        key = f'{self.cooldown_prefix}{device_id}'
        self.session_state[key] = datetime.now()
        logger.debug(f"設備 {device_id} 進入冷卻期")



