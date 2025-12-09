import subprocess
import os
import socket
import logging
from typing import Dict, Optional
from pathlib import Path
from config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

class GameServerManager:
    """管理 Node.js Game Server 的子進程"""
    
    def __init__(self, server_path: Path):
        self.server_path = server_path
        self.processes: Dict[str, subprocess.Popen] = {}  # room_id -> process
        self.ports: Dict[str, int] = {}  # room_id -> port
        
    def start_server(self, room_id: str) -> Optional[int]:
        """
        為房間啟動一個 Game Server
        Returns: 分配的 Port, 若失敗則返回 None
        """
        if room_id in self.processes:
            if self.processes[room_id].poll() is None:
                logger.info(f"房間 {room_id} 的 Server 已經在運行 (Port: {self.ports[room_id]})")
                return self.ports[room_id]
            else:
                logger.warning(f"房間 {room_id} 的 Server 已停止，重新啟動...")

        port = self._find_available_port()
        if not port:
            logger.error("無可用 Port")
            return None
            
        try:
            # 假設 server.js 位於指定路徑
            server_script = self.server_path / "server.js"
            if not server_script.exists():
                logger.error(f"找不到 Server 腳本: {server_script}")
                return None
                
            env = os.environ.copy()
            env["PORT"] = str(port)
            
            # 啟動 Node.js 進程
            # 注意: 這裡使用 Popen 以便在背景執行
            proc = subprocess.Popen(
                ["node", str(server_script)],
                env=env,
                cwd=str(self.server_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[room_id] = proc
            self.ports[room_id] = port
            
            logger.info(f"已啟動 Game Server (Room: {room_id}, Port: {port}, PID: {proc.pid})")
            return port
            
        except Exception as e:
            logger.error(f"啟動 Game Server 失敗: {e}")
            return None
            
    def stop_server(self, room_id: str) -> bool:
        """停止指定房間的 Server"""
        if room_id in self.processes:
            proc = self.processes[room_id]
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            
            del self.processes[room_id]
            if room_id in self.ports:
                del self.ports[room_id]
            
            logger.info(f"已停止 Game Server (Room: {room_id})")
            return True
        return False
        
    def get_server_info(self, room_id: str) -> Optional[Dict]:
        """取得 Server 資訊"""
        if room_id in self.ports:
            return {
                "port": self.ports[room_id],
                "pid": self.processes[room_id].pid,
                "status": "running" if self.processes[room_id].poll() is None else "stopped"
            }
        return None

    def _find_available_port(self, start_port: int = 3001, end_port: int = 3100) -> Optional[int]:
        """尋找可用 Port"""
        for port in range(start_port, end_port):
            if port in self.ports.values():
                continue
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
        return None
