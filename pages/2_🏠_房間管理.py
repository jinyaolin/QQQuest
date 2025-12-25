"""
房間管理頁面
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import time

from utils.logger import get_logger

# 導入房間管理模塊
from pages.room import (
    add_room_dialog,
    edit_room_dialog,
    delete_room_dialog,
    manage_devices_dialog,
    execute_action_on_room_dialog,
    reconnect_room_devices_dialog,
    execute_device_action_dialog,
    room_view_dialog,
    render_room_card
)

logger = get_logger(__name__)

# 頁面配置
st.set_page_config(
    page_title="房間管理 - QQQuest",
    page_icon="🏠",
    layout="wide"
)

# 自定義 CSS 樣式
st.markdown("""
    <style>
    /* 隱藏標題旁的錨點鏈接圖標 */
    a.st-emotion-cache-yinll1,
    a[class*="st-emotion-cache"][href^="#"] {
        display: none !important;
    }

    /* 統一房間卡片和設備卡片高度和對齊 */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
        height: 100%;
        min-height: 320px;
    }

    /* 確保卡片內容填充整個容器 */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div {
        height: 100%;
        display: flex;
        flex-direction: column;
    }

    /* 讓卡片在 grid 中均勻分布 */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
    }

    /* 房間卡片中的按鈕允許換行，避免長名稱被截斷 */
    [data-testid="stVerticalBlockBorderWrapper"] button[data-testid="stBaseButton-secondary"] {
        white-space: normal !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        height: auto !important;
        min-height: 2.5rem !important;
        line-height: 1.4 !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] button[data-testid="stBaseButton-secondary"] > div {
        white-space: normal !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    </style>
""", unsafe_allow_html=True)

# 自動刷新（每 5 秒）- 但在有對話框時暫停
dialog_keys = [key for key in st.session_state.keys() if key.startswith(('add_room', 'edit_room_', 'delete_room_', 'show_manage_devices_', 'show_execute_action_room_', 'show_room_view_'))]
dialog_states = {key: st.session_state.get(key, False) for key in dialog_keys}
has_dialog_open = any(dialog_states.values())

# 只在沒有對話框時自動刷新
if not has_dialog_open:
    count = st_autorefresh(interval=5000, key="room_refresh")

# 初始化系統
from utils.init import init_all, ensure_room_registry, ensure_socket_server_manager

if not init_all():
    st.stop()

# 確保房間註冊管理器已初始化（雙重檢查）
ensure_room_registry()

# 確保 Socket Server 管理器已初始化
ensure_socket_server_manager()

# Session state 初始化
if 'show_add_room_dialog' not in st.session_state:
    st.session_state.show_add_room_dialog = False


def main():
    """主函式"""
    st.title("🏠 房間管理")
    st.caption("建立和管理房間，批量控制多台設備")

    # 頂部操作列
    col1, col2 = st.columns([5, 1])

    with col1:
        st.caption("💡 提示：點擊「新增房間」創建房間，然後在房間中加入設備")

    with col2:
        if st.button("➕ 新增房間", use_container_width=True, type="primary"):
            for key in ['new_room_name', 'new_room_description', 'new_room_max_devices',
                       'new_room_socket_ip', 'new_room_socket_port']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.show_add_room_dialog = True
            st.rerun()

    st.markdown("---")

    # 獲取所有房間
    rooms = st.session_state.room_registry.get_all_rooms()

    # 顯示統計
    if rooms:
        stats = st.session_state.room_registry.get_statistics()
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("📊 房間總數", stats.get('total_rooms', 0))
        col2.metric("📱 總設備數", stats.get('total_devices', 0))
        col3.metric("🏠 有設備的房間", stats.get('rooms_with_devices', 0))
        col4.metric("📭 空房間", stats.get('empty_rooms', 0))

        st.markdown("---")

    # 顯示房間列表
    if not rooms:
        st.info("🏠 還沒有任何房間，點擊「新增房間」開始創建")
    else:
        # 使用網格佈局（每行 2 個卡片，增加卡片寬度以顯示更多內容）
        cols_per_row = 2
        for i in range(0, len(rooms), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, room in enumerate(rooms[i:i+cols_per_row]):
                with cols[j]:
                    render_room_card(room)

    # 處理對話框
    if st.session_state.get('show_add_room_dialog'):
        add_room_dialog()

    # 處理設備執行動作對話框（房間視圖中觸發）
    all_devices = st.session_state.device_registry.get_all_devices()
    for device in all_devices:
        if st.session_state.get(f'execute_action_on_{device.device_id}'):
            # 獲取房間信息（如果從房間視圖觸發）
            device_room = None
            room_id = st.session_state.get(f'execute_action_room_{device.device_id}')
            if room_id:
                device_room = st.session_state.room_registry.get_room(room_id)
            else:
                # 如果沒有保存的房間 ID，嘗試查找設備所屬的房間
                device_room = st.session_state.room_registry.get_device_room(device.device_id)
            execute_device_action_dialog(device, device_room)

    # 處理房間對話框
    for room in rooms:
        if st.session_state.get(f'show_room_view_{room.room_id}'):
            room_view_dialog(room)

        if st.session_state.get(f'edit_room_{room.room_id}'):
            edit_room_dialog(room)

        if st.session_state.get(f'delete_room_{room.room_id}'):
            delete_room_dialog(room)

        if st.session_state.get(f'show_manage_devices_{room.room_id}'):
            manage_devices_dialog(room)

        if st.session_state.get(f'show_execute_action_room_{room.room_id}'):
            execute_action_on_room_dialog(room)

        if st.session_state.get(f'show_reconnect_room_{room.room_id}'):
            reconnect_room_devices_dialog(room)

        # 處理重新啟動 Socket Server
        if st.session_state.get(f'restart_socket_{room.room_id}'):
            if room.socket_ip and room.socket_port:
                if 'socket_server_manager' in st.session_state:
                    socket_manager = st.session_state.socket_server_manager
                    with st.spinner("正在重啟 Socket Server..."):
                        success, msg = socket_manager.restart_server(
                            room.room_id,
                            room.name,
                            room.socket_ip,
                            room.socket_port
                        )
                        if success:
                            st.success(f"✅ Socket Server 已重啟: {room.socket_ip}:{room.socket_port}")
                            logger.info(f"✅ 重啟 Socket Server 成功: {room.name} ({room.socket_ip}:{room.socket_port})")
                        else:
                            st.error(f"❌ Socket Server 重啟失敗: {msg}")
                            logger.error(f"❌ 重啟 Socket Server 失敗: {room.name} - {msg}")
                        time.sleep(1)
                else:
                    st.error("❌ Socket Server 管理器未初始化")
                    time.sleep(1)
            else:
                st.warning("⚠️ 此房間未配置 Socket Server")
                time.sleep(1)

            st.session_state[f'restart_socket_{room.room_id}'] = False
            st.rerun()


if __name__ == "__main__":
    main()
