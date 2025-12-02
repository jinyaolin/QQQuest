"""
房間（Room）資料模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


class Room(BaseModel):
    """房間模型"""
    room_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = Field(..., min_length=1, max_length=50, description="房間名稱")
    description: Optional[str] = Field(None, max_length=200, description="房間說明")
    max_devices: int = Field(default=0, ge=0, description="最大設備數量（0=無限制）")
    device_ids: List[str] = Field(default_factory=list, description="房間內設備 ID 列表")
    
    # 時間戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def device_count(self) -> int:
        """獲取房間內設備數量"""
        return len(self.device_ids)
    
    @property
    def is_full(self) -> bool:
        """檢查房間是否已滿"""
        if self.max_devices == 0:  # 無限制
            return False
        return len(self.device_ids) >= self.max_devices
    
    @property
    def display_name(self) -> str:
        """顯示名稱"""
        return f"🏠 {self.name}"
    
    @property
    def capacity_text(self) -> str:
        """容量文字"""
        if self.max_devices == 0:
            return f"{self.device_count}"
        else:
            return f"{self.device_count}/{self.max_devices}"
    
    def add_device(self, device_id: str) -> bool:
        """
        添加設備到房間
        
        Args:
            device_id: 設備 ID
        
        Returns:
            是否成功
        """
        # 檢查是否已存在
        if device_id in self.device_ids:
            return False
        
        # 檢查是否已滿
        if self.is_full:
            return False
        
        self.device_ids.append(device_id)
        self.updated_at = datetime.now()
        return True
    
    def remove_device(self, device_id: str) -> bool:
        """
        從房間移除設備
        
        Args:
            device_id: 設備 ID
        
        Returns:
            是否成功
        """
        if device_id in self.device_ids:
            self.device_ids.remove(device_id)
            self.updated_at = datetime.now()
            return True
        return False
    
    def has_device(self, device_id: str) -> bool:
        """
        檢查設備是否在房間內
        
        Args:
            device_id: 設備 ID
        
        Returns:
            是否在房間內
        """
        return device_id in self.device_ids
    
    def to_dict(self) -> dict:
        """轉換為字典（用於儲存）"""
        data = self.model_dump(exclude_none=False)
        # 轉換 datetime 為字串
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Room':
        """從字典創建（用於讀取）"""
        # 轉換字串為 datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)



