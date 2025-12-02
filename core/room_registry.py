"""
房間註冊管理器
"""
from typing import List, Optional, Dict, Any, Tuple
from tinydb import TinyDB, Query
from pathlib import Path
from core.room import Room
from config.settings import DATA_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class RoomRegistry:
    """房間註冊管理器"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化房間註冊管理器
        
        Args:
            db_path: 資料庫路徑，預設為 DATA_DIR / "rooms.json"
        """
        if db_path is None:
            db_path = DATA_DIR / "rooms.json"
        
        self.db_path = db_path
        self.db = TinyDB(db_path)
        self.rooms_table = self.db.table('rooms')
        logger.info(f"房間註冊管理器已初始化，資料庫路徑: {db_path}")
    
    def create_room(
        self,
        name: str,
        description: Optional[str] = None,
        max_devices: int = 0
    ) -> Optional[Room]:
        """
        創建新房間
        
        Args:
            name: 房間名稱
            description: 房間說明
            max_devices: 最大設備數量（0=無限制）
        
        Returns:
            Room 對象，失敗返回 None
        """
        try:
            # 檢查名稱是否已存在
            if self.get_room_by_name(name):
                logger.error(f"房間名稱已存在: {name}")
                return None
            
            # 創建房間
            room = Room(
                name=name,
                description=description,
                max_devices=max_devices
            )
            
            # 儲存到資料庫
            self.rooms_table.insert(room.to_dict())
            logger.info(f"✅ 創建房間成功: {room.display_name} (ID: {room.room_id})")
            
            return room
        
        except Exception as e:
            logger.error(f"❌ 創建房間失敗: {e}")
            return None
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """
        根據 ID 獲取房間
        
        Args:
            room_id: 房間 ID
        
        Returns:
            Room 對象，不存在返回 None
        """
        try:
            RoomQuery = Query()
            result = self.rooms_table.get(RoomQuery.room_id == room_id)
            
            if result:
                return Room.from_dict(result)
            
            return None
        
        except Exception as e:
            logger.error(f"❌ 獲取房間失敗 (ID: {room_id}): {e}")
            return None
    
    def get_room_by_name(self, name: str) -> Optional[Room]:
        """
        根據名稱獲取房間
        
        Args:
            name: 房間名稱
        
        Returns:
            Room 對象，不存在返回 None
        """
        try:
            RoomQuery = Query()
            result = self.rooms_table.get(RoomQuery.name == name)
            
            if result:
                return Room.from_dict(result)
            
            return None
        
        except Exception as e:
            logger.error(f"❌ 獲取房間失敗 (名稱: {name}): {e}")
            return None
    
    def get_all_rooms(self) -> List[Room]:
        """
        獲取所有房間
        
        Returns:
            Room 列表
        """
        try:
            results = self.rooms_table.all()
            rooms = [Room.from_dict(data) for data in results]
            logger.debug(f"獲取所有房間: {len(rooms)} 個")
            return rooms
        
        except Exception as e:
            logger.error(f"❌ 獲取所有房間失敗: {e}")
            return []
    
    def update_room(self, room: Room) -> bool:
        """
        更新房間
        
        Args:
            room: Room 對象
        
        Returns:
            是否成功
        """
        try:
            # 更新時間戳
            from datetime import datetime
            room.updated_at = datetime.now()
            
            # 更新資料庫
            RoomQuery = Query()
            self.rooms_table.update(
                room.to_dict(),
                RoomQuery.room_id == room.room_id
            )
            
            logger.info(f"✅ 更新房間成功: {room.display_name} (ID: {room.room_id})")
            return True
        
        except Exception as e:
            logger.error(f"❌ 更新房間失敗 (ID: {room.room_id}): {e}")
            return False
    
    def delete_room(self, room_id: str) -> bool:
        """
        刪除房間
        
        Args:
            room_id: 房間 ID
        
        Returns:
            是否成功
        """
        try:
            RoomQuery = Query()
            result = self.rooms_table.remove(RoomQuery.room_id == room_id)
            
            if result:
                logger.info(f"✅ 刪除房間成功 (ID: {room_id})")
                return True
            else:
                logger.warning(f"⚠️ 房間不存在 (ID: {room_id})")
                return False
        
        except Exception as e:
            logger.error(f"❌ 刪除房間失敗 (ID: {room_id}): {e}")
            return False
    
    def add_device_to_room(self, room_id: str, device_id: str) -> Tuple[bool, str]:
        """
        添加設備到房間
        
        Args:
            room_id: 房間 ID
            device_id: 設備 ID
        
        Returns:
            (成功, 訊息)
        """
        try:
            # 獲取房間
            room = self.get_room(room_id)
            if not room:
                return False, "房間不存在"
            
            # 檢查是否已滿
            if room.is_full:
                return False, f"房間已滿 ({room.capacity_text})"
            
            # 檢查設備是否已在其他房間
            current_room = self.get_device_room(device_id)
            if current_room:
                # 從當前房間移除
                current_room.remove_device(device_id)
                self.update_room(current_room)
                logger.info(f"設備 {device_id} 已從房間 {current_room.name} 移出")
            
            # 添加到新房間
            if room.add_device(device_id):
                self.update_room(room)
                logger.info(f"✅ 設備 {device_id} 已添加到房間 {room.name}")
                
                if current_room:
                    return True, f"設備已從「{current_room.name}」轉移到「{room.name}」"
                else:
                    return True, f"設備已添加到「{room.name}」"
            else:
                return False, "添加設備失敗"
        
        except Exception as e:
            logger.error(f"❌ 添加設備到房間失敗: {e}")
            return False, f"添加失敗: {str(e)}"
    
    def remove_device_from_room(self, room_id: str, device_id: str) -> Tuple[bool, str]:
        """
        從房間移除設備
        
        Args:
            room_id: 房間 ID
            device_id: 設備 ID
        
        Returns:
            (成功, 訊息)
        """
        try:
            # 獲取房間
            room = self.get_room(room_id)
            if not room:
                return False, "房間不存在"
            
            # 移除設備
            if room.remove_device(device_id):
                self.update_room(room)
                logger.info(f"✅ 設備 {device_id} 已從房間 {room.name} 移出")
                return True, f"設備已從「{room.name}」移出"
            else:
                return False, "設備不在此房間內"
        
        except Exception as e:
            logger.error(f"❌ 從房間移除設備失敗: {e}")
            return False, f"移除失敗: {str(e)}"
    
    def get_device_room(self, device_id: str) -> Optional[Room]:
        """
        獲取設備所在的房間
        
        Args:
            device_id: 設備 ID
        
        Returns:
            Room 對象，不存在返回 None
        """
        try:
            all_rooms = self.get_all_rooms()
            for room in all_rooms:
                if room.has_device(device_id):
                    return room
            return None
        
        except Exception as e:
            logger.error(f"❌ 獲取設備房間失敗: {e}")
            return None
    
    def get_room_devices(self, room_id: str, device_registry) -> List:
        """
        獲取房間內的所有設備對象
        
        Args:
            room_id: 房間 ID
            device_registry: DeviceRegistry 實例
        
        Returns:
            Device 列表
        """
        try:
            room = self.get_room(room_id)
            if not room:
                return []
            
            devices = []
            for device_id in room.device_ids:
                device = device_registry.get_device_by_id(device_id)
                if device:
                    devices.append(device)
            
            return devices
        
        except Exception as e:
            logger.error(f"❌ 獲取房間設備失敗: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取統計信息
        
        Returns:
            統計信息字典
        """
        try:
            all_rooms = self.get_all_rooms()
            
            total_devices = sum(room.device_count for room in all_rooms)
            
            stats = {
                "total_rooms": len(all_rooms),
                "total_devices": total_devices,
                "rooms_with_devices": len([r for r in all_rooms if r.device_count > 0]),
                "empty_rooms": len([r for r in all_rooms if r.device_count == 0]),
            }
            
            return stats
        
        except Exception as e:
            logger.error(f"❌ 獲取統計信息失敗: {e}")
            return {}
    
    def close(self):
        """關閉資料庫連接"""
        self.db.close()
        logger.info("房間註冊管理器已關閉")




