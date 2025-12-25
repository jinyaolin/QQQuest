"""
房間管理 UI 工具函數
"""
import streamlit as st
from typing import Any


def hide_dialog_close_button():
    """隱藏對話框右上角的關閉按鈕"""
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


def render_input(label: str, current_value: Any, key_suffix: str) -> Any:
    """
    根據當前值的類型渲染對應的輸入組件

    Args:
        label: 輸入框標籤
        current_value: 當前值
        key_suffix: session state key 的後綴

    Returns:
        用戶輸入的值
    """
    if isinstance(current_value, bool):
        return st.checkbox(label, value=current_value, key=f"input_{key_suffix}")
    elif isinstance(current_value, int):
        return st.number_input(label, value=current_value, key=f"input_{key_suffix}")
    elif isinstance(current_value, float):
        return st.number_input(label, value=current_value, format="%.2f", key=f"input_{key_suffix}")
    else:
        return st.text_input(label, value=str(current_value), key=f"input_{key_suffix}")
