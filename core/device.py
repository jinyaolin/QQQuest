"""
設備類別
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from config.constants import DeviceStatus, ConnectionType


class Device(BaseModel):
    """設備類別"""
    
    # 基本資訊
    device_id: str = Field(..., description="設備 ID（內部使用）")
    serial: str = Field(..., description="序列號（Serial Number，唯一識別）")
    alias: str = Field(default="", description="代號（使用者自訂）")
    name: str = Field(default="", description="設備名稱")
    model: str = Field(default="", description="設備型號")
    android_version: str = Field(default="", description="Android 版本")
    
    # 連線資訊
    ip: str = Field(default="", description="IP 地址")
    port: int = Field(default=5555, description="端口")
    connection_type: ConnectionType = Field(
        default=ConnectionType.UNKNOWN,
        description="連線類型"
    )
    status: DeviceStatus = Field(
        default=DeviceStatus.OFFLINE,
        description="連線狀態"
    )
    
    # 狀態資訊
    battery: int = Field(default=0, description="電量百分比")
    temperature: float = Field(default=0.0, description="溫度（攝氏）")
    is_charging: bool = Field(default=False, description="是否充電中")
    
    # 管理資訊
    room_id: Optional[str] = Field(default=None, description="所屬房間 ID")
    notes: str = Field(default="", description="備註")
    sort_order: int = Field(default=0, description="排序順序")
    last_seen: Optional[datetime] = Field(
        default=None,
        description="最後上線時間"
    )
    first_connected: Optional[datetime] = Field(
        default=None,
        description="首次連接時間"
    )
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @property
    def connection_string(self) -> str:
        """取得連接字串"""
        if self.ip:
            return f"{self.ip}:{self.port}"
        return self.serial
    
    @property
    def display_name(self) -> str:
        """取得顯示名稱"""
        if self.alias:
            return self.alias
        if self.name:
            return self.name
        return self.serial[:8] + "..."
    
    @property
    def short_serial(self) -> str:
        """取得縮短的序列號"""
        if len(self.serial) > 12:
            return self.serial[:4] + ".." + self.serial[-4:]
        return self.serial
    
    @property
    def is_online(self) -> bool:
        """檢查是否在線"""
        return self.status == DeviceStatus.ONLINE
    
    @property
    def is_low_battery(self) -> bool:
        """檢查是否低電量"""
        from config.settings import BATTERY_LOW_THRESHOLD
        return self.battery < BATTERY_LOW_THRESHOLD
    
    @property
    def is_high_temperature(self) -> bool:
        """檢查是否高溫"""
        from config.settings import TEMPERATURE_HIGH_THRESHOLD
        return self.temperature > TEMPERATURE_HIGH_THRESHOLD
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        # 使用 Pydantic v2 的 model_dump，mode='python' 確保正確序列化
        data = self.model_dump(mode='python', exclude_none=False)
        
        # 確保 datetime 轉換為 ISO 字串
        if isinstance(data.get('last_seen'), datetime):
            data['last_seen'] = data['last_seen'].isoformat()
        if isinstance(data.get('first_connected'), datetime):
            data['first_connected'] = data['first_connected'].isoformat()
        
        # 移除 None 值（在轉換後移除，避免遺漏某些欄位）
        data = {k: v for k, v in data.items() if v is not None}
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Device':
        """從字典建立"""
        # 轉換 ISO 格式字串為 datetime
        if 'last_seen' in data and isinstance(data['last_seen'], str):
            data['last_seen'] = datetime.fromisoformat(data['last_seen'])
        if 'first_connected' in data and isinstance(data['first_connected'], str):
            data['first_connected'] = datetime.fromisoformat(data['first_connected'])
        return cls(**data)
    
    def update_status(
        self,
        status: Optional[DeviceStatus] = None,
        battery: Optional[int] = None,
        temperature: Optional[float] = None,
        is_charging: Optional[bool] = None
    ):
        """更新設備狀態"""
        if status is not None:
            self.status = status
            if status == DeviceStatus.ONLINE:
                self.last_seen = datetime.now()
        
        if battery is not None:
            self.battery = battery
        
        if temperature is not None:
            self.temperature = temperature
        
        if is_charging is not None:
            self.is_charging = is_charging

