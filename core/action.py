"""
動作（Action）資料模型
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


class ActionType(str, Enum):
    """動作類型枚舉"""
    WAKE_UP = "wake_up"           # 喚醒
    SLEEP = "sleep"               # 休眠
    KEEP_AWAKE = "keep_awake"     # 保持喚醒（接電源時不進入深度睡眠）
    LAUNCH_APP = "launch_app"     # 執行程式
    STOP_APP = "stop_app"         # 關閉程式
    RESTART_APP = "restart_app"   # 重啟應用
    SEND_KEY = "send_key"         # 發送按鍵


# 動作類型中文名稱映射
ACTION_TYPE_NAMES = {
    ActionType.WAKE_UP: "喚醒設備",
    ActionType.SLEEP: "休眠設備",
    ActionType.KEEP_AWAKE: "保持喚醒",
    ActionType.LAUNCH_APP: "執行程式",
    ActionType.STOP_APP: "關閉程式",
    ActionType.RESTART_APP: "重啟應用",
    ActionType.SEND_KEY: "發送按鍵",
}

# 動作類型圖標映射
ACTION_TYPE_ICONS = {
    ActionType.WAKE_UP: "☀️",
    ActionType.SLEEP: "😴",
    ActionType.KEEP_AWAKE: "🔌",
    ActionType.LAUNCH_APP: "🚀",
    ActionType.STOP_APP: "🛑",
    ActionType.RESTART_APP: "🔄",
    ActionType.SEND_KEY: "⌨️",
}


class Action(BaseModel):
    """動作模型"""
    action_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = Field(..., min_length=1, max_length=50, description="動作名稱")
    description: Optional[str] = Field(None, max_length=200, description="動作說明")
    action_type: ActionType = Field(..., description="動作類型")
    params: Dict[str, Any] = Field(default_factory=dict, description="動作參數")
    
    # 時間戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 執行統計
    execution_count: int = Field(default=0, description="執行次數")
    success_count: int = Field(default=0, description="成功次數")
    failure_count: int = Field(default=0, description="失敗次數")
    last_executed_at: Optional[datetime] = Field(None, description="最後執行時間")
    last_execution_status: Optional[str] = Field(None, description="最後執行狀態")
    
    class Config:
        use_enum_values = True
    
    @property
    def type_name(self) -> str:
        """獲取動作類型中文名稱"""
        return ACTION_TYPE_NAMES.get(ActionType(self.action_type), self.action_type)
    
    @property
    def type_icon(self) -> str:
        """獲取動作類型圖標"""
        return ACTION_TYPE_ICONS.get(ActionType(self.action_type), "⚡")
    
    @property
    def success_rate(self) -> float:
        """計算成功率"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100
    
    @property
    def display_name(self) -> str:
        """顯示名稱（包含圖標）"""
        return f"{self.type_icon} {self.name}"
    
    def increment_execution(self, success: bool = True, status: str = ""):
        """增加執行計數"""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.last_executed_at = datetime.now()
        self.last_execution_status = status
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於儲存）"""
        data = self.model_dump(exclude_none=False)
        # 轉換 datetime 為字串
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        if self.last_executed_at:
            data['last_executed_at'] = self.last_executed_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """從字典創建（用於讀取）"""
        # 轉換字串為 datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if 'last_executed_at' in data and isinstance(data['last_executed_at'], str):
            data['last_executed_at'] = datetime.fromisoformat(data['last_executed_at'])
        return cls(**data)


class ActionParamsValidator:
    """動作參數驗證器"""
    
    @staticmethod
    def validate_wake_up(params: Dict[str, Any]) -> tuple[bool, str]:
        """驗證喚醒參數"""
        # 喚醒動作不需要必填參數
        return True, ""
    
    @staticmethod
    def validate_sleep(params: Dict[str, Any]) -> tuple[bool, str]:
        """驗證休眠參數"""
        # 休眠動作不需要必填參數
        return True, ""
    
    @staticmethod
    def validate_keep_awake(params: Dict[str, Any]) -> tuple[bool, str]:
        """驗證保持喚醒參數"""
        # 檢查 mode 參數（可選，默認為 3）
        mode = params.get('mode', 3)
        if mode not in [0, 1, 2, 3]:
            return False, "mode 參數必須為 0、1、2 或 3"
        return True, ""
    
    @staticmethod
    def validate_launch_app(params: Dict[str, Any]) -> tuple[bool, str]:
        """驗證執行程式參數"""
        if not params.get('package'):
            return False, "package 參數為必填"
        
        # 驗證 package 格式
        package = params['package']
        import re
        if not re.match(r'^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$', package.lower()):
            return False, "package 格式不正確（應為：com.example.app）"
        
        # 驗證 activity 格式（如果有）
        activity = params.get('activity', '')
        if activity and not activity.startswith('.') and '.' not in activity:
            return False, "activity 格式不正確（應為：.MainActivity 或完整類名）"
        
        return True, ""
    
    @staticmethod
    def validate_stop_app(params: Dict[str, Any]) -> tuple[bool, str]:
        """驗證關閉程式參數"""
        if not params.get('package'):
            return False, "package 參數為必填"
        
        package = params['package']
        import re
        if not re.match(r'^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$', package.lower()):
            return False, "package 格式不正確（應為：com.example.app）"
        
        return True, ""
    
    @staticmethod
    def validate_restart_app(params: Dict[str, Any]) -> tuple[bool, str]:
        """驗證重啟應用參數"""
        if not params.get('package'):
            return False, "package 參數為必填"
        
        package = params['package']
        import re
        if not re.match(r'^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$', package.lower()):
            return False, "package 格式不正確（應為：com.example.app）"
        
        return True, ""
    
    @staticmethod
    def validate_send_key(params: Dict[str, Any]) -> tuple[bool, str]:
        """驗證發送按鍵參數"""
        if not params.get('keycode'):
            return False, "keycode 參數為必填"
        
        return True, ""
    
    @classmethod
    def validate(cls, action_type: ActionType, params: Dict[str, Any]) -> tuple[bool, str]:
        """根據動作類型驗證參數"""
        validators = {
            ActionType.WAKE_UP: cls.validate_wake_up,
            ActionType.SLEEP: cls.validate_sleep,
            ActionType.KEEP_AWAKE: cls.validate_keep_awake,
            ActionType.LAUNCH_APP: cls.validate_launch_app,
            ActionType.STOP_APP: cls.validate_stop_app,
            ActionType.RESTART_APP: cls.validate_restart_app,
            ActionType.SEND_KEY: cls.validate_send_key,
        }
        
        validator = validators.get(action_type)
        if validator:
            return validator(params)
        
        return False, f"未知的動作類型: {action_type}"


# 常用按鍵碼
COMMON_KEYCODES = {
    "HOME": {"code": 3, "name": "主頁", "description": "返回主頁面"},
    "BACK": {"code": 4, "name": "返回", "description": "返回上一頁"},
    "MENU": {"code": 82, "name": "選單", "description": "打開選單"},
    "POWER": {"code": 26, "name": "電源", "description": "電源鍵"},
    "VOLUME_UP": {"code": 24, "name": "音量+", "description": "增加音量"},
    "VOLUME_DOWN": {"code": 25, "name": "音量-", "description": "降低音量"},
    "WAKEUP": {"code": 224, "name": "喚醒", "description": "喚醒設備"},
    "SLEEP": {"code": 223, "name": "睡眠", "description": "進入睡眠"},
}



