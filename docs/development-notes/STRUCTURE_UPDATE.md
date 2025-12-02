# 📁 專案結構更新說明

## 變更原因

Streamlit 的多頁面應用要求頁面檔案必須放在與主腳本 (`app.py`) 同級的 `pages/` 目錄中。

## 新的專案結構

```
QQquest/
├── app.py                      # ✅ 主程式
├── pages/                      # ✅ Streamlit 頁面（新位置）
│   ├── 1_📱_設備管理.py
│   ├── 2_🏠_房間管理.py
│   └── 3_⚡_動作管理.py
│
├── config/                     # 配置
│   ├── settings.py
│   └── constants.py
│
├── core/                       # 核心模組
│   ├── device.py
│   ├── adb_manager.py
│   ├── device_registry.py
│   └── usb_monitor.py
│
├── ui/                         # UI 組件（保留作為組件目錄）
│   ├── components/             # 可重用的 UI 組件
│   └── pages/                  # ⚠️  已廢棄，請使用根目錄的 pages/
│
├── utils/                      # 工具
│   └── logger.py
│
├── data/                       # 資料儲存
└── logs/                       # 日誌
```

## 變更內容

1. ✅ 創建了 `/pages/` 目錄（與 app.py 同級）
2. ✅ 複製頁面檔案到新位置
3. ✅ 更新 `app.py` 中的頁面路徑

## 路徑變更

### 舊路徑（錯誤）
```python
st.switch_page("ui/pages/1_📱_設備管理.py")
```

### 新路徑（正確）
```python
st.switch_page("pages/1_📱_設備管理.py")
```

## Streamlit 多頁面規則

Streamlit 會自動識別以下位置的頁面：
- ✅ `pages/*.py` - 與 app.py 同級的 pages 目錄
- ❌ `ui/pages/*.py` - 不會被自動識別

頁面檔案命名規則：
- `1_頁面名稱.py` - 數字前綴決定順序
- `頁面名稱.py` - 按字母順序排列
- 支援 emoji 表情符號

## 側邊欄導航

Streamlit 會自動在側邊欄生成導航選單：
- 📱 設備管理
- 🏠 房間管理  
- ⚡ 動作管理

## 保留的 ui/ 目錄

`ui/` 目錄現在用於存放可重用的 UI 組件：
- `ui/components/` - 自訂 UI 組件
- `ui/pages/` - 已廢棄，可以刪除

## 如何添加新頁面

1. 在 `pages/` 目錄創建新檔案
2. 檔案名格式：`序號_emoji_名稱.py`
3. 例如：`4_🔧_系統設定.py`

範例：
```python
# pages/4_🔧_系統設定.py
import streamlit as st

st.set_page_config(
    page_title="系統設定 - QQQuest",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 系統設定")
# ... 你的程式碼
```

Streamlit 會自動將其加入側邊欄！

## 驗證結構

啟動後檢查：
1. ✅ 側邊欄顯示所有頁面
2. ✅ 點擊可以切換頁面
3. ✅ 沒有路徑錯誤

---

**結構已修復！現在可以正常使用了！** 🚀

