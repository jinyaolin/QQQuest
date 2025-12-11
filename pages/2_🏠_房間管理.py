"""
房間管理頁面
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from typing import Optional
import time
import json
from datetime import datetime
from core.room import Room
from core.room_registry import RoomRegistry
from config.constants import DeviceStatus, STATUS_ICONS
from utils.logger import get_logger

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


@st.dialog("➕ 新增房間", width="large")
def add_room_dialog():
    """新增房間對話框"""
    # 隱藏對話框右上角的關閉按鈕
    st.markdown("""
        <style>
        /* 隱藏對話框的關閉按鈕 - 使用多種選擇器確保覆蓋 */
        button[kind="header"] {
            display: none !important;
        }
        
        button[aria-label="Close"] {
            display: none !important;
        }
        
        div[data-testid="stDialog"] button[kind="header"] {
            display: none !important;
        }
        
        /* 針對可能的內部類名 */
        button.st-emotion-cache-ue6h4q,
        button.st-emotion-cache-7oyrr6 {
            display: none !important;
        }
        
        /* 通過屬性選擇器 */
        button[data-baseweb="button"][kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader("📝 基本資訊")
    
    # 房間名稱
    name = st.text_input(
        "房間名稱 *",
        placeholder="例如：訓練室 A",
        help="為房間取一個容易識別的名稱",
        key="new_room_name"
    )
    
    # 房間描述
    description = st.text_area(
        "房間說明（選填）",
        placeholder="描述這個房間的用途...",
        height=80,
        key="new_room_description"
    )
    
    # 最大設備數量
    max_devices = st.number_input(
        "最大設備數量",
        min_value=0,
        max_value=100,
        value=0,
        help="0 表示無限制",
        key="new_room_max_devices"
    )
    
    if max_devices == 0:
        st.caption("💡 設為 0 表示此房間可容納無限數量的設備")
    else:
        st.caption(f"💡 此房間最多可容納 {max_devices} 台設備")
    
    st.markdown("---")
    
    # 按鈕
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 保存", type="primary", use_container_width=True, key="add_room_save"):
            # 驗證必填欄位
            if not name:
                st.error("❌ 請輸入房間名稱")
                return
            
            # 創建房間
            room = st.session_state.room_registry.create_room(
                name=name,
                description=description if description else None,
                max_devices=max_devices,
                socket_ip=socket_ip if socket_ip else None,
                socket_port=socket_port if socket_ip else None
            )
            
            if room:
                st.success(f"✅ 房間已創建：{room.display_name}")
                logger.info(f"✅ 創建房間成功: {room.display_name}")
                
                # 如果配置了 Socket Server，自動啟動
                if room.socket_ip and room.socket_port:
                    if 'socket_server_manager' in st.session_state:
                        socket_manager = st.session_state.socket_server_manager
                        success, msg = socket_manager.start_server(
                            room.room_id,
                            room.name,
                            room.socket_ip,
                            room.socket_port
                        )
                        if success:
                            st.info(f"📡 Socket Server 已啟動: {room.socket_ip}:{room.socket_port}")
                        else:
                            st.warning(f"⚠️ Socket Server 啟動失敗: {msg}")
                
                st.session_state.show_add_room_dialog = False
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 創建房間失敗（可能名稱已存在）")
    
    with col2:
        if st.button("❌ 取消", use_container_width=True, key="add_room_cancel"):
            st.session_state.show_add_room_dialog = False
            st.rerun()


@st.dialog("✏️ 編輯房間", width="large")
def edit_room_dialog(room: Room):
    """編輯房間對話框"""
    from core.room import Room, RoomParameter, RoomParameterType
    
    # 初始化緩衝區（如果尚未存在）
    buffer_key = f'room_buffer_{room.room_id}'
    if buffer_key not in st.session_state:
        # 使用 model_copy 創建副本，確保不直接修改原始對象（直到保存）
        st.session_state[buffer_key] = room.model_copy(deep=True)
    
    # 使用緩衝區對象進行所有操作
    room_buffer = st.session_state[buffer_key]
    
    # 隱藏對話框右上角的關閉按鈕
    st.markdown("""
        <style>
        button[kind="header"] { display: none !important; }
        button[aria-label="Close"] { display: none !important; }
        div[data-testid="stDialog"] button[kind="header"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------
    # 參數編輯子視圖
    # ---------------------------
    if f'editing_param_{room.room_id}' in st.session_state:
        param_idx = st.session_state[f'editing_param_{room.room_id}']
        
        # 標題
        if param_idx == -1:
            st.subheader("➕ 新增參數")
            # 初始化新參數（如果是第一次進入此狀態）
            if f'temp_param_{room.room_id}' not in st.session_state:
                st.session_state[f'temp_param_{room.room_id}'] = RoomParameter(
                    name="new_param",
                    value_type=RoomParameterType.STRING,
                    is_global=True,
                    global_value=""
                )
            current_param = st.session_state[f'temp_param_{room.room_id}']
        else:
            # 編輯現有參數 - 從 buffer 取值
            # 注意：這裡我們操作的是 room 對象中的引用，或者我們應該 clone 一份？
            # 為了避免未保存的修改影響原對象，我們應該 clone。
            # 但 Pydantic model copy 比較簡單。
            if f'temp_param_{room.room_id}' not in st.session_state:
                st.session_state[f'temp_param_{room.room_id}'] = room_buffer.parameters[param_idx].model_copy(deep=True)
            
            current_param = st.session_state[f'temp_param_{room.room_id}']
            st.subheader(f"✏️ 編輯參數: {current_param.name}")

        st.caption("設定傳遞給 Android 應用的 Intent 參數")
        st.markdown("---")

        # 編輯表單
        p_name = st.text_input("參數名稱", value=current_param.name, key=f"p_name_{room.room_id}")
        
        # 類型選擇
        type_options = [t.value for t in RoomParameterType]
        try:
            type_index = type_options.index(current_param.value_type)
        except ValueError:
            type_index = 0
            
        p_type_str = st.selectbox(
            "參數類型", 
            type_options, 
            index=type_index,
            key=f"p_type_{room.room_id}"
        )
        p_type = RoomParameterType(p_type_str)
        
        is_global = st.checkbox("設為全域參數 (所有設備使用相同值)", value=current_param.is_global, key=f"p_global_{room.room_id}")
        
        st.markdown("---")
        st.caption("參數值設定")
        
        # 輔助函數：根據類型渲染輸入框
        def render_input(label, current_value, key_suffix):
            k = f"val_{key_suffix}_{room.room_id}"
            
            if p_type == RoomParameterType.BOOLEAN:
                return st.checkbox(label, value=bool(current_value) if current_value is not None else False, key=k)
            elif p_type in [RoomParameterType.INTEGER, RoomParameterType.LONG]:
                return st.number_input(label, value=int(current_value) if current_value is not None else 0, key=k, step=1)
            elif p_type == RoomParameterType.FLOAT:
                return st.number_input(label, value=float(current_value) if current_value is not None else 0.0, key=k, format="%f")
            else:
                return st.text_input(label, value=str(current_value) if current_value is not None else "", key=k)

        new_global_value = current_param.global_value
        new_device_values = current_param.device_values.copy()

        if is_global:
            new_global_value = render_input("全域值", current_param.global_value, "global")
        else:
            st.info("請為房間內的設備設定參數值")
            # 獲取房間內設備
            registry_devices = st.session_state.device_registry.get_all_devices()
            room_devices = [d for d in registry_devices if d.device_id in room_buffer.device_ids]
            
            if not room_devices:
                st.warning("此房間內沒有設備")
            
            for dev in room_devices:
                dev_val = current_param.device_values.get(dev.device_id)
                new_val = render_input(f"{dev.display_name} ({dev.ip})", dev_val, f"dev_{dev.device_id}")
                new_device_values[dev.device_id] = new_val

        st.markdown("---")
        
        # 同步功能區塊
        st.markdown("##### 📤 即時同步")
        sync_col1, sync_col2 = st.columns([3, 1])
        with sync_col1:
            st.caption("將當前參數設定直接發送給 Node.js Server（無需保存）")
        with sync_col2:
            if st.button("🚀 發送", key=f"sync_param_{room.room_id}", help="發送當前參數至 Socket Server"):
                # 構建臨時參數對象用於發送
                live_param = current_param.model_copy(deep=True)
                live_param.name = p_name
                live_param.value_type = p_type
                live_param.is_global = is_global
                if is_global:
                    live_param.global_value = new_global_value
                    live_param.device_values = {}
                else:
                    live_param.global_value = None
                    live_param.device_values = new_device_values
                
                # 檢查 Socket Server 狀態 (使用原始 room 配置或 buffer? 通常是用已啟動的配置)
                # 我們應該檢查 room.socket_ip (已保存的) 是否有運行的服務器
                # 如果用戶改了 IP 但沒保存重啟，這裡發送會失敗，這是預期的。
                if room.socket_ip and room.socket_port:
                    from core.socket_client import SocketClient

                    try:
                        with SocketClient(room.socket_ip, room.socket_port) as client:
                            # 構建 payload
                            command_type = "send_params" # 重用協議，或者單獨定義 "update_param"?
                            # 用戶請求是 "send parameters"，可以是一個 list 包含單個 param
                            data = [live_param.model_dump()]
                            
                            success, response = client.send_command(command_type, data)
                            if success:
                                st.toast(f"✅ 參數 {live_param.name} 發送成功!", icon="🚀")
                            else:
                                st.error(f"❌ 發送失敗: {response.get('message', '未知錯誤')}")
                    except Exception as e:
                        st.error(f"❌ 連接失敗: {str(e)}")
                else:
                    st.warning("⚠️ 此房間尚未配置或啟動 Socket Server")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("確認", type="primary", use_container_width=True, key=f"save_param_{room.room_id}"):
                # 更新 temp param
                current_param.name = p_name
                current_param.value_type = p_type
                current_param.is_global = is_global
                if is_global:
                    current_param.global_value = new_global_value
                    current_param.device_values = {}
                else:
                    current_param.global_value = None
                    current_param.device_values = new_device_values
                
                # 寫回 room_buffer 對象
                if param_idx == -1:
                    room_buffer.parameters.append(current_param)
                else:
                    room_buffer.parameters[param_idx] = current_param
                
                # 清理 state 並返回
                del st.session_state[f'editing_param_{room.room_id}']
                del st.session_state[f'temp_param_{room.room_id}']
                st.rerun()
        
        with col_b:
            if st.button("取消", use_container_width=True, key=f"cancel_param_{room.room_id}"):
                del st.session_state[f'editing_param_{room.room_id}']
                del st.session_state[f'temp_param_{room.room_id}']
                st.rerun()
        
        # 結束子視圖渲染
        return

    # ---------------------------
    # 主視圖：房間編輯
    # ---------------------------
    
    st.caption(f"房間 ID: {room_buffer.room_id}")
    st.markdown("---")
    
    st.subheader("📝 基本資訊")
    
    # 房間名稱
    name_key = f"edit_room_name_{room.room_id}"
    name = st.text_input(
        "房間名稱 *",
        value=room_buffer.name,
        help="為房間取一個容易識別的名稱",
        key=name_key
    )
    
    # 房間描述
    desc_key = f"edit_room_description_{room.room_id}"
    description = st.text_area(
        "房間說明（選填）",
        value=room_buffer.description if room_buffer.description else "",
        height=80,
        key=desc_key
    )
    
    # 最大設備數量
    max_dev_key = f"edit_room_max_devices_{room.room_id}"
    max_devices = st.number_input(
        "最大設備數量",
        min_value=0,
        max_value=100,
        value=room_buffer.max_devices,
        help="0 表示無限制",
        key=max_dev_key
    )
    
    # ... 容量提示 ...
    if max_devices == 0:
        st.caption("💡 設為 0 表示此房間可容納無限數量的設備")
    else:
        st.caption(f"💡 此房間最多可容納 {max_devices} 台設備")
        if room_buffer.device_count > max_devices:
            st.warning(f"⚠️ 當前房間有 {room_buffer.device_count} 台設備，超過新設定的上限！")
    
    st.markdown("---")
    st.subheader("🔌 Socket Server 設定（選填）")
    
    col1, col2 = st.columns(2)
    with col1:
        ip_key = f"edit_room_socket_ip_{room.room_id}"
        socket_ip = st.text_input(
            "Socket Server IP",
            value=room_buffer.socket_ip if room_buffer.socket_ip else "",
            placeholder="0.0.0.0 或 127.0.0.1",
            key=ip_key
        )
    with col2:
        port_key = f"edit_room_socket_port_{room.room_id}"
        socket_port = st.number_input(
            "Socket Server Port",
            min_value=1,
            max_value=65535,
            value=room_buffer.socket_port if room_buffer.socket_port else 3000,
            key=port_key
        )
    
    if socket_ip:
        st.info(f"📡 Socket Server 將在啟動時監聽 {socket_ip}:{socket_port}")
    else:
        st.caption("💡 留空 IP 地址則不會啟動 Socket Server")
    
    st.markdown("---")
    
    # --- 房間參數設定 ---
    st.subheader("⚙️ 房間參數設定")
    
    if not room_buffer.parameters:
        st.info("尚未設定任何參數")
    else:
        for i, param in enumerate(room_buffer.parameters):
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 2, 3, 2])
                with c1:
                    st.markdown(f"**{param.name}**")
                    st.caption(f"`{param.value_type}`")
                with c2:
                    st.markdown("🌐 全域" if param.is_global else "📱 個別設備")
                with c3:
                    if param.is_global:
                        st.code(str(param.global_value), language="text")
                    else:
                        st.caption(f"已設定 {len(param.device_values)} 台設備")
                with c4:
                    col_edit, col_del = st.columns(2)
                    with col_edit:
                        def on_edit_click(idx=i):
                            # 保存當前場景狀態到 buffer
                            room_buffer.name = st.session_state[name_key]
                            room_buffer.description = st.session_state[desc_key]
                            room_buffer.max_devices = st.session_state[max_dev_key]
                            room_buffer.socket_ip = st.session_state[ip_key]
                            room_buffer.socket_port = st.session_state[port_key]
                            st.session_state[f'editing_param_{room.room_id}'] = idx
                            
                        st.button("✏️", key=f"edit_param_{room.room_id}_{i}", on_click=on_edit_click)
                    with col_del:
                        if st.button("🗑️", key=f"del_param_{room.room_id}_{i}"):
                            room_buffer.parameters.pop(i)
                            st.rerun()
            st.markdown("---")

    # 新增參數按鈕
    def on_add_click():
        # 保存當前場景狀態
        room_buffer.name = st.session_state[name_key]
        room_buffer.description = st.session_state[desc_key]
        room_buffer.max_devices = st.session_state[max_dev_key]
        room_buffer.socket_ip = st.session_state[ip_key]
        room_buffer.socket_port = st.session_state[port_key]
        st.session_state[f'editing_param_{room.room_id}'] = -1
        
    st.button("➕ 新增參數", key=f"add_param_btn_{room.room_id}", on_click=on_add_click)
    
    st.markdown("---")
    
    # 底部按鈕
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存", type="primary", use_container_width=True, key=f"edit_room_save_{room.room_id}"):
            if not name:
                st.error("❌ 請輸入房間名稱")
            else:
                # 檢查名稱重複
                if name != room_buffer.name:
                    existing = st.session_state.room_registry.get_room_by_name(name)
                    # 確保不與他人重複（排除自己）
                    if existing and existing.room_id != room.room_id:
                        st.error("❌ 房間名稱已存在")
                        return 
                
                # 這裡的賦值其實已經在 widget binding 中完成了嗎？
                # 不，st.text_input(value=room.name) 只是初始值。
                # 我們需要手動獲取最新值，或者信賴 session_state 綁定
                # 這裡直接用 name 變數即可 (它包含最新輸入)
                
                old_socket_ip = room_buffer.socket_ip
                old_socket_port = room_buffer.socket_port
                
                room_buffer.name = name
                room_buffer.description = description if description else None
                room_buffer.max_devices = max_devices
                room_buffer.socket_ip = socket_ip if socket_ip else None
                room_buffer.socket_port = socket_port if socket_ip else None
                
                if st.session_state.room_registry.update_room(room_buffer):
                    st.success(f"✅ 房間已更新")
                    # Socket Server 重啟邏輯 (與之前相同)
                    # ... 略 ...
                    if (old_socket_ip != room_buffer.socket_ip or old_socket_port != room_buffer.socket_port):
                         if 'socket_server_manager' in st.session_state:
                            sm = st.session_state.socket_server_manager
                            if old_socket_ip: sm.stop_server(room.room_id)
                            if room_buffer.socket_ip: 
                                sm.start_server(room.room_id, room_buffer.name, room_buffer.socket_ip, room_buffer.socket_port)

                    st.session_state[f'edit_room_{room.room_id}'] = False
                    # 清除 buffer
                    if buffer_key in st.session_state:
                        del st.session_state[buffer_key]
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ 更新失敗")

    with col2:
        if st.button("❌ 取消", use_container_width=True, key=f"edit_room_cancel_{room.room_id}"):
            st.session_state[f'edit_room_{room.room_id}'] = False
            # 清除 buffer
            if buffer_key in st.session_state:
                del st.session_state[buffer_key]
            st.rerun()


@st.dialog("🗑️ 確認刪除房間", width="small")
def delete_room_dialog(room: Room):
    """刪除房間確認對話框"""
    # 隱藏對話框右上角的關閉按鈕
    st.markdown("""
        <style>
        /* 隱藏對話框的關閉按鈕 - 使用多種選擇器確保覆蓋 */
        button[kind="header"] {
            display: none !important;
        }
        
        button[aria-label="Close"] {
            display: none !important;
        }
        
        div[data-testid="stDialog"] button[kind="header"] {
            display: none !important;
        }
        
        /* 針對可能的內部類名 */
        button.st-emotion-cache-ue6h4q,
        button.st-emotion-cache-7oyrr6 {
            display: none !important;
        }
        
        /* 通過屬性選擇器 */
        button[data-baseweb="button"][kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.warning(f"確定要刪除房間 **{room.display_name}** 嗎？")
    
    if room.device_count > 0:
        st.error(f"⚠️ 此房間內有 {room.device_count} 台設備")
        st.info("💡 刪除房間後，設備將不再屬於任何房間（但不會被刪除）")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ 確定刪除", type="primary", use_container_width=True):
            # 停止 Socket Server（如果存在）
            if room.socket_ip and room.socket_port:
                if 'socket_server_manager' in st.session_state:
                    socket_manager = st.session_state.socket_server_manager
                    socket_manager.stop_server(room.room_id)
                    logger.info(f"🛑 已停止 Socket Server: {room.name}")
            
            # 刪除房間
            if st.session_state.room_registry.delete_room(room.room_id):
                st.success("✅ 房間已刪除")
                logger.info(f"🗑️ 刪除房間: {room.display_name}")
                st.session_state[f'delete_room_{room.room_id}'] = False
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 刪除失敗")
    
    with col2:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state[f'delete_room_{room.room_id}'] = False
            st.rerun()


@st.dialog("➕ 管理設備", width="large")
def manage_devices_dialog(room: Room):
    """管理房間設備對話框"""
    # 隱藏對話框右上角的關閉按鈕
    st.markdown("""
        <style>
        /* 隱藏對話框的關閉按鈕 - 使用多種選擇器確保覆蓋 */
        button[kind="header"] {
            display: none !important;
        }
        
        button[aria-label="Close"] {
            display: none !important;
        }
        
        div[data-testid="stDialog"] button[kind="header"] {
            display: none !important;
        }
        
        /* 針對可能的內部類名 */
        button.st-emotion-cache-ue6h4q,
        button.st-emotion-cache-7oyrr6 {
            display: none !important;
        }
        
        /* 通過屬性選擇器 */
        button[data-baseweb="button"][kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader(f"📱 管理設備 - {room.display_name}")
    
    # 顯示房間容量
    if room.max_devices > 0:
        st.info(f"📊 房間容量：{room.capacity_text}（剩餘 {room.max_devices - room.device_count} 個名額）")
    else:
        st.info(f"📊 房間容量：{room.capacity_text}（無限制）")
    
    st.markdown("---")
    
    # 獲取所有設備並按排序順序排列
    all_devices = st.session_state.device_registry.get_all_devices()
    all_devices.sort(key=lambda d: d.sort_order)  # 按設備管理頁面的排序方式排序
    
    if not all_devices:
        st.warning("⚠️ 沒有可用的設備")
        if st.button("關閉"):
            st.session_state[f'show_manage_devices_{room.room_id}'] = False
            st.rerun()
        return
    
    st.markdown("**選擇要加入房間的設備**")
    st.caption("💡 已經在其他房間的設備，勾選後會自動轉移到此房間")
    
    # 創建設備選擇列表
    selected_devices = []
    
    for device in all_devices:
        # 檢查設備當前所在房間
        current_room = st.session_state.room_registry.get_device_room(device.device_id)
        
        # 預設勾選狀態（如果設備已在此房間）
        default_checked = (current_room and current_room.room_id == room.room_id)
        
        # 顯示設備信息
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 構建標籤
            label = device.display_name
            if current_room:
                if current_room.room_id == room.room_id:
                    label += f" ✅ **（目前在此房間）**"
                else:
                    label += f" 📍 **（目前在：{current_room.name}）**"
            
            # 設備選擇框
            checked = st.checkbox(
                label,
                value=default_checked,
                key=f"device_select_{device.device_id}_{room.room_id}"
            )
            
            if checked:
                selected_devices.append((device, current_room))
        
        with col2:
            # 顯示設備狀態
            if device.is_online:
                st.caption("🟢 在線")
            else:
                st.caption("🔴 離線")
    
    st.markdown("---")
    
    # 按鈕
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 保存", type="primary", use_container_width=True):
            # 檢查容量
            if room.max_devices > 0 and len(selected_devices) > room.max_devices:
                st.error(f"❌ 選擇的設備數量（{len(selected_devices)}）超過房間上限（{room.max_devices}）")
                return
            
            # 處理設備變更
            success_count = 0
            transfer_count = 0
            
            # 移除未勾選的設備
            for device_id in room.device_ids.copy():
                if not any(d.device_id == device_id for d, _ in selected_devices):
                    success, msg = st.session_state.room_registry.remove_device_from_room(
                        room.room_id,
                        device_id
                    )
                    if success:
                        success_count += 1
            
            # 添加勾選的設備
            for device, current_room in selected_devices:
                if not room.has_device(device.device_id):
                    success, msg = st.session_state.room_registry.add_device_to_room(
                        room.room_id,
                        device.device_id
                    )
                    if success:
                        success_count += 1
                        if current_room and current_room.room_id != room.room_id:
                            transfer_count += 1
            
            if success_count > 0:
                msg_parts = [f"✅ 成功更新 {success_count} 台設備"]
                if transfer_count > 0:
                    msg_parts.append(f"（其中 {transfer_count} 台從其他房間轉移）")
                st.success(" ".join(msg_parts))
                logger.info(f"✅ 更新房間設備: {room.display_name}")
                time.sleep(1)
                st.session_state[f'show_manage_devices_{room.room_id}'] = False
                st.rerun()
            else:
                st.info("💡 沒有變更")
    
    with col2:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state[f'show_manage_devices_{room.room_id}'] = False
            st.rerun()


@st.dialog("⚡ 執行動作", width="large")
def execute_action_on_room_dialog(room: Room):
    """在房間所有設備上執行動作對話框"""
    # 隱藏對話框右上角的關閉按鈕
    st.markdown("""
        <style>
        /* 隱藏對話框的關閉按鈕 - 使用多種選擇器確保覆蓋 */
        button[kind="header"] {
            display: none !important;
        }
        
        button[aria-label="Close"] {
            display: none !important;
        }
        
        div[data-testid="stDialog"] button[kind="header"] {
            display: none !important;
        }
        
        /* 針對可能的內部類名 */
        button.st-emotion-cache-ue6h4q,
        button.st-emotion-cache-7oyrr6 {
            display: none !important;
        }
        
        /* 通過屬性選擇器 */
        button[data-baseweb="button"][kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader(f"⚡ 批量執行動作 - {room.display_name}")
    
    # 獲取房間內設備
    room_devices = st.session_state.room_registry.get_room_devices(
        room.room_id,
        st.session_state.device_registry
    )
    
    # 按設備管理頁面的排序方式排序
    room_devices.sort(key=lambda d: d.sort_order)
    
    if not room_devices:
        st.warning("⚠️ 房間內沒有設備")
        if st.button("關閉"):
            st.session_state[f'show_execute_action_room_{room.room_id}'] = False
            st.rerun()
        return
    
    # 顯示設備信息
    online_devices = [d for d in room_devices if d.status == DeviceStatus.ONLINE]
    offline_devices = [d for d in room_devices if d.status == DeviceStatus.OFFLINE]
    not_connected_devices = [d for d in room_devices if d.status == DeviceStatus.NOT_CONNECTED]
    
    st.info(f"📱 房間內設備：共 {len(room_devices)} 台（🟢 在線 {len(online_devices)} 台，🟠 離線 {len(offline_devices)} 台，⚫ 未連接 {len(not_connected_devices)} 台）")
    
    if not online_devices:
        st.warning("⚠️ 沒有在線設備，無法執行動作")
        if st.button("關閉"):
            st.session_state[f'show_execute_action_room_{room.room_id}'] = False
            st.rerun()
        return
    
    st.caption("💡 動作將在所有在線設備上執行")
    
    st.markdown("---")
    
    # 獲取所有動作
    all_actions = st.session_state.action_registry.get_all_actions()
    
    if not all_actions:
        st.info("📝 還沒有任何動作，請先前往動作管理頁面創建動作")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ 前往動作管理", use_container_width=True, type="primary"):
                st.switch_page("pages/3_⚡_動作管理.py")
        with col2:
            if st.button("❌ 關閉", use_container_width=True):
                st.session_state[f'show_execute_action_room_{room.room_id}'] = False
                st.rerun()
        return
    
    # 動作選擇
    st.markdown("**選擇要執行的動作**")
    
    action_options = {action.action_id: action for action in all_actions}
    action_labels = {
        action.action_id: f"{action.display_name}" + (f" - {action.description[:30]}..." if action.description and len(action.description) > 30 else f" - {action.description}" if action.description else "")
        for action in all_actions
    }
    
    selected_action_id = st.selectbox(
        "動作",
        options=list(action_options.keys()),
        format_func=lambda aid: action_labels[aid],
        label_visibility="collapsed"
    )
    
    selected_action = action_options[selected_action_id]
    
    # 顯示動作詳情
    with st.expander("📋 動作詳情", expanded=False):
        st.markdown(f"**類型**: {selected_action.type_name}")
        if selected_action.params:
            st.markdown("**參數**:")
            for key, value in selected_action.params.items():
                if value:
                    st.text(f"  {key}: {value}")
    
    st.markdown("---")
    
    # 執行按鈕
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 執行", type="primary", use_container_width=True):
            # 準備設備列表
            device_list = [device.connection_string for device in online_devices]
            
            # 創建進度顯示
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            # 定義進度回調
            def update_progress(completed, total):
                progress = completed / total
                progress_bar.progress(progress)
                progress_text.text(f"🚀 執行進度：{completed}/{total} 台設備")
            
            with st.spinner("🚀 並發執行中..."):
                # 準備房間信息（如果房間配置了 Socket Server）
                # 準備房間信息
                room_info = {}
                
                # Socket Server 參數
                if room.socket_ip and room.socket_port:
                    room_info['socket_ip'] = room.socket_ip
                    room_info['socket_port'] = room.socket_port
                
                # 房間參數
                if room.parameters:
                    room_info['parameters'] = room.parameters
                    
                    # 建立 device connection_string -> device_id 的映射
                    # 這樣 ADB Manager 就能找到正確的設備 ID 來查詢參數
                    device_id_map = {d.connection_string: d.device_id for d in online_devices}
                    room_info['device_id_map'] = device_id_map
                
                # 準備設備參數映射 (用於 device_ip 等)
                # 即使沒有房間參數，我們也想發送 device_id/ip 給應用
                if 'device_id_map' not in room_info:
                     room_info['device_id_map'] = {d.connection_string: d.device_id for d in online_devices}
                
                # 構建 device_params_map (目前主要用於 IP)
                device_params_map = {}
                for d in online_devices:
                    device_params_map[d.connection_string] = {
                        'ip': d.ip,
                        'port': d.port
                    }
                room_info['device_params_map'] = device_params_map
                
                # 使用並發方法執行
                batch_results = st.session_state.adb_manager.execute_action_batch(
                    device_list,
                    selected_action,
                    progress_callback=update_progress,
                    room_info=room_info
                )
                
                # 處理結果
                success_count = 0
                fail_count = 0
                results = []
                
                for device_str, success, message in batch_results:
                    # 找到對應的設備對象
                    device = next((d for d in online_devices if d.connection_string == device_str), None)
                    device_name = device.display_name if device else device_str
                    
                    if success:
                        success_count += 1
                        results.append(f"✅ {device_name}: {message}")
                    else:
                        fail_count += 1
                        results.append(f"❌ {device_name}: {message}")
                
                # 清除進度顯示
                progress_placeholder.empty()
                progress_bar.empty()
                progress_text.empty()
                
                # 更新動作統計
                selected_action.execution_count += len(online_devices)
                selected_action.success_count += success_count
                selected_action.failure_count += fail_count
                from datetime import datetime
                selected_action.last_executed_at = datetime.now()
                selected_action.last_execution_status = f"批量執行：成功 {success_count}/{len(online_devices)}"
                st.session_state.action_registry.update_action(selected_action)
                
                # 顯示結果
                st.markdown("### 執行結果")
                st.success(f"✅ 成功：{success_count} 台")
                if fail_count > 0:
                    st.error(f"❌ 失敗：{fail_count} 台")
                
                # 顯示詳細結果
                with st.expander("查看詳細結果"):
                    for result in results:
                        st.text(result)
                
                logger.info(f"⚡ 批量執行動作: {selected_action.display_name} -> {room.display_name} (成功: {success_count}, 失敗: {fail_count})")
                
                time.sleep(2)
                st.session_state[f'show_execute_action_room_{room.room_id}'] = False
                st.rerun()
    
    with col2:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state[f'show_execute_action_room_{room.room_id}'] = False
            st.rerun()


@st.dialog("🔌 重新連接設備", width="large")
def reconnect_room_devices_dialog(room: Room):
    """重新連接房間內設備對話框"""
    # 隱藏對話框右上角的關閉按鈕
    st.markdown("""
        <style>
        /* 隱藏對話框的關閉按鈕 - 使用多種選擇器確保覆蓋 */
        button[kind="header"] {
            display: none !important;
        }
        
        button[aria-label="Close"] {
            display: none !important;
        }
        
        div[data-testid="stDialog"] button[kind="header"] {
            display: none !important;
        }
        
        /* 針對可能的內部類名 */
        button.st-emotion-cache-ue6h4q,
        button.st-emotion-cache-7oyrr6 {
            display: none !important;
        }
        
        /* 通過屬性選擇器 */
        button[data-baseweb="button"][kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader(f"🔌 重新連接設備 - {room.display_name}")
    st.caption("💡 檢查房間內設備的連接狀態，並嘗試重新連接不在線的設備")
    
    st.markdown("---")
    
    # 獲取房間內設備
    room_devices = st.session_state.room_registry.get_room_devices(
        room.room_id,
        st.session_state.device_registry
    )
    
    # 按設備管理頁面的排序方式排序
    room_devices.sort(key=lambda d: d.sort_order)
    
    if not room_devices:
        st.warning("⚠️ 房間內沒有設備")
        if st.button("關閉"):
            st.session_state[f'show_reconnect_room_{room.room_id}'] = False
            st.rerun()
        return
    
    # 獲取當前 ADB 連接的設備列表
    adb_devices = st.session_state.adb_manager.get_devices()
    # 創建 serial -> state 的映射
    adb_device_map = {d['serial']: d['state'] for d in adb_devices}
    
    # 檢查每個設備的連接狀態
    devices_to_reconnect = []
    devices_status = []
    
    for device in room_devices:
        # 構建可能的連接字串
        possible_serials = [device.serial]
        if device.ip:
            possible_serials.append(f"{device.ip}:{device.port}")
        
        # 查找設備在 adb devices 中的狀態
        adb_state = None
        for serial in possible_serials:
            if serial in adb_device_map:
                adb_state = adb_device_map[serial]
                break
        
        # 根據設備狀態和 ADB 狀態判斷
        if device.status == DeviceStatus.NOT_CONNECTED and device.ip:
            # 未連接狀態且有 IP → 需要重新連接
            devices_to_reconnect.append(device)
            devices_status.append({
                'device': device,
                'status': '需要重新連接',
                'reason': '設備未連接（不在 ADB 列表中）'
            })
        elif device.status == DeviceStatus.ONLINE:
            if adb_state == "device":
                devices_status.append({
                    'device': device,
                    'status': '已連接',
                    'reason': '設備在線（ADB state: device）'
                })
            elif adb_state == "offline":
                devices_status.append({
                    'device': device,
                    'status': '離線',
                    'reason': '設備在 ADB 列表中但狀態為 offline'
                })
            else:
                # 狀態不一致，可能需要重新連接
                if device.ip:
                    devices_to_reconnect.append(device)
                    devices_status.append({
                        'device': device,
                        'status': '需要重新連接',
                        'reason': '設備標記為在線但不在 ADB 列表中'
                    })
                else:
                    devices_status.append({
                        'device': device,
                        'status': '無法連接',
                        'reason': '設備沒有 IP 地址'
                    })
        elif device.status == DeviceStatus.OFFLINE:
            devices_status.append({
                'device': device,
                'status': '跳過',
                'reason': '設備狀態為離線（ADB state: offline），不需要重新連接'
            })
        else:
            # 其他狀態
            if device.ip:
                devices_status.append({
                    'device': device,
                    'status': '無法連接',
                    'reason': f'設備狀態：{device.status}'
                })
            else:
                devices_status.append({
                    'device': device,
                    'status': '無法連接',
                    'reason': '設備沒有 IP 地址'
                })
    
    # 顯示設備狀態
    st.markdown("### 📊 設備連接狀態")
    
    for status_info in devices_status:
        device = status_info['device']
        status = status_info['status']
        reason = status_info['reason']
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if status == '需要重新連接':
                st.markdown(f"**{device.display_name}** - ⚠️ {status}")
            elif status == '已連接':
                st.markdown(f"**{device.display_name}** - ✅ {status}")
            elif status == '跳過':
                st.markdown(f"**{device.display_name}** - ⏭️ {status}")
            else:
                st.markdown(f"**{device.display_name}** - ❌ {status}")
            st.caption(f"  {reason}")
        
        with col2:
            # 顯示設備狀態圖示
            status_icon = STATUS_ICONS.get(device.status, "❓")
            status_text = {
                DeviceStatus.ONLINE: "🟢 在線",
                DeviceStatus.OFFLINE: "🟠 離線",
                DeviceStatus.NOT_CONNECTED: "⚫ 未連接",
            }.get(device.status, f"{status_icon} {device.status}")
            st.caption(status_text)
    
    st.markdown("---")
    
    # 顯示需要重新連接的設備數量
    if devices_to_reconnect:
        st.info(f"📋 發現 {len(devices_to_reconnect)} 台設備需要重新連接")
    else:
        st.success("✅ 所有設備連接正常，無需重新連接")
    
    # 按鈕
    col1, col2 = st.columns(2)
    
    with col1:
        if devices_to_reconnect:
            if st.button("🔌 開始重新連接", type="primary", use_container_width=True):
                with st.spinner("正在重新連接設備..."):
                    # 準備設備列表（IP 和 Port）
                    devices_list = [(device.ip, device.port) for device in devices_to_reconnect if device.ip]
                    
                    # 創建設備映射（用於查找結果對應的設備）
                    device_map = {f"{device.ip}:{device.port}": device for device in devices_to_reconnect if device.ip}
                    
                    # 進度顯示
                    progress_text = st.empty()
                    
                    def progress_callback(completed, total):
                        progress_text.text(f"🔌 連接進度：{completed}/{total} 台設備")
                    
                    # 使用並發連接（與 execute_action_batch 相同的模式）
                    logger.info(f"🔌 開始並發重新連接: {room.display_name} ({len(devices_list)} 台設備)")
                    batch_results = st.session_state.adb_manager.connect_batch(
                        devices_list,
                        max_workers=10,
                        progress_callback=progress_callback
                    )
                    
                    # 處理結果
                    success_count = 0
                    fail_count = 0
                    results = []
                    
                    for connection_str, success, output in batch_results:
                        device = device_map.get(connection_str)
                        if not device:
                            continue
                        
                        if success or "already connected" in output.lower():
                            # 連接成功，更新 last_seen
                            # 狀態會在下次自動掃描時根據 ADB 實際狀態更新（ONLINE 或 OFFLINE）
                            device.last_seen = datetime.now()
                            st.session_state.device_registry.save_device(device)
                            success_count += 1
                            results.append(f"✅ {device.display_name}: 連接命令已發送，狀態將在下次掃描時更新")
                            logger.info(f"✅ 重新連接成功: {device.display_name}，等待狀態掃描更新")
                        else:
                            fail_count += 1
                            results.append(f"❌ {device.display_name}: {output}")
                            logger.error(f"❌ 重新連接失敗: {device.display_name} - {output}")
                    
                    # 清除進度顯示
                    progress_text.empty()
                    
                    # 顯示結果
                    st.markdown("### 連接結果")
                    st.success(f"✅ 成功：{success_count} 台")
                    if fail_count > 0:
                        st.error(f"❌ 失敗：{fail_count} 台")
                    
                    # 顯示詳細結果
                    with st.expander("查看詳細結果"):
                        for result in results:
                            st.text(result)
                    
                    logger.info(f"🔌 重新連接完成: {room.display_name} (成功: {success_count}, 失敗: {fail_count})")
                    
                    time.sleep(2)
                    st.session_state[f'show_reconnect_room_{room.room_id}'] = False
                    st.rerun()
        else:
            st.button("🔌 開始重新連接", use_container_width=True, disabled=True)
            st.caption("（無需重新連接的設備）")
    
    with col2:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state[f'show_reconnect_room_{room.room_id}'] = False
            st.rerun()


@st.dialog("⚡ 執行動作", width="large")
def execute_device_action_dialog(device, room: Optional[Room] = None):
    """在設備上執行動作對話框（房間視圖使用）"""
    # 隱藏對話框右上角的關閉按鈕
    st.markdown("""
        <style>
        /* 隱藏對話框的關閉按鈕 - 使用多種選擇器確保覆蓋 */
        button[kind="header"] {
            display: none !important;
        }
        
        button[aria-label="Close"] {
            display: none !important;
        }
        
        div[data-testid="stDialog"] button[kind="header"] {
            display: none !important;
        }
        
        /* 針對可能的內部類名 */
        button.st-emotion-cache-ue6h4q,
        button.st-emotion-cache-7oyrr6 {
            display: none !important;
        }
        
        /* 通過屬性選擇器 */
        button[data-baseweb="button"][kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader(f"📱 目標設備：{device.display_name}")
    
    if not device.is_online:
        st.warning("⚠️ 設備離線，請先連線後再執行動作")
        if st.button("關閉"):
            st.session_state[f'execute_action_on_{device.device_id}'] = False
            st.rerun()
        return
    
    st.markdown("---")
    
    # 獲取所有動作
    all_actions = st.session_state.action_registry.get_all_actions()
    
    if not all_actions:
        st.info("📝 還沒有任何動作，請先前往動作管理頁面創建動作")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ 前往動作管理", use_container_width=True, type="primary"):
                st.switch_page("pages/3_⚡_動作管理.py")
        with col2:
            if st.button("❌ 關閉", use_container_width=True):
                st.session_state[f'execute_action_on_{device.device_id}'] = False
                st.rerun()
        return
    
    # 動作選擇
    st.markdown("**選擇要執行的動作**")
    
    # 顯示動作列表
    action_options = {action.action_id: action for action in all_actions}
    action_labels = {
        action.action_id: f"{action.display_name}" + (f" - {action.description[:30]}..." if action.description and len(action.description) > 30 else f" - {action.description}" if action.description else "")
        for action in all_actions
    }
    
    selected_action_id = st.selectbox(
        "動作",
        options=list(action_options.keys()),
        format_func=lambda aid: action_labels[aid],
        label_visibility="collapsed"
    )
    
    selected_action = action_options[selected_action_id]
    
    # 顯示動作詳情
    with st.expander("📋 動作詳情", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**類型**: {selected_action.type_name}")
            if selected_action.execution_count > 0:
                st.markdown(f"**執行次數**: {selected_action.execution_count}")
        with col2:
            if selected_action.execution_count > 0:
                st.markdown(f"**成功率**: {selected_action.success_rate:.0f}%")
            if selected_action.last_executed_at:
                from datetime import datetime
                time_diff = datetime.now() - selected_action.last_executed_at
                if time_diff.days > 0:
                    last_exec = f"{time_diff.days} 天前"
                elif time_diff.seconds >= 3600:
                    last_exec = f"{time_diff.seconds // 3600} 小時前"
                elif time_diff.seconds >= 60:
                    last_exec = f"{time_diff.seconds // 60} 分鐘前"
                else:
                    last_exec = "剛剛"
                st.markdown(f"**最後執行**: {last_exec}")
        
        # 顯示參數
        if selected_action.params:
            st.markdown("**參數**:")
            for key, value in selected_action.params.items():
                if value:
                    st.text(f"  {key}: {value}")
    
    st.markdown("---")
    
    # 執行按鈕
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 執行", type="primary", use_container_width=True):
            with st.spinner("執行中..."):
                # 準備房間信息（如果提供了房間且房間配置了 Socket Server）
                room_info = None
                if room and room.socket_ip and room.socket_port:
                    room_info = {
                        'socket_ip': room.socket_ip,
                        'socket_port': room.socket_port
                    }
                
                # 執行動作
                success, message = st.session_state.adb_manager.execute_action(
                    device.connection_string,
                    selected_action,
                    room_info=room_info
                )
                
                # 更新執行統計
                selected_action.increment_execution(success=success, status=message)
                st.session_state.action_registry.update_action(selected_action)
                
                if success:
                    st.success(f"✅ {message}")
                    logger.info(f"✅ 執行動作成功: {selected_action.display_name} -> {device.display_name}")
                else:
                    st.error(f"❌ {message}")
                    logger.error(f"❌ 執行動作失敗: {selected_action.display_name} -> {device.display_name}")
                
                time.sleep(1.5)
                st.session_state[f'execute_action_on_{device.device_id}'] = False
                st.rerun()
    
    with col2:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state[f'execute_action_on_{device.device_id}'] = False
            st.rerun()


@st.dialog("🏠 房間視圖", width="large")
def room_view_dialog(room: Room):
    """房間視圖對話框 - 顯示房間內所有設備"""
    # 確保必要的組件已初始化
    from utils.init import ensure_room_registry, ensure_initialization
    ensure_initialization()
    ensure_room_registry()
    
    # 隱藏對話框右上角的關閉按鈕
    st.markdown("""
        <style>
        /* 隱藏對話框的關閉按鈕 - 使用多種選擇器確保覆蓋 */
        button[kind="header"] {
            display: none !important;
        }
        
        button[aria-label="Close"] {
            display: none !important;
        }
        
        div[data-testid="stDialog"] button[kind="header"] {
            display: none !important;
        }
        
        /* 針對可能的內部類名 */
        button.st-emotion-cache-ue6h4q,
        button.st-emotion-cache-7oyrr6 {
            display: none !important;
        }
        
        /* 通過屬性選擇器 */
        button[data-baseweb="button"][kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 房間信息
    st.markdown(f"## {room.display_name}")
    
    if room.description:
        st.caption(room.description)
    
    # 房間統計
    room_devices = st.session_state.room_registry.get_room_devices(
        room.room_id,
        st.session_state.device_registry
    )
    
    # 按設備管理頁面的排序方式排序
    room_devices.sort(key=lambda d: d.sort_order)
    
    online_devices = [d for d in room_devices if d.status == DeviceStatus.ONLINE]
    offline_devices = [d for d in room_devices if d.status == DeviceStatus.OFFLINE]
    not_connected_devices = [d for d in room_devices if d.status == DeviceStatus.NOT_CONNECTED]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("設備總數", room.capacity_text)
    
    with col2:
        st.metric("🟢 在線", len(online_devices))
    
    with col3:
        st.metric("🟠 離線", len(offline_devices))
    
    with col4:
        st.metric("⚫ 未連接", len(not_connected_devices))
    
    with col4:
        if room.max_devices > 0:
            remaining = room.max_devices - room.device_count
            st.metric("剩餘名額", remaining)
        else:
            st.metric("容量限制", "無限制")
    
    st.markdown("---")
    
    # 快速操作按鈕
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⚡ 執行動作", use_container_width=True, type="primary"):
            st.session_state[f'show_room_view_{room.room_id}'] = False
            st.session_state[f'show_execute_action_room_{room.room_id}'] = True
            st.rerun()
    
    with col2:
        if st.button("➕ 管理設備", use_container_width=True):
            st.session_state[f'show_room_view_{room.room_id}'] = False
            st.session_state[f'show_manage_devices_{room.room_id}'] = True
            st.rerun()
    
    with col3:
        if st.button("❌ 關閉", use_container_width=True):
            st.session_state[f'show_room_view_{room.room_id}'] = False
            st.rerun()
    
    st.markdown("---")
    
    # Socket Server 監控（如果房間配置了 Socket Server）
    if room.socket_ip and room.socket_port:
        st.markdown("### 📡 Socket Server 監控")
        
        # 檢查 Socket Server 狀態
        socket_running = False
        if 'socket_server_manager' in st.session_state:
            socket_manager = st.session_state.socket_server_manager
            socket_running = socket_manager.is_server_running(room.room_id)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if socket_running:
                st.success(f"🟢 Socket Server 運行中 - {room.socket_ip}:{room.socket_port}")
            else:
                st.warning(f"🔴 Socket Server 未運行 - {room.socket_ip}:{room.socket_port}")
        
        with col2:
            if socket_running:
                if st.button("🔄 重啟", key=f"restart_socket_in_view_{room.room_id}", use_container_width=True):
                    if 'socket_server_manager' in st.session_state:
                        socket_manager = st.session_state.socket_server_manager
                        success, msg = socket_manager.restart_server(
                            room.room_id,
                            room.name,
                            room.socket_ip,
                            room.socket_port
                        )
                        if success:
                            st.success("✅ Socket Server 已重啟")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
        
        # 日誌視窗和命令輸入
        tab1, tab2 = st.tabs(["📋 日誌監看", "⌨️ 命令發送"])
        
        with tab1:
            # 日誌視窗
            from core.socket_client import read_socket_server_log
            
            # 讀取日誌
            log_lines = read_socket_server_log(room.room_id, room.socket_port, lines=200)
            
            if log_lines:
                # 顯示日誌（只讀文本框）
                log_text = ''.join(log_lines)
                # 使用動態 key 強制刷新 UI
                import time
                st.text_area(
                    "Socket Server 日誌",
                    value=log_text,
                    height=300,
                    disabled=True,
                    key=f"socket_log_{room.room_id}_{int(time.time())}"
                )
                
                # 自動滾動到底部
                import streamlit.components.v1 as components
                # 使用當前時間戳確保 JS 每次都會重新執行
                current_time = int(time.time() * 1000)
                js = f"""
                <script>
                    // Timestamp: {current_time}
                    function scrollBottom() {{
                        var textAreas = window.parent.document.querySelectorAll('textarea');
                        for (var i = 0; i < textAreas.length; i++) {{
                            if (textAreas[i].getAttribute('aria-label') === 'Socket Server 日誌') {{
                                textAreas[i].scrollTop = textAreas[i].scrollHeight;
                                break;
                            }}
                        }}
                    }}
                    // 嘗試多次滾動以確保渲染完成
                    setTimeout(scrollBottom, 100);
                    setTimeout(scrollBottom, 300);
                    setTimeout(scrollBottom, 500);
                </script>
                """
                components.html(js, height=0)
                
                # 刷新按鈕
                if st.button("🔄 刷新日誌", key=f"refresh_log_{room.room_id}"):
                    st.rerun()
            else:
                st.info("📝 日誌文件不存在或為空")
                if st.button("🔄 刷新日誌", key=f"refresh_log_{room.room_id}"):
                    st.rerun()
        
        with tab2:
            # 命令輸入欄
            st.markdown("**發送命令到 Socket Server**")
            
            # 命令類型選擇
            command_type = st.selectbox(
                "命令類型",
                options=["send_params", "echo", "command"],
                index=0,
                help="選擇要發送的命令類型",
                key=f"command_type_{room.room_id}"
            )
            
            # 命令數據輸入
            command_data = None
            if command_type == "echo":
                command_data = st.text_input(
                    "要回顯的數據",
                    placeholder="輸入要回顯的文本",
                    key=f"echo_data_{room.room_id}"
                )
            elif command_type == "command":
                command_data = st.text_input(
                    "命令數據（JSON 格式）",
                    placeholder='{"action": "your_command"}',
                    key=f"command_data_{room.room_id}"
                )
            elif command_type == "send_params":

                # 序列化所有參數
                params_list = [p.model_dump() for p in room.parameters] if room.parameters else []
                # 構建完整 payload (如果需要包裹在某個 key 中，例如 'parameters')
                # 根據用戶描述："send parameters will put all room parameters in json way"
                # 我們發送一個包含 parameters 列表的 JSON
                payload = params_list
                
                # 為了顯示漂亮，轉為字串
                json_str = json.dumps(payload, ensure_ascii=False, indent=2)
                
                st.text_area(
                    "發送內容預覽",
                    value=json_str,
                    height=200,
                    disabled=True
                )
                # 將序列化後的對象作為數據準備發送
                # 注意：後面的邏輯會再次檢查 command_type
            
            # 發送按鈕
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("📤 發送命令", type="primary", use_container_width=True, key=f"send_command_{room.room_id}"):
                    if socket_running:
                        from core.socket_client import SocketClient
                        
                        try:
                            with SocketClient(room.socket_ip, room.socket_port) as client:
                                # 準備數據
                                data = None
                                if command_type == "echo" and command_data:
                                    data = {"text": command_data}
                                elif command_type == "command" and command_data:
                                    try:
                                        data = json.loads(command_data)
                                    except json.JSONDecodeError:
                                        st.error("❌ 無效的 JSON 格式")
                                        st.stop()
                                elif command_type == "send_params":
                                    # 直接使用參數列表
                                    data = [p.model_dump() for p in room.parameters] if room.parameters else []
                                
                                # 發送命令
                                success, response = client.send_command(command_type, data)
                                
                                if success:
                                    st.success("✅ 命令發送成功")
                                    st.json(response)
                                else:
                                    st.error(f"❌ 命令發送失敗: {response.get('message', '未知錯誤')}")
                        except Exception as e:
                            st.error(f"❌ 連接失敗: {str(e)}")
                    else:
                        st.error("❌ Socket Server 未運行，無法發送命令")
            
            with col2:
                if st.button("🔄 刷新", use_container_width=True, key=f"refresh_command_{room.room_id}"):
                    st.rerun()
            
            # 顯示幫助信息
            with st.expander("💡 命令說明"):
                st.markdown("""
                **命令類型說明：**
                - **echo**: 回顯命令，服務器會返回發送的數據
                - **command**: 自定義命令，可以發送 JSON 格式的數據
                
                **使用示例：**
                - 選擇 `echo`，輸入文本後發送，服務器會回顯該文本
                - 選擇 `command`，輸入 JSON 格式的數據發送自定義命令
                """)
        
        st.markdown("---")
    
    st.markdown("---")
    
    # 顯示設備列表
    if not room_devices:
        st.info("📭 房間內沒有設備，點擊「管理設備」添加設備")
        return
    
    st.markdown("### 📱 房間內設備")
    
    # 獲取設備詳細狀態
    from config.settings import DEVICE_UPDATE_INTERVAL
    import time as time_module
    
    # 使用標籤頁分隔不同狀態的設備
    tabs_data = []
    if online_devices:
        tabs_data.append(("🟢 在線", online_devices))
    if offline_devices:
        tabs_data.append(("🟠 離線", offline_devices))
    if not_connected_devices:
        tabs_data.append(("⚫ 未連接", not_connected_devices))
    
    if len(tabs_data) > 1:
        # 多個狀態，使用標籤頁
        tab_names = [f"{name} ({len(devs)})" for name, devs in tabs_data]
        tabs = st.tabs(tab_names)
        for tab, (name, devs) in zip(tabs, tabs_data):
            with tab:
                render_devices_in_room(devs, room)
    elif len(tabs_data) == 1:
        # 只有一種狀態，直接顯示
        _, devs = tabs_data[0]
        render_devices_in_room(devs, room)


def render_devices_in_room(devices, room):
    """在房間視圖中渲染設備卡片"""
    from config.constants import STATUS_ICONS
    from datetime import datetime
    import time as time_module
    
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


