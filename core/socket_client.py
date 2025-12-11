"""
Socket Client - 連接到房間的 Node.js Socket Server
"""
import socket
import json
import time
from typing import Optional, Tuple, List
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


class SocketClient:
    """Socket Client 類別，用於連接到房間的 Socket Server"""
    
    def __init__(self, socket_ip: str, socket_port: int, client_id: str = "Server"):
        """
        初始化 Socket Client
        
        Args:
            socket_ip: Socket Server IP 地址
            socket_port: Socket Server 端口
            client_id: 客戶端 ID (預設為 Server)
        """
        self.socket_ip = socket_ip
        self.socket_port = socket_port
        self.client_id = client_id
        self.socket: Optional[socket.socket] = None
        self.connected = False
    
    def connect(self, timeout: int = 5) -> Tuple[bool, str]:
        """
        連接到 Socket Server
        
        Args:
            timeout: 連接超時時間（秒）
        
        Returns:
            (成功, 訊息)
        """
        try:
            if self.connected and self.socket:
                return True, "已連接"
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((self.socket_ip, self.socket_port))
            self.connected = True
            
            logger.info(f"✅ 已連接到 Socket Server: {self.socket_ip}:{self.socket_port}")
            
            # 接收並消耗歡迎消息
            try:
                self.socket.settimeout(2) # 短暫超時等待歡迎消息
                welcome_data = b''
                while True:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    welcome_data += chunk
                    if b'\n' in welcome_data:
                        break
                
                if welcome_data:
                    logger.debug(f"收到歡迎消息: {welcome_data.decode('utf-8').strip()}")
            except socket.timeout:
                pass # 忽略讀取超時，可能是服務器沒發送或延遲
            except Exception as e:
                logger.warning(f"讀取歡迎消息失敗: {e}")
            
            # 如果有 client_id，自動登錄
            if self.client_id:
                return self.login(self.client_id)
                
            return True, "連接成功"
        
        except socket.timeout:
            error_msg = f"連接超時: {self.socket_ip}:{self.socket_port}"
            logger.error(error_msg)
            return False, error_msg
        except ConnectionRefusedError:
            error_msg = f"連接被拒絕: {self.socket_ip}:{self.socket_port}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"連接失敗: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def login(self, device_id: str) -> Tuple[bool, str]:
        """
        登錄到 Socket Server
        
        Args:
            device_id: 設備 ID
            
        Returns:
            (成功, 訊息)
        """
        # 注意：我們使用更底層的 sendall 和 recv 來避免 self.send_command 中的遞歸連接問題
        # 並且 send_command 設計為通用命令，這裡我們需要特定的處理流程
        
        try:
            if not self.connected or not self.socket:
                return False, "未連接"
                
            message = {
                'type': 'login',
                'device_id': device_id
            }
            
            message_str = json.dumps(message) + '\n'
            self.socket.sendall(message_str.encode('utf-8'))
            logger.debug(f"發送登錄請求: {device_id}")
            
            # 接收登錄響應
            self.socket.settimeout(5)
            response_data = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b'\n' in response_data:
                    break
            
            if response_data:
                response_str = response_data.decode('utf-8').strip()
                if '\n' in response_str:
                    response_str = response_str.split('\n')[0]
                    
                response = json.loads(response_str)
                if response.get('success'):
                    logger.info(f"✅ 登錄成功: {device_id}")
                    return True, "登錄成功"
                else:
                    return False, response.get('message', '登錄失敗')
            else:
                return False, "未收到登錄響應"
                
        except Exception as e:
            logger.error(f"登錄異常: {e}")
            return False, f"登錄異常: {str(e)}"
            
    def disconnect(self):
        """斷開連接"""
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            self.connected = False
            logger.info("Socket Client 已斷開連接")
        except Exception as e:
            logger.error(f"斷開連接失敗: {e}")
    
    def send_command(self, command: str, data: Optional[dict] = None) -> Tuple[bool, dict]:
        """
        發送命令到 Socket Server
        
        Args:
            command: 命令類型（如 'ping', 'echo', 'command'）
            data: 額外的數據（可選）
        
        Returns:
            (成功, 響應字典)
        """
        try:
            if not self.connected or not self.socket:
                success, msg = self.connect()
                if not success:
                    return False, {'type': 'error', 'message': msg}
            
            # 構建消息
            message = {
                'type': command,
                'data': data if data else {}
            }
            
            # 發送消息（JSON 格式，以換行符結尾）
            message_str = json.dumps(message) + '\n'
            self.socket.sendall(message_str.encode('utf-8'))
            
            logger.debug(f"發送命令: {command}")
            
            # 接收響應（設置超時）
            self.socket.settimeout(5)
            response_data = b''
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                    if b'\n' in response_data:
                        break
                except socket.timeout:
                    break
            
            if response_data:
                response_str = response_data.decode('utf-8').strip()
                # 取第一行（JSON 消息以換行符分隔）
                if '\n' in response_str:
                    response_str = response_str.split('\n')[0]
                
                try:
                    response = json.loads(response_str)
                    logger.debug(f"收到響應: {response}")
                    return True, response
                except json.JSONDecodeError:
                    return False, {'type': 'error', 'message': f'無效的響應格式: {response_str}'}
            else:
                return False, {'type': 'error', 'message': '未收到響應'}
        
        except socket.timeout:
            return False, {'type': 'error', 'message': '接收響應超時'}
        except Exception as e:
            error_msg = f"發送命令失敗: {str(e)}"
            logger.error(error_msg)
            return False, {'type': 'error', 'message': error_msg}
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


def read_socket_server_log(room_id: str, socket_port: int, lines: int = 100) -> List[str]:
    """
    讀取 Socket Server 的日誌文件
    
    Args:
        room_id: 房間 ID
        socket_port: Socket Server 端口
        lines: 讀取的行數（從文件末尾開始）
    
    Returns:
        日誌行列表
    """
    try:
        # 日誌文件路徑
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        log_file = project_root / "logs" / "socket_servers" / f"room_{room_id}_{socket_port}.log"
        
        if not log_file.exists():
            return []
        
        # 讀取文件的最後 N 行
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    
    except Exception as e:
        logger.error(f"讀取日誌文件失敗: {e}")
        return []


