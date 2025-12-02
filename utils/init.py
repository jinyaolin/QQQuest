"""
系統初始化工具
確保所有頁面都能正確初始化核心組件
"""
import streamlit as st
from utils.logger import get_logger

logger = get_logger(__name__)


def ensure_initialization():
    """
    確保系統已初始化
    如果未初始化，自動進行初始化
    
    這個函數應該在每個頁面開始時調用
    """
    if 'initialized' not in st.session_state or not st.session_state.initialized:
        logger.info("檢測到系統未初始化，開始自動初始化...")
        
        try:
            from core.adb_manager import ADBManager
            from core.device_registry import DeviceRegistry
            
            # 初始化核心組件
            st.session_state.adb_manager = ADBManager()
            st.session_state.device_registry = DeviceRegistry()
            
            st.session_state.initialized = True
            logger.info("✅ 系統自動初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 系統初始化失敗: {e}")
            st.error(f"⚠️ 系統初始化失敗: {e}")
            st.error("請檢查 ADB 是否正確安裝，或返回首頁重試")
            
            if st.button("返回首頁"):
                st.switch_page("app.py")
            
            st.stop()
            return False
    
    return True


def ensure_action_registry():
    """確保動作註冊管理器已初始化"""
    if 'action_registry' not in st.session_state:
        try:
            from core.action_registry import ActionRegistry
            st.session_state.action_registry = ActionRegistry()
            logger.debug("動作註冊管理器已初始化")
        except Exception as e:
            logger.error(f"動作註冊管理器初始化失敗: {e}")
            return False
    return True


def ensure_room_registry():
    """確保房間註冊管理器已初始化"""
    if 'room_registry' not in st.session_state:
        try:
            from core.room_registry import RoomRegistry
            st.session_state.room_registry = RoomRegistry()
            logger.debug("房間註冊管理器已初始化")
        except Exception as e:
            logger.error(f"房間註冊管理器初始化失敗: {e}")
            return False
    return True


def init_all():
    """
    初始化所有組件
    適用於需要所有功能的頁面
    """
    if not ensure_initialization():
        return False
    
    ensure_action_registry()
    ensure_room_registry()
    
    return True




