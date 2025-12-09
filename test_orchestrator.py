from pathlib import Path
import time
from core.game_server_manager import GameServerManager

# 假設 Board Game Server 在這個路徑 (請根據實際情況修改)
# 這裡指向使用者的 androidgame 專案路徑
BOARD_GAME_SERVER_PATH = Path("/Users/jinyaolin/androidgame/server")

def main():
    manager = GameServerManager(BOARD_GAME_SERVER_PATH)
    
    room_id = "default_room"
    
    print(f"啟動房間 {room_id} 的 Game Server...")
    port = manager.start_server(room_id)
    
    if port:
        print(f"✅ Server 啟動成功，Port: {port}")
        
        # 保持運行一段時間
        time.sleep(5)
        
        info = manager.get_server_info(room_id)
        print(f"Server 狀態: {info}")
        
        print("停止 Server...")
        manager.stop_server(room_id)
        print("✅ Server 已停止")
    else:
        print("❌ Server 啟動失敗")

if __name__ == "__main__":
    main()
