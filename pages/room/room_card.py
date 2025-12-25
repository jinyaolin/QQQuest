"""
房間卡片渲染函數
拆分自 pages/2_🏠_房間管理.py
"""
import streamlit as st
import time as time_module

from core.room import Room
from config.constants import DeviceStatus, STATUS_ICONS
from utils.logger import get_logger

logger = get_logger(__name__)


def render_devices_in_room(devices, room):
    """在房間視圖中渲染設備卡片"""
    # 使用網格佈局（每行 2 個卡片）
    cols_per_row = 2
    for i in range(0, len(devices), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, device in enumerate(devices[i:i+cols_per_row]):
            with cols[j]:
                # 狀態圖示
                status_icon = STATUS_ICONS.get(device.status, "❓")

                # 卡片容器
                with st.container(border=True):
                    # 頂部：標題和選單按鈕
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"#### {status_icon} {device.display_name}")
                    with col2:
                        # 使用 popover 讓選單在按鈕正下方展開
                        with st.popover("⋮", use_container_width=False):
                            st.markdown("**操作選單**")

                            # 執行動作
                            if device.is_online:
                                if st.button("⚡ 執行動作", key=f"room_dev_action_{device.device_id}", use_container_width=True):
                                    # 關閉房間視圖，打開執行動作對話框
                                    # 保存房間信息到 session state，以便在對話框中使用
                                    st.session_state[f'execute_action_room_{device.device_id}'] = room.room_id
                                    st.session_state[f'show_room_view_{room.room_id}'] = False
                                    st.session_state[f'execute_action_on_{device.device_id}'] = True
                                    st.rerun()
                            else:
                                st.button("⚡ 執行動作", key=f"room_dev_action_{device.device_id}", use_container_width=True, disabled=True)
                                st.caption("（設備離線）")

                            # 監看設備
                            if device.is_online:
                                if st.button("📺 監看設備", key=f"room_dev_monitor_{device.device_id}", use_container_width=True):
                                    success, message = st.session_state.adb_manager.start_scrcpy(
                                        device.connection_string,
                                        window_title=f"{device.display_name} - {room.name}"
                                    )
                                    if success:
                                        st.success(f"✅ {message}")
                                    else:
                                        st.error(f"❌ {message}")
                                    time_module.sleep(0.5)

                            st.divider()

                            # 移出房間
                            if st.button("🚪 移出房間", key=f"room_dev_remove_{device.device_id}", use_container_width=True, type="secondary"):
                                success, msg = st.session_state.room_registry.remove_device_from_room(
                                    room.room_id,
                                    device.device_id
                                )
                                if success:
                                    st.success(f"✅ {msg}")
                                    time_module.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")

                    # 設備信息
                    st.caption(f"序號: {device.serial}")

                    if device.notes:
                        st.caption(f"備註: {device.notes}")

                    # 連線信息
                    if device.is_online:
                        st.success(f"🟢 在線 - {device.connection_string}")

                        # 獲取詳細狀態
                        device_status = st.session_state.adb_manager.get_device_status(device.connection_string)

                        if device_status:
                            col1, col2 = st.columns(2)

                            with col1:
                                if device_status.get('battery_level') is not None:
                                    battery = device_status['battery_level']
                                    st.metric("電量", f"{battery}%")

                                if device_status.get('temperature') is not None:
                                    temp = device_status['temperature']
                                    st.metric("溫度", f"{temp}°C")

                            with col2:
                                if device_status.get('is_awake') is not None:
                                    awake_status = "👁️ 清醒" if device_status['is_awake'] else "😴 休眠"
                                    st.caption(awake_status)

                                if device_status.get('uptime_seconds') is not None:
                                    uptime = device_status['uptime_seconds']
                                    hours = uptime // 3600
                                    minutes = (uptime % 3600) // 60
                                    st.caption(f"⏱️ 運行時間: {hours}h {minutes}m")
                    else:
                        st.error("🔴 離線")


def render_room_card(room: Room):
    """渲染房間卡片"""
    # 獲取房間內設備
    room_devices = st.session_state.room_registry.get_room_devices(
        room.room_id,
        st.session_state.device_registry
    )

    online_count = len([d for d in room_devices if d.status == DeviceStatus.ONLINE])
    offline_count = len([d for d in room_devices if d.status == DeviceStatus.OFFLINE])
    not_connected_count = len([d for d in room_devices if d.status == DeviceStatus.NOT_CONNECTED])

    # 卡片容器
    with st.container(border=True):
        # 頂部：標題和選單按鈕
        col1, col2 = st.columns([5, 1])
        with col1:
            # 可點擊的房間名稱（通過增加列寬度和減少每行卡片數量來顯示更多內容）
            if st.button(
                f"{room.display_name}",
                key=f"btn_room_name_{room.room_id}",
                use_container_width=True,
                type="secondary"
            ):
                st.session_state[f'show_room_view_{room.room_id}'] = True
                st.rerun()
        with col2:
            # 使用 popover 讓選單在按鈕正下方展開
            with st.popover("⋮", use_container_width=False):
                st.markdown("**操作選單**")

                # 執行動作
                if room.device_count > 0:
                    if st.button("⚡ 執行動作", key=f"btn_execute_action_room_{room.room_id}", use_container_width=True):
                        st.session_state[f'show_execute_action_room_{room.room_id}'] = True
                        st.rerun()
                else:
                    st.button("⚡ 執行動作", key=f"btn_execute_action_room_{room.room_id}", use_container_width=True, disabled=True)
                    st.caption("（房間內無設備）")

                # 管理設備
                if st.button("➕ 管理設備", key=f"btn_manage_devices_{room.room_id}", use_container_width=True):
                    st.session_state[f'show_manage_devices_{room.room_id}'] = True
                    st.rerun()

                # 重新連接設備
                if room.device_count > 0:
                    if st.button("🔌 重新連接", key=f"btn_reconnect_room_{room.room_id}", use_container_width=True):
                        st.session_state[f'show_reconnect_room_{room.room_id}'] = True
                        st.rerun()
                else:
                    st.button("🔌 重新連接", key=f"btn_reconnect_room_{room.room_id}", use_container_width=True, disabled=True)
                    st.caption("（房間內無設備）")

                # 重新啟動 Socket Server
                if room.socket_ip and room.socket_port:
                    # 檢查 Socket Server 狀態
                    is_running = False
                    if 'socket_server_manager' in st.session_state:
                        socket_manager = st.session_state.socket_server_manager
                        is_running = socket_manager.is_server_running(room.room_id)

                    status_text = "🟢 運行中" if is_running else "🔴 未運行"
                    if st.button(f"🔄 重啟 Socket Server ({status_text})", key=f"btn_restart_socket_{room.room_id}", use_container_width=True):
                        st.session_state[f'restart_socket_{room.room_id}'] = True
                        st.rerun()
                    st.caption(f"📡 {room.socket_ip}:{room.socket_port}")

                st.divider()

                # 編輯房間
                if st.button("✏️ 編輯房間", key=f"edit_{room.room_id}", use_container_width=True):
                    st.session_state[f'edit_room_{room.room_id}'] = True
                    st.rerun()

                # 刪除房間
                if st.button("🗑️ 刪除房間", key=f"delete_{room.room_id}", use_container_width=True, type="secondary"):
                    st.session_state[f'delete_room_{room.room_id}'] = True
                    st.rerun()

        # 房間描述
        if room.description:
            st.caption(room.description)

        # 房間統計
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("設備數量", room.capacity_text)

        with col2:
            st.metric("🟢 在線", online_count)

        with col3:
            st.metric("🟠 離線", offline_count)

        with col4:
            st.metric("⚫ 未連接", not_connected_count)

        # 容量警告
        if room.max_devices > 0 and room.device_count >= room.max_devices:
            st.warning("⚠️ 房間已滿")
