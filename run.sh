#!/bin/bash
# QQQuest 啟動腳本

echo "🎮 正在啟動 QQQuest..."

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 未安裝"
    exit 1
fi

# 檢查 ADB
if ! command -v adb &> /dev/null; then
    echo "⚠️  警告：ADB 未安裝或不在 PATH 中"
    echo "請安裝 Android Platform Tools"
fi

# 檢查虛擬環境
if [ ! -d "venv" ]; then
    echo "📦 建立虛擬環境..."
    python3 -m venv venv
fi

# 啟動虛擬環境
echo "🔧 啟動虛擬環境..."
source venv/bin/activate

# 升級 pip
echo "⬆️  升級 pip..."
python3 -m pip install --upgrade pip -q

# 安裝相依套件
echo "📥 安裝相依套件..."
pip install -r requirements.txt

# 啟動應用程式
echo "🚀 啟動 QQQuest..."
streamlit run app.py


