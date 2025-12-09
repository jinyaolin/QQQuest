"""
系統設定頁面
"""
import streamlit as st
from config.settings import (
    get_user_config, 
    save_user_config,
    SCRCPY_CONFIG,
    SCREENSHOT_CONFIG,
    NETWORK_MONITORING_CONFIG
)
from utils.logger import get_logger

logger = get_logger(__name__)

# 設定頁面
st.set_page_config(
    page_title="系統設定 - QQQuest",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ 系統設定")
st.markdown("---")


def main():
    """主函式"""
    
    # 載入當前設定
    if 'user_config' not in st.session_state:
        st.session_state.user_config = get_user_config()
    
    # 創建標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(["📺 scrcpy 監看設定", "📸 截圖預覽設定", "🌐 網路監控設定", "💾 匯入/匯出"])
    
    # === scrcpy 監看設定 ===
    with tab1:
        st.header("📺 scrcpy 監看設定")
        st.markdown("設定點擊「監看設備」時啟動 scrcpy 的參數")
        st.markdown("---")
        
        scrcpy_config = st.session_state.user_config.get('scrcpy', SCRCPY_CONFIG.copy())
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎬 視訊設定")
            
            # 位元率
            bitrate_options = ["2M", "4M", "8M", "16M", "32M"]
            current_bitrate = scrcpy_config.get('bitrate', '8M')
            if current_bitrate not in bitrate_options:
                bitrate_options.append(current_bitrate)
                bitrate_options.sort()
            
            bitrate_index = bitrate_options.index(current_bitrate)
            scrcpy_config['bitrate'] = st.selectbox(
                "視訊位元率",
                options=bitrate_options,
                index=bitrate_index,
                help="較高的位元率提供更好的畫質，但需要更多頻寬"
            )
            
            # 最大畫面寬度
            scrcpy_config['max_size'] = st.number_input(
                "最大畫面寬度（像素）",
                min_value=480,
                max_value=3840,
                value=scrcpy_config.get('max_size', 1024),
                step=128,
                help="限制視訊寬度，0 表示無限制"
            )
            
            # 最大幀率
            scrcpy_config['max_fps'] = st.number_input(
                "最大幀率（FPS）",
                min_value=0,
                max_value=120,
                value=scrcpy_config.get('max_fps', 60),
                step=10,
                help="限制幀率，0 表示無限制"
            )
            
            # 渲染驅動
            render_drivers = ["自動", "opengl", "opengles2", "opengles", "metal", "software"]
            current_driver = scrcpy_config.get('render_driver') or "自動"
            driver_index = render_drivers.index(current_driver) if current_driver in render_drivers else 0
            
            selected_driver = st.selectbox(
                "渲染驅動",
                options=render_drivers,
                index=driver_index,
                help="選擇渲染驅動，一般使用自動即可"
            )
            scrcpy_config['render_driver'] = None if selected_driver == "自動" else selected_driver
        
        with col2:
            st.subheader("🪟 視窗設定")
            
            # 視窗寬度
            window_width = scrcpy_config.get('window_width')
            use_custom_width = st.checkbox(
                "自訂視窗寬度",
                value=window_width is not None,
                help="不勾選則自動根據畫面大小調整"
            )
            if use_custom_width:
                scrcpy_config['window_width'] = st.number_input(
                    "視窗寬度（像素）",
                    min_value=320,
                    max_value=3840,
                    value=window_width if window_width else 800,
                    step=50
                )
            else:
                scrcpy_config['window_width'] = None
            
            # 視窗高度
            window_height = scrcpy_config.get('window_height')
            use_custom_height = st.checkbox(
                "自訂視窗高度",
                value=window_height is not None,
                help="不勾選則自動根據畫面大小調整"
            )
            if use_custom_height:
                scrcpy_config['window_height'] = st.number_input(
                    "視窗高度（像素）",
                    min_value=240,
                    max_value=2160,
                    value=window_height if window_height else 600,
                    step=50
                )
            else:
                scrcpy_config['window_height'] = None
            
            # 視窗位置
            window_x = scrcpy_config.get('window_x')
            use_custom_position = st.checkbox(
                "自訂視窗位置",
                value=window_x is not None,
                help="不勾選則由系統自動決定"
            )
            if use_custom_position:
                col_x, col_y = st.columns(2)
                with col_x:
                    scrcpy_config['window_x'] = st.number_input(
                        "X 座標",
                        min_value=0,
                        max_value=5000,
                        value=window_x if window_x is not None else 100,
                        step=10
                    )
                with col_y:
                    window_y = scrcpy_config.get('window_y')
                    scrcpy_config['window_y'] = st.number_input(
                        "Y 座標",
                        min_value=0,
                        max_value=5000,
                        value=window_y if window_y is not None else 100,
                        step=10
                    )
            else:
                scrcpy_config['window_x'] = None
                scrcpy_config['window_y'] = None
        
        st.markdown("---")
        
        # 布林選項
        st.subheader("🔧 其他選項")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            scrcpy_config['stay_awake'] = st.checkbox(
                "保持設備清醒",
                value=scrcpy_config.get('stay_awake', True),
                help="監看時保持設備螢幕常亮"
            )
            scrcpy_config['show_touches'] = st.checkbox(
                "顯示觸控點",
                value=scrcpy_config.get('show_touches', False),
                help="在畫面上顯示觸控位置"
            )
        
        with col2:
            scrcpy_config['fullscreen'] = st.checkbox(
                "全螢幕模式",
                value=scrcpy_config.get('fullscreen', False),
                help="以全螢幕模式啟動"
            )
            scrcpy_config['always_on_top'] = st.checkbox(
                "視窗置頂",
                value=scrcpy_config.get('always_on_top', False),
                help="視窗永遠在最上層"
            )
        
        with col3:
            scrcpy_config['turn_screen_off'] = st.checkbox(
                "關閉設備螢幕",
                value=scrcpy_config.get('turn_screen_off', False),
                help="鏡像時關閉設備螢幕（節省電力）"
            )
            scrcpy_config['enable_audio'] = st.checkbox(
                "啟用音訊轉發",
                value=scrcpy_config.get('enable_audio', False),
                help="轉發設備音訊到電腦（⚠️ 可能會關閉 Quest 的內建聲音）"
            )
        
        st.session_state.user_config['scrcpy'] = scrcpy_config
    
    # === 截圖預覽設定 ===
    with tab2:
        st.header("📸 截圖預覽設定")
        st.markdown("設定設備卡片上的截圖預覽功能")
        st.markdown("---")
        
        screenshot_config = st.session_state.user_config.get('screenshot', SCREENSHOT_CONFIG.copy())
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚙️ 基本設定")
            
            # 啟用預覽
            screenshot_config['enabled'] = st.checkbox(
                "啟用截圖預覽",
                value=screenshot_config.get('enabled', True),
                help="在設備卡片上顯示即時截圖預覽"
            )
            
            # 更新頻率
            update_interval = screenshot_config.get('update_interval', 5)
            screenshot_config['update_interval'] = st.select_slider(
                "更新頻率（秒）",
                options=[1, 2, 3, 5, 7, 10],
                value=update_interval if update_interval in [1, 2, 3, 5, 7, 10] else 5,
                help="截圖自動更新的時間間隔（秒）"
            )
            
            # 快取
            screenshot_config['cache_enabled'] = st.checkbox(
                "啟用快取",
                value=screenshot_config.get('cache_enabled', True),
                help="啟用快取可減少 ADB 命令執行次數"
            )
        
        with col2:
            st.subheader("🖼️ 圖片設定")
            
            # 最大寬度
            screenshot_config['max_width'] = st.number_input(
                "預覽圖最大寬度（像素）",
                min_value=100,
                max_value=800,
                value=screenshot_config.get('max_width', 300),
                step=50,
                help="預覽圖的最大寬度"
            )
            
            # 最大高度
            screenshot_config['max_height'] = st.number_input(
                "預覽圖最大高度（像素）",
                min_value=100,
                max_value=600,
                value=screenshot_config.get('max_height', 200),
                step=50,
                help="預覽圖的最大高度"
            )
            
            # 品質
            screenshot_config['quality'] = st.slider(
                "JPEG 品質",
                min_value=10,
                max_value=100,
                value=screenshot_config.get('quality', 80),
                step=10,
                help="較高品質提供更清晰的圖片，但檔案較大"
            )
        
        st.session_state.user_config['screenshot'] = screenshot_config
        
        # 預覽效果說明
        if screenshot_config['enabled']:
            st.info(
                f"ℹ️ 截圖預覽將每 **{screenshot_config['update_interval']} 秒**自動更新，"
                f"最大尺寸為 **{screenshot_config['max_width']}x{screenshot_config['max_height']}** 像素"
            )
        else:
            st.warning("⚠️ 截圖預覽已停用，設備卡片將不會顯示即時截圖")
    
    # === 網路監控設定 ===
    with tab3:
        st.header("🌐 網路監控設定")
        st.markdown("設定網路監控和自動連接功能")
        st.markdown("---")
        
        network_config = st.session_state.user_config.get('network_monitoring', NETWORK_MONITORING_CONFIG.copy())
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📡 基本設定")
            
            network_config['enabled'] = st.checkbox(
                "啟用網路監控",
                value=network_config.get('enabled', True),
                help="啟用後系統會定期 Ping 設備以監控網路狀況"
            )
            
            network_config['ping_interval'] = st.slider(
                "Ping 間隔（秒）",
                min_value=5,
                max_value=60,
                value=network_config.get('ping_interval', 10),
                help="每隔多少秒 Ping 一次設備"
            )
            
            network_config['ping_timeout'] = st.slider(
                "Ping 超時（秒）",
                min_value=1,
                max_value=5,
                value=network_config.get('ping_timeout', 2),
                help="Ping 請求的超時時間"
            )
        
        with col2:
            st.subheader("🎯 Ping 目標")
            
            ping_targets = network_config.get('ping_targets', {})
            
            ping_targets['all_devices'] = st.checkbox(
                "Ping 所有設備",
                value=ping_targets.get('all_devices', False),
                help="對所有設備進行 Ping（包括已連接的設備）"
            )
            
            ping_targets['only_not_connected'] = st.checkbox(
                "僅 Ping 未連接設備",
                value=ping_targets.get('only_not_connected', True),
                help="僅對未連接的設備進行 Ping"
            )
            
            ping_targets['only_wifi_devices'] = st.checkbox(
                "僅 Ping WiFi 設備",
                value=ping_targets.get('only_wifi_devices', True),
                help="僅對 WiFi 連接的設備進行 Ping（USB 設備不需要 Ping）"
            )
            
            network_config['ping_targets'] = ping_targets
        
        st.markdown("---")
        
        st.subheader("🔄 自動連接")
        
        network_config['auto_connect'] = st.checkbox(
            "啟用自動連接",
            value=network_config.get('auto_connect', True),
            help="當設備 Ping 通但未連接時，自動嘗試連接"
        )
        
        if network_config['auto_connect']:
            col1, col2 = st.columns(2)
            
            with col1:
                network_config['auto_connect_max_retries'] = st.number_input(
                    "最大重試次數",
                    min_value=1,
                    max_value=10,
                    value=network_config.get('auto_connect_max_retries', 3),
                    help="自動連接失敗後的最大重試次數"
                )
            
            with col2:
                network_config['auto_connect_cooldown'] = st.number_input(
                    "失敗後冷卻時間（秒）",
                    min_value=10,
                    max_value=300,
                    value=network_config.get('auto_connect_cooldown', 30),
                    help="連接失敗後等待多少秒再重試"
                )
        else:
            network_config['auto_connect_max_retries'] = network_config.get('auto_connect_max_retries', 3)
            network_config['auto_connect_cooldown'] = network_config.get('auto_connect_cooldown', 30)
        
        st.session_state.user_config['network_monitoring'] = network_config
        
        st.markdown("---")
        
        with st.expander("ℹ️ 使用說明"):
            st.markdown("""
            ### 網路監控功能說明
            
            1. **Ping 監控**
               - 系統會定期 Ping 設備的 IP 地址
               - 記錄響應時間來評估網路品質
               - 只有 WiFi 連接的設備需要 Ping
            
            2. **自動連接**
               - 當設備 Ping 通但未連接時，自動嘗試連接
               - 如果連接失敗，會重試指定次數
               - 超過重試次數後，標記為「無法連線」（需要手動開啟 WiFi ADB）
            
            3. **設備狀態**
               - **在線**：已連接並可用
               - **離線**：已連接但狀態異常
               - **未連接**：Ping 不通，設備可能關機
               - **無法連線**：Ping 通但無法連接（WiFi ADB 未開啟）
            """)
    
    # === 匯入/匯出設定 ===
    with tab4:
        st.header("💾 匯入/匯出設定")
        st.markdown("備份或恢復您的系統設定")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 匯出設定")
            st.markdown("將當前設定匯出為 JSON 檔案")
            
            import json
            config_json = json.dumps(st.session_state.user_config, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="📥 下載設定檔",
                data=config_json,
                file_name="qqquest_config.json",
                mime="application/json",
                help="下載當前設定為 JSON 檔案"
            )
            
            # 顯示當前設定
            with st.expander("📋 查看當前設定"):
                st.code(config_json, language="json")
        
        with col2:
            st.subheader("📥 匯入設定")
            st.markdown("從 JSON 檔案恢復設定")
            
            uploaded_file = st.file_uploader(
                "選擇設定檔",
                type=["json"],
                help="選擇先前匯出的 JSON 設定檔"
            )
            
            if uploaded_file is not None:
                try:
                    import json
                    imported_config = json.load(uploaded_file)
                    
                    st.success("✅ 設定檔讀取成功！")
                    
                    with st.expander("📋 查看匯入的設定"):
                        st.code(json.dumps(imported_config, ensure_ascii=False, indent=2), language="json")
                    
                    if st.button("🔄 套用匯入的設定", type="primary"):
                        st.session_state.user_config = imported_config
                        if save_user_config(imported_config):
                            st.success("✅ 設定已套用並儲存！")
                            logger.info("匯入設定成功")
                            st.balloons()
                        else:
                            st.error("❌ 儲存設定失敗！")
                            logger.error("儲存匯入的設定失敗")
                
                except Exception as e:
                    st.error(f"❌ 讀取設定檔失敗: {e}")
                    logger.error(f"匯入設定失敗: {e}")
        
        st.markdown("---")
        
        # 重置為預設設定
        st.subheader("🔄 重置設定")
        st.markdown("將所有設定恢復為預設值")
        
        if st.button("⚠️ 重置為預設設定", type="secondary"):
            default_config = {
                "scrcpy": SCRCPY_CONFIG.copy(),
                "screenshot": SCREENSHOT_CONFIG.copy(),
                "network_monitoring": NETWORK_MONITORING_CONFIG.copy(),
            }
            st.session_state.user_config = default_config
            if save_user_config(default_config):
                st.success("✅ 已重置為預設設定！")
                logger.info("重置為預設設定")
                st.rerun()
            else:
                st.error("❌ 重置失敗！")
                logger.error("重置設定失敗")
    
    # === 儲存按鈕 ===
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        if st.button("💾 儲存設定", type="primary", use_container_width=True):
            if save_user_config(st.session_state.user_config):
                st.success("✅ 設定已儲存！")
                logger.info("儲存使用者設定成功")
            else:
                st.error("❌ 儲存失敗！")
                logger.error("儲存使用者設定失敗")
    
    with col3:
        if st.button("🔄 重新載入", use_container_width=True):
            st.session_state.user_config = get_user_config()
            st.success("✅ 已重新載入設定！")
            logger.info("重新載入設定")
            st.rerun()


if __name__ == "__main__":
    main()

