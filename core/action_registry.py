"""
動作註冊管理器
"""
from typing import List, Optional, Dict, Any
from tinydb import TinyDB, Query
from pathlib import Path
from core.action import Action, ActionType, ActionParamsValidator
from config.settings import DATA_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class ActionRegistry:
    """動作註冊管理器"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化動作註冊管理器
        
        Args:
            db_path: 資料庫路徑，預設為 DATA_DIR / "actions.json"
        """
        if db_path is None:
            db_path = DATA_DIR / "actions.json"
        
        self.db_path = db_path
        self.db = TinyDB(db_path)
        self.actions_table = self.db.table('actions')
        logger.info(f"動作註冊管理器已初始化，資料庫路徑: {db_path}")
    
    def create_action(
        self,
        name: str,
        action_type: ActionType,
        params: Dict[str, Any],
        description: Optional[str] = None
    ) -> Optional[Action]:
        """
        創建新動作
        
        Args:
            name: 動作名稱
            action_type: 動作類型
            params: 動作參數
            description: 動作說明
        
        Returns:
            Action 對象，失敗返回 None
        """
        try:
            # 驗證參數
            is_valid, error_msg = ActionParamsValidator.validate(action_type, params)
            if not is_valid:
                logger.error(f"參數驗證失敗: {error_msg}")
                return None
            
            # 創建動作
            action = Action(
                name=name,
                action_type=action_type,
                params=params,
                description=description
            )
            
            # 儲存到資料庫
            self.actions_table.insert(action.to_dict())
            logger.info(f"✅ 創建動作成功: {action.display_name} (ID: {action.action_id})")
            
            return action
        
        except Exception as e:
            logger.error(f"❌ 創建動作失敗: {e}")
            return None
    
    def get_action(self, action_id: str) -> Optional[Action]:
        """
        根據 ID 獲取動作
        
        Args:
            action_id: 動作 ID
        
        Returns:
            Action 對象，不存在返回 None
        """
        try:
            ActionQuery = Query()
            result = self.actions_table.get(ActionQuery.action_id == action_id)
            
            if result:
                return Action.from_dict(result)
            
            return None
        
        except Exception as e:
            logger.error(f"❌ 獲取動作失敗 (ID: {action_id}): {e}")
            return None
    
    def get_all_actions(self) -> List[Action]:
        """
        獲取所有動作
        
        Returns:
            Action 列表
        """
        try:
            results = self.actions_table.all()
            actions = [Action.from_dict(data) for data in results]
            logger.debug(f"獲取所有動作: {len(actions)} 個")
            return actions
        
        except Exception as e:
            logger.error(f"❌ 獲取所有動作失敗: {e}")
            return []
    
    def get_actions_by_type(self, action_type: ActionType) -> List[Action]:
        """
        根據類型獲取動作
        
        Args:
            action_type: 動作類型
        
        Returns:
            Action 列表
        """
        try:
            ActionQuery = Query()
            results = self.actions_table.search(ActionQuery.action_type == action_type.value)
            actions = [Action.from_dict(data) for data in results]
            logger.debug(f"獲取 {action_type.value} 類型動作: {len(actions)} 個")
            return actions
        
        except Exception as e:
            logger.error(f"❌ 獲取動作失敗 (類型: {action_type}): {e}")
            return []
    
    def update_action(self, action: Action) -> bool:
        """
        更新動作
        
        Args:
            action: Action 對象
        
        Returns:
            是否成功
        """
        try:
            # 驗證參數
            is_valid, error_msg = ActionParamsValidator.validate(action.action_type, action.params)
            if not is_valid:
                logger.error(f"參數驗證失敗: {error_msg}")
                return False
            
            # 更新時間戳
            from datetime import datetime
            action.updated_at = datetime.now()
            
            # 更新資料庫
            ActionQuery = Query()
            self.actions_table.update(
                action.to_dict(),
                ActionQuery.action_id == action.action_id
            )
            
            logger.info(f"✅ 更新動作成功: {action.display_name} (ID: {action.action_id})")
            return True
        
        except Exception as e:
            logger.error(f"❌ 更新動作失敗 (ID: {action.action_id}): {e}")
            return False
    
    def delete_action(self, action_id: str) -> bool:
        """
        刪除動作
        
        Args:
            action_id: 動作 ID
        
        Returns:
            是否成功
        """
        try:
            ActionQuery = Query()
            result = self.actions_table.remove(ActionQuery.action_id == action_id)
            
            if result:
                logger.info(f"✅ 刪除動作成功 (ID: {action_id})")
                return True
            else:
                logger.warning(f"⚠️ 動作不存在 (ID: {action_id})")
                return False
        
        except Exception as e:
            logger.error(f"❌ 刪除動作失敗 (ID: {action_id}): {e}")
            return False
    
    def search_actions(self, keyword: str) -> List[Action]:
        """
        搜索動作（根據名稱或說明）
        
        Args:
            keyword: 搜索關鍵字
        
        Returns:
            Action 列表
        """
        try:
            ActionQuery = Query()
            results = self.actions_table.search(
                (ActionQuery.name.search(keyword, flags=0)) |
                (ActionQuery.description.search(keyword, flags=0))
            )
            actions = [Action.from_dict(data) for data in results]
            logger.debug(f"搜索動作 (關鍵字: {keyword}): {len(actions)} 個")
            return actions
        
        except Exception as e:
            logger.error(f"❌ 搜索動作失敗 (關鍵字: {keyword}): {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取統計信息
        
        Returns:
            統計信息字典
        """
        try:
            all_actions = self.get_all_actions()
            
            stats = {
                "total_actions": len(all_actions),
                "total_executions": sum(a.execution_count for a in all_actions),
                "total_success": sum(a.success_count for a in all_actions),
                "total_failure": sum(a.failure_count for a in all_actions),
                "by_type": {}
            }
            
            # 按類型統計
            for action_type in ActionType:
                type_actions = [a for a in all_actions if a.action_type == action_type]
                stats["by_type"][action_type.value] = {
                    "count": len(type_actions),
                    "executions": sum(a.execution_count for a in type_actions),
                    "success": sum(a.success_count for a in type_actions),
                }
            
            # 計算整體成功率
            if stats["total_executions"] > 0:
                stats["overall_success_rate"] = (stats["total_success"] / stats["total_executions"]) * 100
            else:
                stats["overall_success_rate"] = 0.0
            
            return stats
        
        except Exception as e:
            logger.error(f"❌ 獲取統計信息失敗: {e}")
            return {}
    
    def duplicate_action(self, action_id: str, new_name: Optional[str] = None) -> Optional[Action]:
        """
        複製動作
        
        Args:
            action_id: 要複製的動作 ID
            new_name: 新動作名稱（可選）
        
        Returns:
            新的 Action 對象，失敗返回 None
        """
        try:
            # 獲取原動作
            original_action = self.get_action(action_id)
            if not original_action:
                logger.error(f"❌ 找不到動作 (ID: {action_id})")
                return None
            
            # 創建新動作
            new_action_name = new_name if new_name else f"{original_action.name} (副本)"
            new_action = self.create_action(
                name=new_action_name,
                action_type=original_action.action_type,
                params=original_action.params.copy(),
                description=original_action.description
            )
            
            if new_action:
                logger.info(f"✅ 複製動作成功: {new_action.display_name}")
            
            return new_action
        
        except Exception as e:
            logger.error(f"❌ 複製動作失敗: {e}")
            return None
    
    def close(self):
        """關閉資料庫連接"""
        self.db.close()
        logger.info("動作註冊管理器已關閉")




