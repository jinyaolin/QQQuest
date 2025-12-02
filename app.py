"""
QQQuest - Quest 設備同步管理系統
主程式入口
"""
import streamlit as st
from config.settings import STREAMLIT_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)

# 設定頁面配置
st.set_page_config(**STREAMLIT_CONFIG)

# 初始化 session state
from utils.init import ensure_initialization

if not ensure_initialization():
    st.stop()

# 主頁面
def main():
    st.title("🎮 QQQuest - Quest 設備同步管理系統")
    
    st.markdown("""
    ## 歡迎使用 QQQuest！
    
    這是一個基於 ADB 和 scrcpy 的 Quest 設備群組管理系統，支援多設備同步控制、時間碼同步和操作排程。
    
    ### 功能特色
    
    - 📱 **設備管理**：WiFi ADB 連接、設備狀態監控
    - 🏠 **房間管理**：創建房間、設備分配、批量控制
    - ⚡ **動作管理**：預設動作（休眠、開啟/關閉程式、傳送訊息）
    - ⏱️ **時間碼同步**：房間時間碼、高精度設備同步
    - 📅 **CUE 排程**：時間軸編輯、自動執行操作序列
    - 🖥️ **scrcpy 整合**：多設備螢幕鏡像
    
    ### 快速開始
    
    1. 前往 **📱 設備管理** 頁面連接你的 Quest 設備
    2. 在 **🏠 房間管理** 頁面建立房間並分配設備
    3. 使用 **⚡ 動作管理** 頁面設定和執行操作
    
    ---
    
    ### 系統狀態
    """)
    
    # 顯示系統狀態
    col1, col2, col3 = st.columns(3)
    
    with col1:
        devices = st.session_state.device_registry.get_all_devices()
        online_devices = len([d for d in devices if d.is_online])
        st.metric("設備總數", len(devices))
    
    with col2:
        st.metric("在線設備", online_devices)
    
    with col3:
        # 房間數量（暫時顯示 0，等實作房間功能後更新）
        st.metric("房間數量", 0)
    
    # 快速操作
    st.markdown("### 快速操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📱 管理設備", use_container_width=True):
            st.switch_page("pages/1_📱_設備管理.py")
    
    with col2:
        if st.button("🏠 管理房間", use_container_width=True, disabled=True):
            # TODO: 實作房間管理後啟用
            st.info("房間管理功能開發中...")
    
    with col3:
        if st.button("⚡ 管理動作", use_container_width=True, disabled=True):
            # TODO: 實作動作管理後啟用
            st.info("動作管理功能開發中...")
    
    # 最近活動（TODO: 實作日誌系統後顯示）
    st.markdown("### 最近活動")
    st.info("暫無活動記錄")
    
    # 頁尾
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "QQQuest v1.0.0 | "
        "Made with ❤️ by QQQuest Team"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

