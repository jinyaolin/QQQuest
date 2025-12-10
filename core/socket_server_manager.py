"""
Socket Server 管理器
管理每個房間的 Node.js TCP/IP Socket Server
"""
import subprocess
import signal
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class SocketServerManager:
    """Socket Server 管理器"""
    
    def __init__(self):
        """初始化 Socket Server 管理器"""
        self.servers: Dict[str, subprocess.Popen] = {}  # room_id -> process
        self.server_info: Dict[str, dict] = {}  # room_id -> {ip, port, name}
        
        # 獲取 Node.js 腳本路徑
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        self.server_script = project_root / "servers" / "room_socket_server.js"
        
        # 檢查 Node.js 是否可用
        self._check_node_available()
        
        logger.info("Socket Server 管理器已初始化")
    
    def _check_node_available(self) -> bool:
        """檢查 Node.js 是否可用"""
        try:
            result = subprocess.run(
                ['node', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Node.js 可用: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Node.js 不可用: {e}")
            logger.warning("Socket Server 功能將無法使用，請安裝 Node.js")
            return False
        return False
    
    def start_server(
        self,
        room_id: str,
        room_name: str,
        socket_ip: str,
        socket_port: int
    ) -> Tuple[bool, str]:
        """
        啟動房間的 Socket Server
        
        Args:
            room_id: 房間 ID
            room_name: 房間名稱
            socket_ip: Socket Server IP 地址
            socket_port: Socket Server 端口
        
        Returns:
            (成功, 訊息)
        """
        try:
            # 檢查是否已經在運行
            if room_id in self.servers:
                process = self.servers[room_id]
                if process.poll() is None:  # 進程仍在運行
                    logger.warning(f"房間 {room_name} 的 Socket Server 已在運行")
                    return False, "Socket Server 已在運行"
                else:
                    # 進程已結束，清理
                    del self.servers[room_id]
                    if room_id in self.server_info:
                        del self.server_info[room_id]
            
            # 檢查腳本是否存在
            if not self.server_script.exists():
                error_msg = f"Socket Server 腳本不存在: {self.server_script}"
                logger.error(error_msg)
                return False, error_msg
            
            # 啟動 Node.js 進程
            cmd = [
                'node',
                str(self.server_script),
                room_id,
                room_name,
                socket_ip,
                str(socket_port)
            ]
            
            logger.info(f"正在啟動 Socket Server: {room_name} ({socket_ip}:{socket_port})")
            logger.debug(f"執行命令: {' '.join(cmd)}")
            
            # 啟動進程（不等待完成）
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.server_script.parent.parent
            )
            
            # 等待一下，檢查是否成功啟動
            import time
            time.sleep(0.5)
            
            if process.poll() is not None:
                # 進程已結束（可能啟動失敗）
                stdout, stderr = process.communicate()
                error_msg = f"Socket Server 啟動失敗: {stderr or stdout}"
                logger.error(error_msg)
                return False, error_msg
            
            # 保存進程和資訊
            self.servers[room_id] = process
            self.server_info[room_id] = {
                'ip': socket_ip,
                'port': socket_port,
                'name': room_name
            }
            
            logger.info(f"✅ Socket Server 已啟動: {room_name} ({socket_ip}:{socket_port})")
            return True, f"Socket Server 已啟動: {socket_ip}:{socket_port}"
        
        except Exception as e:
            error_msg = f"啟動 Socket Server 失敗: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def stop_server(self, room_id: str) -> Tuple[bool, str]:
        """
        停止房間的 Socket Server
        
        Args:
            room_id: 房間 ID
        
        Returns:
            (成功, 訊息)
        """
        try:
            if room_id not in self.servers:
                return False, "Socket Server 未運行"
            
            process = self.servers[room_id]
            
            # 檢查進程是否仍在運行
            if process.poll() is not None:
                # 進程已結束
                del self.servers[room_id]
                if room_id in self.server_info:
                    del self.server_info[room_id]
                return False, "Socket Server 未運行"
            
            # 發送 SIGTERM 信號
            process.terminate()
            
            # 等待進程結束（最多 5 秒）
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 強制終止
                logger.warning(f"Socket Server 未響應 SIGTERM，強制終止: {room_id}")
                process.kill()
                process.wait()
            
            # 清理
            del self.servers[room_id]
            if room_id in self.server_info:
                server_info = self.server_info[room_id]
                del self.server_info[room_id]
                logger.info(f"✅ Socket Server 已停止: {server_info['name']}")
                return True, f"Socket Server 已停止"
            else:
                logger.info(f"✅ Socket Server 已停止: {room_id}")
                return True, "Socket Server 已停止"
        
        except Exception as e:
            error_msg = f"停止 Socket Server 失敗: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def restart_server(
        self,
        room_id: str,
        room_name: str,
        socket_ip: str,
        socket_port: int
    ) -> Tuple[bool, str]:
        """
        重啟房間的 Socket Server
        
        Args:
            room_id: 房間 ID
            room_name: 房間名稱
            socket_ip: Socket Server IP 地址
            socket_port: Socket Server 端口
        
        Returns:
            (成功, 訊息)
        """
        # 先停止
        self.stop_server(room_id)
        
        # 再啟動
        return self.start_server(room_id, room_name, socket_ip, socket_port)
    
    def is_server_running(self, room_id: str) -> bool:
        """
        檢查房間的 Socket Server 是否在運行
        
        Args:
            room_id: 房間 ID
        
        Returns:
            是否在運行
        """
        if room_id not in self.servers:
            return False
        
        process = self.servers[room_id]
        return process.poll() is None
    
    def get_server_info(self, room_id: str) -> Optional[dict]:
        """
        獲取 Socket Server 資訊
        
        Args:
            room_id: 房間 ID
        
        Returns:
            Socket Server 資訊字典，不存在返回 None
        """
        return self.server_info.get(room_id)
    
    def stop_all_servers(self):
        """停止所有 Socket Server"""
        room_ids = list(self.servers.keys())
        for room_id in room_ids:
            self.stop_server(room_id)
        logger.info("所有 Socket Server 已停止")
    
    def cleanup(self):
        """清理資源（停止所有服務器）"""
        self.stop_all_servers()


# 全局實例
_socket_server_manager: Optional[SocketServerManager] = None


def get_socket_server_manager() -> SocketServerManager:
    """獲取 Socket Server 管理器實例（單例模式）"""
    global _socket_server_manager
    if _socket_server_manager is None:
        _socket_server_manager = SocketServerManager()
    return _socket_server_manager


