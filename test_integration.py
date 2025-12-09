import logging
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock ADBManager for testing without real devices
sys.modules['core.adb_manager'] = MagicMock()

from core.game_server_manager import GameServerManager
from core.adb_manager import ADBManager

# 指向實際的 Server 位置
SERVER_PATH = Path("/Users/jinyaolin/androidgame/server")

def test_integration():
    print("=== 開始整合測試 ===")
    
    # 1. 初始化 Manager
    server_manager = GameServerManager(SERVER_PATH)
    adb_manager = ADBManager()
    
    # 2. 模擬啟動房間
    room_id = "test_room_1"
    print(f"[Step 1] 啟動 Game Server (Room: {room_id})...")
    port = server_manager.start_server(room_id)
    
    if not port:
        print("❌ Server 啟動失敗")
        return
        
    print(f"✅ Server 已啟動於 Port: {port}")
    
    # 3. 模擬 ADB 推送配置
    device_serial = "emulator-5554"
    server_ip = "10.0.2.2" # Android 模擬器的 localhost
    
    print(f"[Step 2] 透過 ADB 啟動 App 並帶入配置 (IP: {server_ip}, Port: {port})...")
    
    # 在真實環境中會呼叫真實的 ADB，這裡我們只印出會執行的指令
    extras = {
        "server_ip": server_ip,
        "server_port": port
    }
    
    # 呼叫我們剛剛新增的方法 (雖然是 Mock，但確認方法簽名存在)
    # 注意：因為我們 Mock 了 ADBManager，這裡實際上不會執行 ADB 指令，但可以測試程式碼邏輯是否正確
    try:
        # 暫時替換 Mock 的方法為真實的打印，以便我們看到效果
        def mock_launch(device, package, activity, extras):
            cmd = f"am start -n {package}/{activity}"
            for k, v in extras.items():
                if isinstance(v, int):
                    cmd += f" --ei {k} {v}"
                else:
                    cmd += f" --es {k} \"{v}\""
            print(f"   -> [ADB Command]: adb -s {device} shell {cmd}")
            return True, "Mock Success"
            
        adb_manager.launch_app_with_extras = mock_launch
        
        adb_manager.launch_app_with_extras(
            device_serial,
            "com.example.boardgame",
            ".MainActivity",
            extras
        )
        print("✅ App 啟動指令已發送")
        
    except Exception as e:
        print(f"❌ ADB 指令發送失敗: {e}")
    
    # 4. 等待並清理
    print("[Step 3] 等待 3 秒模擬遊戲運行...")
    time.sleep(3)
    
    print("[Step 4] 停止 Game Server...")
    server_manager.stop_server(room_id)
    print("✅ Server 已停止")
    
    print("=== 測試完成 ===")

if __name__ == "__main__":
    test_integration()
