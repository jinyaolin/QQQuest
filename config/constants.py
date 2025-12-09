"""
系統常數定義
"""
from enum import Enum


class DeviceStatus(str, Enum):
    """設備狀態"""
    ONLINE = "online"  # 在線（在 adb devices 列表中，狀態為 device）
    OFFLINE = "offline"  # 離線（在 adb devices 列表中，狀態為 offline）
    NOT_CONNECTED = "not_connected"  # 未連接（不在 adb devices 列表中）
    ADB_NOT_ENABLED = "adb_not_enabled"  # WiFi ADB 未開啟（Ping 通但無法連接）
    BUSY = "busy"  # 忙碌中
    CONNECTING = "connecting"  # 連接中
    ERROR = "error"  # 錯誤


class ConnectionType(str, Enum):
    """連線類型"""
    USB = "usb"  # USB 連線
    WIFI = "wifi"  # WiFi 連線
    UNKNOWN = "unknown"  # 未知


class RoomStatus(str, Enum):
    """房間狀態"""
    RUNNING = "running"  # 執行中
    PAUSED = "paused"  # 暫停
    STOPPED = "stopped"  # 停止
    IDLE = "idle"  # 閒置


class ActionType(str, Enum):
    """動作類型"""
    SLEEP = "sleep"  # 休眠
    WAKE = "wake"  # 喚醒
    START_APP = "start_app"  # 啟動應用
    STOP_APP = "stop_app"  # 關閉應用
    SEND_MESSAGE = "send_message"  # 傳送訊息
    REBOOT = "reboot"  # 重啟
    SCREENSHOT = "screenshot"  # 截圖
    INSTALL_APK = "install_apk"  # 安裝 APK
    UNINSTALL_APP = "uninstall_app"  # 卸載應用
    PUSH_FILE = "push_file"  # 推送檔案
    PULL_FILE = "pull_file"  # 拉取檔案
    CUSTOM = "custom"  # 自訂


class CueStatus(str, Enum):
    """CUE 狀態"""
    PENDING = "pending"  # 待執行
    RUNNING = "running"  # 執行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消


# ADB 命令模板
ADB_COMMANDS = {
    "sleep": "input keyevent KEYCODE_SLEEP",
    "wake": "input keyevent KEYCODE_WAKEUP",
    "start_app": "am start -n {package}/{activity}",
    "stop_app": "am force-stop {package}",
    "send_message": "am broadcast -a {package}.MESSAGE --es msg \"{content}\"",
    "reboot": "reboot",
    "screenshot": "screencap -p /sdcard/screenshot.png",
    "get_battery": "dumpsys battery | grep level",
    "get_temperature": "dumpsys battery | grep temperature",
    "get_packages": "pm list packages",
    "install_apk": "install -r {apk_path}",
    "uninstall_app": "uninstall {package}",
}

# 狀態圖示
STATUS_ICONS = {
    DeviceStatus.ONLINE: "🟢",
    DeviceStatus.OFFLINE: "🟠",  # 橙色表示在列表中但狀態為 offline
    DeviceStatus.NOT_CONNECTED: "⚫",  # 黑色表示未連接
    DeviceStatus.ADB_NOT_ENABLED: "🟡",  # 黃色表示需要手動開啟 WiFi ADB
    DeviceStatus.BUSY: "🟡",
    DeviceStatus.CONNECTING: "🔵",
    DeviceStatus.ERROR: "⚠️",
}

CONNECTION_ICONS = {
    ConnectionType.USB: "🔌",
    ConnectionType.WIFI: "📶",
    ConnectionType.UNKNOWN: "❓",
}

# 預設動作圖示
ACTION_ICONS = {
    ActionType.SLEEP: "😴",
    ActionType.WAKE: "👁️",
    ActionType.START_APP: "🚀",
    ActionType.STOP_APP: "❌",
    ActionType.SEND_MESSAGE: "💬",
    ActionType.REBOOT: "🔄",
    ActionType.SCREENSHOT: "📸",
    ActionType.INSTALL_APK: "📦",
    ActionType.UNINSTALL_APP: "🗑️",
}



