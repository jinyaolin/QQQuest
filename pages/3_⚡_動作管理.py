"""
動作管理頁面
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from typing import Optional, List, Tuple
import time
from pathlib import Path
from datetime import datetime
from core.action import Action, ActionType, ACTION_TYPE_NAMES, ACTION_TYPE_ICONS, COMMON_KEYCODES, ActionParamsValidator
from core.action_registry import ActionRegistry
from utils.logger import get_logger

logger = get_logger(__name__)


def get_apks_directory() -> Path:
    """獲取 APKs 目錄路徑（相對於 Streamlit 應用根目錄）"""
    # 獲取當前文件的目錄（pages/），然後回到上一級（項目根目錄）
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    apks_dir = project_root / "apks"
    return apks_dir


def scan_apks_directory() -> List[Tuple[str, str, datetime]]:
    """
    掃描 apks 目錄，返回所有 APK 文件列表
    
    Returns:
        List of (file_path, file_name, created_time) tuples
    """
    apks_dir = get_apks_directory()
    
    # 如果目錄不存在，創建它
    if not apks_dir.exists():
        apks_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"創建 APKs 目錄: {apks_dir}")
        return []
    
    apk_files = []
    for file_path in apks_dir.glob("*.apk"):
        if file_path.is_file():
            # 獲取文件創建時間
            created_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            apk_files.append((
                str(file_path),
                file_path.name,
                created_time
            ))
    
    # 按創建時間排序（最新的在前）
    apk_files.sort(key=lambda x: x[2], reverse=True)
    
    return apk_files

# 頁面配置
st.set_page_config(
    page_title="動作管理 - QQQuest",
    page_icon="⚡",
    layout="wide"
)

# 隱藏標題旁的錨點鏈接圖標
st.markdown("""
    <style>
    /* 隱藏標題旁的錨點鏈接圖標 */
    a.st-emotion-cache-yinll1,
    a[class*="st-emotion-cache"][href^="#"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# 自動刷新（每 5 秒）- 但在有對話框時暫停
dialog_keys = [key for key in st.session_state.keys() if key.startswith(('add_action', 'edit_action_', 'delete_action_', 'execute_action_'))]
dialog_states = {key: st.session_state.get(key, False) for key in dialog_keys}
has_dialog_open = any(dialog_states.values())

# 只在沒有對話框時自動刷新
if not has_dialog_open:
    count = st_autorefresh(interval=5000, key="action_refresh")

# 初始化系統
from utils.init import ensure_initialization, ensure_action_registry, ensure_room_registry

if not ensure_initialization():
    st.stop()

ensure_action_registry()
ensure_room_registry()  # 需要 room_registry 來查找設備所屬的房間

# Session state 初始化
if 'show_add_action_dialog' not in st.session_state:
    st.session_state.show_add_action_dialog = False
if 'search_keyword' not in st.session_state:
    st.session_state.search_keyword = ""
if 'filter_type' not in st.session_state:
    st.session_state.filter_type = "全部"
if 'new_action_type' not in st.session_state:
    st.session_state.new_action_type = ActionType.WAKE_UP
if 'use_common_keycode' not in st.session_state:
    st.session_state.use_common_keycode = True


@st.dialog("➕ 新增動作", width="large")
def add_action_dialog():
    """新增動作對話框"""
    # 隱藏對話框關閉按鈕
    st.markdown("""
        <style>
        button[kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader("📝 基本資訊")
    
    # 動作類型選擇（在 form 外面，可以實時響應）
    action_type_options = list(ACTION_TYPE_NAMES.keys())
    action_type_labels = [f"{ACTION_TYPE_ICONS[t]} {ACTION_TYPE_NAMES[t]}" for t in action_type_options]
    
    # 找到當前選擇的類型索引
    try:
        current_type_index = action_type_options.index(st.session_state.new_action_type)
    except (ValueError, AttributeError):
        current_type_index = 0
    
    selected_type_index = st.selectbox(
        "動作類型 *",
        options=range(len(action_type_options)),
        index=current_type_index,
        format_func=lambda i: action_type_labels[i],
        help="選擇要執行的動作類型",
        key="new_action_type_select"
    )
    
    # 更新 session state
    selected_type = action_type_options[selected_type_index]
    st.session_state.new_action_type = selected_type
    
    # 動作名稱
    name = st.text_input(
        "動作名稱 *",
        placeholder="例如：啟動訓練程式",
        help="為動作取一個容易識別的名稱",
        key="new_action_name"
    )
    
    # 動作說明
    description = st.text_area(
        "動作說明（選填）",
        placeholder="描述這個動作的用途...",
        height=60,
        key="new_action_description"
    )
    
    st.markdown("---")
    st.subheader("⚙️ 動作參數")
    
    params = {}
    
    # 根據動作類型顯示不同的參數輸入（都在 form 外面）
    if selected_type == ActionType.WAKE_UP:
        st.info("☀️ 喚醒設備不需要額外參數")
        params['verify'] = st.checkbox("驗證喚醒成功", value=True, key="wake_verify")
    
    elif selected_type == ActionType.SLEEP:
        st.info("😴 休眠設備")
        params['force'] = st.checkbox("強制休眠", value=False, help="使用 SLEEP 而非 POWER 鍵", key="sleep_force")
        params['verify'] = st.checkbox("驗證休眠成功", value=True, key="sleep_verify")
    
    elif selected_type == ActionType.KEEP_AWAKE:
        st.info("🔌 保持喚醒（接電源時不進入深度睡眠）")
        st.caption("💡 設置設備在接上電源時保持喚醒狀態，避免網路功能被關閉")
        
        mode_options = {
            0: "禁用（預設值）",
            1: "僅 AC 充電時保持喚醒",
            2: "僅 USB 充電時保持喚醒",
            3: "AC 和 USB 充電時保持喚醒（推薦）"
        }
        
        mode_labels = [f"{k}: {v}" for k, v in mode_options.items()]
        mode_index = st.selectbox(
            "喚醒模式 *",
            options=list(mode_options.keys()),
            format_func=lambda x: mode_options[x],
            index=3,  # 默認選擇推薦值 3
            help="選擇設備在接電源時保持喚醒的模式",
            key="keep_awake_mode"
        )
        params['mode'] = mode_index
        
        st.markdown("---")
        st.markdown("**說明**")
        st.markdown("- **模式 0**: 禁用此功能，設備會按正常的閒置計時器進入深度睡眠")
        st.markdown("- **模式 1**: 僅在使用牆上充電器（AC）時保持喚醒")
        st.markdown("- **模式 2**: 僅在連接電腦 USB 充電時保持喚醒")
        st.markdown("- **模式 3**: AC 和 USB 充電時都保持喚醒，確保網路功能不被關閉（推薦）")
    
    elif selected_type == ActionType.LAUNCH_APP:
        st.info("🚀 執行程式")
        params['package'] = st.text_input(
            "Package 名稱 *",
            placeholder="com.example.app",
            help="應用程式的 package 名稱",
            key="launch_package"
        )
        params['activity'] = st.text_input(
            "Activity 名稱（選填）",
            placeholder=".MainActivity",
            help="Activity 名稱（以 . 開頭的相對名稱或完整類名）",
            key="launch_activity"
        )
        params['stop_existing'] = st.checkbox("啟動前先關閉已運行的實例", value=False, key="launch_stop_existing")
        params['wait'] = st.checkbox("等待啟動完成", value=True, key="launch_wait")
    
    elif selected_type == ActionType.STOP_APP:
        st.info("🛑 關閉程式")
        params['package'] = st.text_input(
            "Package 名稱 *",
            placeholder="com.example.app",
            help="要關閉的應用程式 package 名稱",
            key="stop_package"
        )
        params['method'] = st.selectbox(
            "關閉方式",
            options=["force-stop", "kill"],
            index=0,
            help="force-stop 完全停止應用，kill 僅殺進程",
            key="stop_method"
        )
        params['verify'] = st.checkbox("驗證關閉成功", value=True, key="stop_verify")
    
    elif selected_type == ActionType.RESTART_APP:
        st.info("🔄 重啟應用")
        params['package'] = st.text_input(
            "Package 名稱 *",
            placeholder="com.example.app",
            help="要重啟的應用程式 package 名稱",
            key="restart_package"
        )
        params['activity'] = st.text_input(
            "Activity 名稱（選填）",
            placeholder=".MainActivity",
            help="Activity 名稱（以 . 開頭的相對名稱或完整類名）",
            key="restart_activity"
        )
        params['delay'] = st.number_input(
            "重啟延遲（秒）",
            min_value=0,
            max_value=10,
            value=1,
            help="關閉後等待多少秒再啟動",
            key="restart_delay"
        )
    
    elif selected_type == ActionType.SEND_KEY:
        st.info("⌨️ 發送按鍵")
        
        # 常用按鍵快速選擇
        st.markdown("**常用按鍵**")
        
        use_common = st.checkbox("使用常用按鍵", value=st.session_state.use_common_keycode, key="use_common_key_new")
        st.session_state.use_common_keycode = use_common
        
        if use_common:
            keycode_options = list(COMMON_KEYCODES.keys())
            keycode_labels = [f"{COMMON_KEYCODES[k]['name']} ({k})" for k in keycode_options]
            
            selected_key_index = st.selectbox(
                "選擇按鍵",
                options=range(len(keycode_options)),
                format_func=lambda i: keycode_labels[i],
                key="sendkey_common_select"
            )
            selected_key = keycode_options[selected_key_index]
            params['keycode'] = COMMON_KEYCODES[selected_key]['code']
            st.caption(f"說明：{COMMON_KEYCODES[selected_key]['description']}")
        else:
            params['keycode'] = st.text_input(
                "按鍵碼",
                placeholder="KEYCODE_HOME 或 3",
                help="輸入按鍵碼名稱或數字",
                key="sendkey_custom"
            )
        
        params['repeat'] = st.number_input(
            "重複次數",
            min_value=1,
            max_value=10,
            value=1,
            key="sendkey_repeat"
        )
    
    elif selected_type == ActionType.INSTALL_APK:
        st.info("📦 安裝 APK")
        
        # 掃描 apks 目錄
        apk_files = scan_apks_directory()
        
        if not apk_files:
            st.warning("⚠️ apks 目錄中沒有找到 APK 文件")
            st.caption(f"請將 APK 文件放到以下目錄：{get_apks_directory()}")
            params['apk_path'] = ""
        else:
            # 創建選項列表（顯示文件名和創建時間）
            apk_options = []
            apk_paths = {}
            
            for file_path, file_name, created_time in apk_files:
                # 格式化時間
                time_str = created_time.strftime("%Y-%m-%d %H:%M:%S")
                display_name = f"{file_name} ({time_str})"
                apk_options.append(display_name)
                apk_paths[display_name] = file_path
            
            selected_display = st.selectbox(
                "選擇 APK 文件 *",
                options=apk_options,
                help="選擇要安裝的 APK 文件（顯示創建時間以便區分）",
                key="install_apk_select"
            )
            
            if selected_display:
                params['apk_path'] = apk_paths[selected_display]
                st.caption(f"📁 路徑：{params['apk_path']}")
            else:
                params['apk_path'] = ""
        
        params['replace'] = st.checkbox(
            "替換已存在的應用",
            value=True,
            help="如果應用已安裝，是否替換安裝",
            key="install_replace"
        )
        
        params['grant_permissions'] = st.checkbox(
            "自動授予權限",
            value=False,
            help="安裝時自動授予所有權限",
            key="install_grant_permissions"
        )
    
    st.markdown("---")
    
    # 按鈕（不在 form 裡）
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 保存", type="primary", use_container_width=True, key="add_action_save"):
            # 驗證必填欄位
            if not name:
                st.error("❌ 請輸入動作名稱")
                return
            
            # 驗證參數
            is_valid, error_msg = ActionParamsValidator.validate(selected_type, params)
            if not is_valid:
                st.error(f"❌ {error_msg}")
                return
            
            # 創建動作
            action = st.session_state.action_registry.create_action(
                name=name,
                action_type=selected_type,
                params=params,
                description=description if description else None
            )
            
            if action:
                st.success(f"✅ 動作已創建：{action.display_name}")
                logger.info(f"✅ 創建動作成功: {action.display_name}")
                st.session_state.show_add_action_dialog = False
                st.session_state.new_action_type = ActionType.WAKE_UP  # 重置類型
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 創建動作失敗")
    
    with col2:
        if st.button("❌ 取消", use_container_width=True, key="add_action_cancel"):
            st.session_state.show_add_action_dialog = False
            st.session_state.new_action_type = ActionType.WAKE_UP  # 重置類型
            st.rerun()


@st.dialog("✏️ 編輯動作", width="large")
def edit_action_dialog(action: Action):
    """編輯動作對話框"""
    # 隱藏對話框關閉按鈕
    st.markdown("""
        <style>
        button[kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.caption(f"動作 ID: {action.action_id}")
    st.caption(f"類型: {action.type_name}")
    
    with st.form(f"edit_action_form_{action.action_id}"):
        st.subheader("📝 基本資訊")
        
        # 動作名稱
        name = st.text_input(
            "動作名稱 *",
            value=action.name,
            help="為動作取一個容易識別的名稱"
        )
        
        # 動作說明
        description = st.text_area(
            "動作說明（選填）",
            value=action.description if action.description else "",
            height=60
        )
        
        st.markdown("---")
        st.subheader("⚙️ 動作參數")
        
        params = action.params.copy()
        
        # 根據動作類型顯示參數編輯界面
        # （與新增對話框類似，但使用現有值）
        if action.action_type == ActionType.WAKE_UP:
            params['verify'] = st.checkbox("驗證喚醒成功", value=params.get('verify', True))
        
        elif action.action_type == ActionType.SLEEP:
            params['force'] = st.checkbox("強制休眠", value=params.get('force', False))
            params['verify'] = st.checkbox("驗證休眠成功", value=params.get('verify', True))
        
        elif action.action_type == ActionType.KEEP_AWAKE:
            mode_options = {
                0: "禁用（預設值）",
                1: "僅 AC 充電時保持喚醒",
                2: "僅 USB 充電時保持喚醒",
                3: "AC 和 USB 充電時保持喚醒（推薦）"
            }
            
            current_mode = params.get('mode', 3)
            mode_index = st.selectbox(
                "喚醒模式 *",
                options=list(mode_options.keys()),
                format_func=lambda x: mode_options[x],
                index=list(mode_options.keys()).index(current_mode) if current_mode in mode_options else 3,
                help="選擇設備在接電源時保持喚醒的模式"
            )
            params['mode'] = mode_index
            
            st.markdown("---")
            st.markdown("**說明**")
            st.markdown("- **模式 0**: 禁用此功能，設備會按正常的閒置計時器進入深度睡眠")
            st.markdown("- **模式 1**: 僅在使用牆上充電器（AC）時保持喚醒")
            st.markdown("- **模式 2**: 僅在連接電腦 USB 充電時保持喚醒")
            st.markdown("- **模式 3**: AC 和 USB 充電時都保持喚醒，確保網路功能不被關閉（推薦）")
        
        elif action.action_type == ActionType.LAUNCH_APP:
            params['package'] = st.text_input(
                "Package 名稱 *",
                value=params.get('package', ''),
                placeholder="com.example.app"
            )
            params['activity'] = st.text_input(
                "Activity 名稱（選填）",
                value=params.get('activity', ''),
                placeholder=".MainActivity"
            )
            params['stop_existing'] = st.checkbox("啟動前先關閉已運行的實例", value=params.get('stop_existing', False))
            params['wait'] = st.checkbox("等待啟動完成", value=params.get('wait', True))
        
        elif action.action_type == ActionType.STOP_APP:
            params['package'] = st.text_input(
                "Package 名稱 *",
                value=params.get('package', ''),
                placeholder="com.example.app"
            )
            params['method'] = st.selectbox(
                "關閉方式",
                options=["force-stop", "kill"],
                index=0 if params.get('method') == 'force-stop' else 1
            )
            params['verify'] = st.checkbox("驗證關閉成功", value=params.get('verify', True))
        
        elif action.action_type == ActionType.RESTART_APP:
            params['package'] = st.text_input(
                "Package 名稱 *",
                value=params.get('package', ''),
                placeholder="com.example.app"
            )
            params['activity'] = st.text_input(
                "Activity 名稱（選填）",
                value=params.get('activity', ''),
                placeholder=".MainActivity"
            )
            params['delay'] = st.number_input(
                "重啟延遲（秒）",
                min_value=0,
                max_value=10,
                value=params.get('delay', 1)
            )
        
        elif action.action_type == ActionType.SEND_KEY:
            keycode_value = params.get('keycode', '')
            params['keycode'] = st.text_input(
                "按鍵碼",
                value=str(keycode_value),
                placeholder="KEYCODE_HOME 或 3"
            )
            params['repeat'] = st.number_input(
                "重複次數",
                min_value=1,
                max_value=10,
                value=params.get('repeat', 1)
            )
        
        elif action.action_type == ActionType.INSTALL_APK:
            # 掃描 apks 目錄
            apk_files = scan_apks_directory()
            
            if not apk_files:
                st.warning("⚠️ apks 目錄中沒有找到 APK 文件")
                st.caption(f"請將 APK 文件放到以下目錄：{get_apks_directory()}")
                params['apk_path'] = params.get('apk_path', '')
            else:
                # 創建選項列表（顯示文件名和創建時間）
                apk_options = []
                apk_paths = {}
                
                for file_path, file_name, created_time in apk_files:
                    # 格式化時間
                    time_str = created_time.strftime("%Y-%m-%d %H:%M:%S")
                    display_name = f"{file_name} ({time_str})"
                    apk_options.append(display_name)
                    apk_paths[display_name] = file_path
                
                # 找到當前選擇的 APK（如果存在）
                current_apk_path = params.get('apk_path', '')
                current_index = 0
                if current_apk_path:
                    # 嘗試找到匹配的路徑
                    for i, (file_path, _, _) in enumerate(apk_files):
                        if file_path == current_apk_path or str(file_path) == current_apk_path:
                            current_index = i
                            break
                
                selected_display = st.selectbox(
                    "選擇 APK 文件 *",
                    options=apk_options,
                    index=current_index if current_index < len(apk_options) else 0,
                    help="選擇要安裝的 APK 文件（顯示創建時間以便區分）"
                )
                
                if selected_display:
                    params['apk_path'] = apk_paths[selected_display]
                    st.caption(f"📁 路徑：{params['apk_path']}")
                else:
                    params['apk_path'] = ""
            
            params['replace'] = st.checkbox(
                "替換已存在的應用",
                value=params.get('replace', True),
                help="如果應用已安裝，是否替換安裝"
            )
            
            params['grant_permissions'] = st.checkbox(
                "自動授予權限",
                value=params.get('grant_permissions', False),
                help="安裝時自動授予所有權限"
            )
        
        st.markdown("---")
        
        # 按鈕
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if cancelled:
            st.session_state[f'edit_action_{action.action_id}'] = False
            st.rerun()
        
        if submitted:
            # 驗證
            if not name:
                st.error("❌ 請輸入動作名稱")
                return
            
            is_valid, error_msg = ActionParamsValidator.validate(action.action_type, params)
            if not is_valid:
                st.error(f"❌ {error_msg}")
                return
            
            # 更新動作
            action.name = name
            action.description = description if description else None
            action.params = params
            
            if st.session_state.action_registry.update_action(action):
                st.success(f"✅ 動作已更新：{action.display_name}")
                logger.info(f"✅ 更新動作成功: {action.display_name}")
                st.session_state[f'edit_action_{action.action_id}'] = False
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 更新動作失敗")


@st.dialog("🗑️ 確認刪除", width="small")
def delete_action_dialog(action: Action):
    """刪除動作確認對話框"""
    # 隱藏對話框關閉按鈕
    st.markdown("""
        <style>
        button[kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.warning(f"確定要刪除動作 **{action.display_name}** 嗎？")
    st.caption(f"類型：{action.type_name}")
    
    if action.execution_count > 0:
        st.info(f"📊 此動作已執行 {action.execution_count} 次")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ 確定刪除", type="primary", use_container_width=True):
            if st.session_state.action_registry.delete_action(action.action_id):
                st.success("✅ 動作已刪除")
                logger.info(f"🗑️ 刪除動作: {action.display_name}")
                st.session_state[f'delete_action_{action.action_id}'] = False
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 刪除失敗")
    
    with col2:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state[f'delete_action_{action.action_id}'] = False
            st.rerun()


@st.dialog("▶️ 執行動作", width="medium")
def execute_action_dialog(action: Action):
    """執行動作對話框（選擇設備）"""
    # 隱藏對話框關閉按鈕
    st.markdown("""
        <style>
        button[kind="header"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader(f"{action.display_name}")
    st.caption(f"類型：{action.type_name}")
    
    if action.description:
        st.info(action.description)
    
    st.markdown("---")
    st.markdown("**選擇要執行的設備**")
    
    # 獲取所有設備
    devices = st.session_state.device_registry.get_all_devices()
    online_devices = [d for d in devices if d.is_online]
    
    if not online_devices:
        st.warning("⚠️ 沒有在線設備")
        if st.button("關閉"):
            st.session_state[f'execute_action_{action.action_id}'] = False
            st.rerun()
        return
    
    # 設備選擇
    device_options = {d.device_id: d.display_name for d in online_devices}
    selected_device_id = st.selectbox(
        "設備",
        options=list(device_options.keys()),
        format_func=lambda did: device_options[did]
    )
    
    selected_device = next(d for d in online_devices if d.device_id == selected_device_id)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 執行", type="primary", use_container_width=True):
            with st.spinner("執行中..."):
                # 自動查找設備所屬的房間並獲取 Socket Server 信息
                room_info = None
                if 'room_registry' in st.session_state:
                    device_room = st.session_state.room_registry.get_device_room(selected_device.device_id)
                    if device_room and device_room.socket_ip and device_room.socket_port:
                        room_info = {
                            'socket_ip': device_room.socket_ip,
                            'socket_port': device_room.socket_port
                        }
                        logger.debug(f"📡 自動添加 Socket Server 參數: {selected_device.display_name} -> {device_room.name} ({device_room.socket_ip}:{device_room.socket_port})")
                
                # 執行動作
                success, message = st.session_state.adb_manager.execute_action(
                    selected_device.connection_string,
                    action,
                    room_info=room_info
                )
                
                # 更新執行統計
                action.increment_execution(success=success, status=message)
                st.session_state.action_registry.update_action(action)
                
                if success:
                    st.success(f"✅ {message}")
                    logger.info(f"✅ 執行動作成功: {action.display_name} -> {selected_device.display_name}")
                else:
                    st.error(f"❌ {message}")
                    logger.error(f"❌ 執行動作失敗: {action.display_name} -> {selected_device.display_name}")
                
                time.sleep(1.5)
                st.session_state[f'execute_action_{action.action_id}'] = False
                st.rerun()
    
    with col2:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state[f'execute_action_{action.action_id}'] = False
            st.rerun()


def render_action_card(action: Action):
    """渲染動作卡片"""
    with st.container(border=True):
        # 頂部：標題和選單
        col1, col2 = st.columns([5, 1])
        
        with col1:
            st.markdown(f"### {action.display_name}")
            st.caption(f"類型：{action.type_name}")
        
        with col2:
            # 操作選單
            with st.popover("⋮", use_container_width=False):
                st.markdown("**操作選單**")
                
                if st.button("▶️ 執行", key=f"exec_{action.action_id}", use_container_width=True):
                    st.session_state[f'execute_action_{action.action_id}'] = True
                    st.rerun()
                
                if st.button("✏️ 編輯", key=f"edit_{action.action_id}", use_container_width=True):
                    st.session_state[f'edit_action_{action.action_id}'] = True
                    st.rerun()
                
                if st.button("📋 複製", key=f"copy_{action.action_id}", use_container_width=True):
                    new_action = st.session_state.action_registry.duplicate_action(action.action_id)
                    if new_action:
                        st.success(f"✅ 已複製：{new_action.name}")
                        time.sleep(1)
                        st.rerun()
                
                st.divider()
                
                if st.button("🗑️ 刪除", key=f"del_{action.action_id}", use_container_width=True, type="secondary"):
                    st.session_state[f'delete_action_{action.action_id}'] = True
                    st.rerun()
        
        # 動作說明
        if action.description:
            st.markdown(f"*{action.description}*")
        
        # 參數預覽
        if action.params:
            with st.expander("📋 參數詳情"):
                for key, value in action.params.items():
                    if value:  # 只顯示非空值
                        st.text(f"{key}: {value}")
        
        # 統計資訊
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("執行次數", action.execution_count)
        
        with col2:
            success_rate = action.success_rate
            st.metric("成功率", f"{success_rate:.0f}%")
        
        with col3:
            if action.last_executed_at:
                from datetime import datetime
                time_diff = datetime.now() - action.last_executed_at
                if time_diff.days > 0:
                    last_exec = f"{time_diff.days} 天前"
                elif time_diff.seconds >= 3600:
                    last_exec = f"{time_diff.seconds // 3600} 小時前"
                elif time_diff.seconds >= 60:
                    last_exec = f"{time_diff.seconds // 60} 分鐘前"
                else:
                    last_exec = "剛剛"
                st.caption(f"最後執行：{last_exec}")


def main():
    """主函式"""
    st.title("⚡ 動作管理")
    st.caption("建立和管理可重複使用的設備動作")
    
    # 頂部操作列
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # 搜索
        search_keyword = st.text_input(
            "🔍 搜索動作",
            value=st.session_state.search_keyword,
            placeholder="輸入關鍵字...",
            label_visibility="collapsed"
        )
        st.session_state.search_keyword = search_keyword
    
    with col2:
        # 類型篩選
        filter_options = ["全部"] + [ACTION_TYPE_NAMES[t] for t in ActionType]
        filter_type = st.selectbox(
            "類型篩選",
            options=filter_options,
            index=filter_options.index(st.session_state.filter_type) if st.session_state.filter_type in filter_options else 0,
            label_visibility="collapsed"
        )
        st.session_state.filter_type = filter_type
    
    with col3:
        if st.button("➕ 新增動作", use_container_width=True, type="primary"):
            st.session_state.show_add_action_dialog = True
            st.session_state.new_action_type = ActionType.WAKE_UP  # 重置為第一個類型
            st.rerun()
    
    st.markdown("---")
    
    # 獲取動作列表
    if search_keyword:
        actions = st.session_state.action_registry.search_actions(search_keyword)
    else:
        actions = st.session_state.action_registry.get_all_actions()
    
    # 類型篩選
    if filter_type != "全部":
        # 找到對應的 ActionType
        selected_type = next((t for t in ActionType if ACTION_TYPE_NAMES[t] == filter_type), None)
        if selected_type:
            actions = [a for a in actions if a.action_type == selected_type]
    
    # 顯示統計
    if actions:
        col1, col2, col3, col4 = st.columns(4)
        
        total_actions = len(actions)
        total_executions = sum(a.execution_count for a in actions)
        total_success = sum(a.success_count for a in actions)
        overall_success_rate = (total_success / total_executions * 100) if total_executions > 0 else 0
        
        col1.metric("📊 動作總數", total_actions)
        col2.metric("⚡ 總執行次數", total_executions)
        col3.metric("✅ 成功次數", total_success)
        col4.metric("📈 整體成功率", f"{overall_success_rate:.0f}%")
        
        st.markdown("---")
    
    # 顯示動作列表
    if not actions:
        if search_keyword:
            st.info(f"🔍 沒有找到包含「{search_keyword}」的動作")
        else:
            st.info("📝 還沒有任何動作，點擊「新增動作」開始創建")
    else:
        # 使用網格佈局（每行 2 個卡片）
        for i in range(0, len(actions), 2):
            cols = st.columns(2)
            
            for j, col in enumerate(cols):
                if i + j < len(actions):
                    with col:
                        render_action_card(actions[i + j])
    
    # 處理對話框
    if st.session_state.get('show_add_action_dialog'):
        add_action_dialog()
    
    for action in actions:
        if st.session_state.get(f'edit_action_{action.action_id}'):
            edit_action_dialog(action)
        
        if st.session_state.get(f'delete_action_{action.action_id}'):
            delete_action_dialog(action)
        
        if st.session_state.get(f'execute_action_{action.action_id}'):
            execute_action_dialog(action)


if __name__ == "__main__":
    main()
