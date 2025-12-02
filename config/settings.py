"""
系統設定檔
"""
from pathlib import Path
from typing import Dict, Any
import json

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent

# 資料目錄
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
TEMP_DIR = PROJECT_ROOT / "temp"

# 資料檔案路徑
DEVICES_DB = DATA_DIR / "devices.json"
DEVICE_REGISTRY_DB = DATA_DIR / "device_registry.json"
ROOMS_DB = DATA_DIR / "rooms.json"
ACTIONS_DB = DATA_DIR / "actions.json"
CUES_DB = DATA_DIR / "cues.json"
USER_CONFIG_DB = DATA_DIR / "user_config.json"  # 使用者自訂設定

# ADB 設定
ADB_DEFAULT_PORT = 5555
ADB_SCAN_INTERVAL = 3  # USB 掃描間隔（秒）
ADB_CONNECTION_TIMEOUT = 15  # 連線超時（秒）- Quest 設備響應較慢，需要更長時間

# 設備監控設定
DEVICE_UPDATE_INTERVAL = 5  # 設備狀態更新間隔（秒）
BATTERY_LOW_THRESHOLD = 20  # 低電量警告閾值（%）
TEMPERATURE_HIGH_THRESHOLD = 40  # 高溫警告閾值（°C）

# scrcpy 監看設定
SCRCPY_CONFIG: Dict[str, Any] = {
    "bitrate": "8M",           # 視訊位元率（例如：8M, 16M, 2M）
    "max_size": 1024,          # 最大畫面寬度（像素）
    "max_fps": 60,             # 最大幀率（0 = 無限制）
    "window_width": None,      # 視窗寬度（None = 自動）
    "window_height": None,     # 視窗高度（None = 自動）
    "window_x": None,          # 視窗 X 座標（None = 自動）
    "window_y": None,          # 視窗 Y 座標（None = 自動）
    "stay_awake": True,        # 保持設備清醒
    "show_touches": False,     # 顯示觸控點
    "fullscreen": False,       # 全螢幕模式
    "always_on_top": False,    # 視窗置頂
    "turn_screen_off": False,  # 關閉設備螢幕（只鏡像）
    "enable_audio": False,     # 啟用音訊轉發（預設關閉以避免關閉 Quest 聲音）
    "render_driver": None,     # 渲染驅動（None = 自動，或 "opengl", "opengles2", "opengles", "metal", "software"）
}

# 截圖預覽設定
SCREENSHOT_CONFIG: Dict[str, Any] = {
    "enabled": True,           # 是否啟用截圖預覽
    "update_interval": 5,      # 截圖更新頻率（秒）1-10
    "max_width": 300,          # 預覽圖最大寬度（像素）
    "max_height": 200,         # 預覽圖最大高度（像素）
    "quality": 80,             # JPEG 品質（1-100）
    "cache_enabled": True,     # 是否啟用快取
}

# 時間碼設定
DEFAULT_FPS = 60  # 預設幀率
TIMECODE_UPDATE_INTERVAL = 0.1  # 時間碼更新間隔（秒）

# 同步設定
SYNC_INTERVAL = 30  # 時間同步間隔（秒）
SYNC_SAMPLES = 10  # 同步採樣次數
SYNC_PRECISION_MS = 50  # 同步精度要求（毫秒）

# UI 設定
UI_REFRESH_INTERVAL = 3  # UI 自動刷新間隔（秒）
CARD_WIDTH = 200  # 設備卡片寬度（像素）
CARD_HEIGHT = 220  # 設備卡片高度（像素）

# Streamlit 設定
STREAMLIT_CONFIG: Dict[str, Any] = {
    "page_title": "QQQuest - Quest 設備管理系統",
    "page_icon": "📱",
    "layout": "wide",
    "initial_sidebar_state": "collapsed",  # 侧边栏默认折叠，点击左上角箭头可展开
}


def ensure_directories():
    """確保所有必要的目錄存在"""
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)


def load_config(config_file: Path) -> Dict[str, Any]:
    """載入 JSON 配置檔案"""
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(config_file: Path, data: Dict[str, Any]):
    """儲存 JSON 配置檔案"""
    ensure_directories()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_config() -> Dict[str, Any]:
    """
    獲取使用者自訂設定，如果不存在則使用預設值
    
    Returns:
        使用者設定字典
    """
    default_config = {
        "scrcpy": SCRCPY_CONFIG.copy(),
        "screenshot": SCREENSHOT_CONFIG.copy(),
    }
    
    if USER_CONFIG_DB.exists():
        try:
            user_config = load_config(USER_CONFIG_DB)
            # 合併使用者設定和預設設定（使用者設定優先）
            for category in default_config:
                if category in user_config:
                    default_config[category].update(user_config[category])
            return default_config
        except Exception as e:
            logger_instance = get_logger(__name__)
            logger_instance.error(f"載入使用者設定失敗: {e}")
            return default_config
    
    return default_config


def save_user_config(config: Dict[str, Any]) -> bool:
    """
    儲存使用者自訂設定
    
    Args:
        config: 使用者設定字典
        
    Returns:
        是否成功儲存
    """
    try:
        save_config(USER_CONFIG_DB, config)
        return True
    except Exception as e:
        logger_instance = get_logger(__name__)
        logger_instance.error(f"儲存使用者設定失敗: {e}")
        return False


# 延遲導入 logger 以避免循環導入
def get_logger(name):
    try:
        from utils.logger import get_logger as _get_logger
        return _get_logger(name)
    except ImportError:
        import logging
        return logging.getLogger(name)


# 初始化目錄
ensure_directories()

