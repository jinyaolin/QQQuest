"""
設備註冊表 - 管理設備序號和歷史記錄
"""
import traceback
from typing import Dict, List, Optional
from datetime import datetime
from tinydb import TinyDB, Query
from config.settings import DEVICE_REGISTRY_DB, DEVICES_DB
from core.device import Device
from utils.logger import get_logger

logger = get_logger(__name__)


class DeviceRegistry:
    """設備註冊表類別"""
    
    def __init__(self):
        self.registry_db = TinyDB(DEVICE_REGISTRY_DB)
        self.devices_db = TinyDB(DEVICES_DB)
        self.query = Query()
        logger.info("設備註冊表已初始化")
    
    def is_known_device(self, serial: str) -> bool:
        """檢查設備是否已知（之前連接過）"""
        result = self.registry_db.search(self.query.serial == serial)
        is_known = len(result) > 0
        logger.debug(f"🔍 檢查設備 {serial[:12]}... : {'已知' if is_known else '未知'}")
        return is_known
    
    def register_device(self, serial: str, device_data: Dict) -> bool:
        """
        註冊新設備
        
        Args:
            serial: 設備序列號
            device_data: 設備資料（dict 格式）
        """
        try:
            if self.is_known_device(serial):
                logger.warning(f"設備已註冊: {serial}")
                return False
            
            # 如果沒有 sort_order，自動分配一個
            if 'sort_order' not in device_data or device_data['sort_order'] == 0:
                # 找到當前最大的 sort_order
                all_devices = self.devices_db.all()
                max_order = max([d.get('sort_order', 0) for d in all_devices], default=0)
                device_data['sort_order'] = max_order + 1
                logger.debug(f"自動分配 sort_order: {device_data['sort_order']}")
            
            # 記錄註冊資訊
            registry_entry = {
                'serial': serial,
                'device_id': device_data.get('device_id'),
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'connection_count': 1,
            }
            
            self.registry_db.insert(registry_entry)
            
            # 儲存設備完整資料
            self.devices_db.insert(device_data)
            
            logger.info(f"新設備已註冊: {serial} (sort_order: {device_data['sort_order']})")
            return True
            
        except Exception as e:
            logger.error(f"註冊設備失敗: {e}")
            return False
    
    def update_device(self, serial: str, device_data: Dict) -> bool:
        """更新設備資料"""
        try:
            # 更新註冊表
            self.registry_db.update(
                {
                    'last_seen': datetime.now().isoformat(),
                },
                self.query.serial == serial
            )
            
            # 增加連接次數
            entry = self.registry_db.get(self.query.serial == serial)
            if entry:
                count = entry.get('connection_count', 0) + 1
                self.registry_db.update(
                    {'connection_count': count},
                    self.query.serial == serial
                )
            
            self.devices_db.update(
                device_data,
                self.query.serial == serial
            )
            return True
            
        except Exception as e:
            logger.error(f"更新設備失敗: {e}")
            logger.error(f"錯誤詳情:\n{traceback.format_exc()}")
            return False
    
    def get_device(self, serial: str) -> Optional[Device]:
        """取得設備資料"""
        result = self.devices_db.search(self.query.serial == serial)
        if result:
            try:
                return Device.from_dict(result[0])
            except Exception as e:
                logger.error(f"解析設備資料失敗: {e}")
                return None
        return None
    
    def get_all_devices(self) -> List[Device]:
        """取得所有設備（按照 sort_order 排序）"""
        all_data = self.devices_db.all()
        logger.debug(f"📂 從資料庫讀取: {len(all_data)} 筆設備資料")
        
        devices = []
        needs_update = False
        
        for idx, data in enumerate(all_data):
            try:
                # 檢查並補上 sort_order（如果沒有）
                if 'sort_order' not in data or data.get('sort_order', 0) == 0:
                    data['sort_order'] = idx + 1
                    needs_update = True
                    logger.info(f"🔧 補上 sort_order: {data.get('serial', 'unknown')[:8]}... -> {data['sort_order']}")
                
                device = Device.from_dict(data)
                devices.append(device)
                logger.debug(f"  [{idx+1}] {device.display_name} ({device.serial[:8]}...) sort_order={device.sort_order}")
            except Exception as e:
                logger.error(f"解析設備資料失敗: {e}, 資料: {data}")
                continue
        
        # 如果有補上 sort_order，保存回資料庫
        if needs_update:
            logger.info(f"💾 保存補上的 sort_order")
            for device in devices:
                self.devices_db.update(
                    {'sort_order': device.sort_order},
                    self.query.serial == device.serial
                )
        
        # 按照 sort_order 排序
        devices.sort(key=lambda d: d.sort_order)
        
        logger.info(f"📋 成功載入 {len(devices)} 台設備（已按 sort_order 排序）")
        return devices
    
    def remove_device(self, serial: str) -> bool:
        """移除設備（從註冊表和設備列表）"""
        try:
            self.registry_db.remove(self.query.serial == serial)
            self.devices_db.remove(self.query.serial == serial)
            logger.info(f"設備已移除: {serial}")
            return True
        except Exception as e:
            logger.error(f"移除設備失敗: {e}")
            return False
    
    def get_registry_info(self, serial: str) -> Optional[Dict]:
        """取得註冊資訊"""
        result = self.registry_db.search(self.query.serial == serial)
        return result[0] if result else None
    
    def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """根據 device_id 取得設備"""
        result = self.devices_db.search(self.query.device_id == device_id)
        if result:
            try:
                return Device.from_dict(result[0])
            except Exception as e:
                logger.error(f"解析設備資料失敗: {e}")
                return None
        return None
    
    def reorder_devices(self):
        """重新排序資料庫中的設備（按照 sort_order）"""
        try:
            all_data = self.devices_db.all()
            
            if len(all_data) == 0:
                return
            
            devices = []
            for data in all_data:
                try:
                    device = Device.from_dict(data)
                    devices.append(device)
                except Exception as e:
                    logger.error(f"解析設備資料失敗: {e}, 資料: {data}")
                    continue
            
            sorted_devices = sorted(devices, key=lambda d: d.sort_order)
            
            self.devices_db.truncate()
            
            for device in sorted_devices:
                device_data = device.to_dict()
                self.devices_db.insert(device_data)
            
            logger.info(f"✅ 資料庫已重新排序（{len(sorted_devices)} 台設備）")
        except Exception as e:
            logger.error(f"重新排序資料庫失敗: {e}")
    
    def save_device(self, device: Device, reorder: bool = False) -> bool:
        """
        儲存或更新設備
        
        Args:
            device: 設備對象
            reorder: 是否在保存後重新排序資料庫（默認 False）
        """
        try:
            device_data = device.to_dict()
            
            if self.is_known_device(device.serial):
                # 更新現有設備
                result = self.update_device(device.serial, device_data)
                # 如果需要重新排序
                if result and reorder:
                    self.reorder_devices()
                return result
            else:
                # 註冊新設備
                result = self.register_device(device.serial, device_data)
                # 如果需要重新排序
                if result and reorder:
                    self.reorder_devices()
                return result
                
        except Exception as e:
            logger.error(f"儲存設備失敗: {e}")
            logger.error(f"錯誤詳情:\n{traceback.format_exc()}")
            logger.error(f"設備序號: {device.serial}")
            return False
    
    def get_statistics(self) -> Dict:
        """取得統計資訊"""
        all_entries = self.registry_db.all()
        return {
            'total_devices': len(all_entries),
            'total_connections': sum(e.get('connection_count', 0) for e in all_entries),
        }
    
    def close(self):
        """關閉資料庫"""
        self.registry_db.close()
        self.devices_db.close()

