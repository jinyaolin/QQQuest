# 🔧 安裝問題修復指南

## 問題說明

由於部分 Python 套件版本問題，需要手動修復安裝。

## 快速修復步驟

### 1. 清除舊的虛擬環境

```bash
cd /Users/jinyaolin/QQquest
rm -rf venv
```

### 2. 重新建立虛擬環境

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 升級 pip

```bash
python3 -m pip install --upgrade pip
```

### 4. 安裝相依套件

```bash
pip install -r requirements.txt
```

如果仍有錯誤，可以逐個安裝核心套件：

```bash
pip install streamlit
pip install adb-shell
pip install pydantic
pip install tinydb
pip install loguru
pip install streamlit-autorefresh
pip install python-dotenv
```

### 5. 啟動應用程式

```bash
streamlit run app.py
```

---

## 完整安裝腳本（一鍵執行）

複製以下命令到終端執行：

```bash
cd /Users/jinyaolin/QQquest && \
rm -rf venv && \
python3 -m venv venv && \
source venv/bin/activate && \
python3 -m pip install --upgrade pip && \
pip install streamlit adb-shell pydantic tinydb loguru streamlit-autorefresh python-dotenv && \
echo "✅ 安裝完成！現在可以執行：streamlit run app.py"
```

---

## 檢查安裝

確認所有套件已正確安裝：

```bash
source venv/bin/activate
python3 -c "
import streamlit
import adb_shell
import pydantic
import tinydb
import loguru
from streamlit_autorefresh import st_autorefresh
print('✅ 所有套件已正確安裝！')
"
```

---

## 最小化安裝（如果仍有問題）

只安裝最核心的套件：

```bash
pip install streamlit adb-shell tinydb loguru
```

然後修改程式碼，註釋掉暫時不需要的功能。

---

## 驗證 ADB

確保 ADB 已安裝：

```bash
adb version
```

如果未安裝，請執行：

```bash
# macOS
brew install android-platform-tools

# Linux
sudo apt-get install android-tools-adb
```

---

## 啟動系統

安裝完成後：

```bash
cd /Users/jinyaolin/QQquest
source venv/bin/activate
streamlit run app.py
```

系統會自動在瀏覽器開啟 `http://localhost:8501`

---

## 常見錯誤解決

### 錯誤 1: `command not found: streamlit`

**原因**: 虛擬環境未啟動或 streamlit 未安裝

**解決**:
```bash
source venv/bin/activate
pip install streamlit
```

### 錯誤 2: `No module named 'streamlit_autorefresh'`

**解決**:
```bash
pip install streamlit-autorefresh
```

如果仍失敗，可以暫時註釋掉這個功能：

編輯 `ui/pages/1_📱_設備管理.py`，找到這一行：
```python
from streamlit_autorefresh import st_autorefresh
```

註釋掉：
```python
# from streamlit_autorefresh import st_autorefresh
```

並註釋掉使用它的地方（第 26 行）：
```python
# count = st_autorefresh(interval=UI_REFRESH_INTERVAL * 1000, key="device_refresh")
```

### 錯誤 3: Python 版本過舊

**檢查 Python 版本**:
```bash
python3 --version
```

需要 Python 3.8 或以上。如果版本過舊，請升級：

```bash
# macOS
brew install python@3.11

# Linux
sudo apt-get install python3.11
```

---

## 成功標誌

當你看到這些訊息時，表示安裝成功：

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

---

## 需要幫助？

如果仍有問題：

1. 查看完整錯誤訊息
2. 檢查 Python 版本：`python3 --version`
3. 檢查 pip 版本：`pip --version`
4. 嘗試最小化安裝

**聯繫資訊**: 請提供完整錯誤訊息以便診斷

