# QQQuest - Quest 設備管理系統

> 基於 ADB 和 scrcpy 的 Quest 設備集中管理系統

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

## 📋 專案簡介

QQQuest 是一個專為 Meta Quest 設備設計的管理系統，提供透過 Wi-Fi 進行設備連接、監看、控制和批量操作的功能。

### ✨ 主要特性

- 📱 **設備管理** - 手動添加、編輯、移除設備，自動狀態同步
- 🏠 **房間管理** - 設備分組管理，批量操作
- ⚡ **動作管理** - 創建可重複使用的動作，批量執行
- 📺 **設備監看** - 使用 scrcpy 實時監看設備畫面
- ⚙️ **系統設定** - 自訂 scrcpy 和截圖參數
- 🚀 **並發處理** - 批量操作性能優化（10 倍提升）

---

## 🚀 快速開始

### 環境需求

- **作業系統**: macOS / Linux / Windows
- **Python**: 3.9 或更高版本
- **ADB**: Android Debug Bridge（用於設備連接）
- **scrcpy**: Screen copy tool（用於設備鏡像）
- **Quest 設備**: 已啟用開發者模式並連接到同一網路

### 安裝步驟

#### 1. 安裝依賴工具

**macOS (使用 Homebrew)**:
```bash
# 安裝 ADB
brew install android-platform-tools

# 安裝 scrcpy
brew install scrcpy
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install android-tools-adb scrcpy
```

**Windows**:
- 下載並安裝 [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)（包含 ADB）
- 下載並安裝 [scrcpy](https://github.com/Genymobile/scrcpy/releases)
- 將安裝目錄添加到系統 PATH

#### 2. 驗證安裝

```bash
# 檢查 ADB
adb version
# 應顯示 ADB 版本號

# 檢查 scrcpy
scrcpy --version
# 應顯示 scrcpy 版本號
```

#### 3. 設置 Quest 設備

**啟用開發者模式**:
1. 在 Quest 設備上：設定 → 系統 → 關於
2. 連續點擊「版本號」7 次
3. 返回設定 → 系統 → 開發者
4. 啟用「開發者模式」

**啟用 Wi-Fi ADB**:

**方法 1: 透過 USB（首次設定）**
```bash
# 1. 用 USB 連接 Quest 到電腦
# 2. 在 Quest 中確認「允許 USB 調試」
# 3. 執行以下命令啟用 TCP/IP 模式
adb tcpip 5555

# 4. Quest裡面還要允許一次USB調試，之後可以拔除 USB 線

# 5. 透過 Wi-Fi 連接（替換成您的 Quest IP）
adb connect 192.168.1.XXX:5555

# 6. Quest裡面還需要允許一次Debug，驗證連接
adb devices
# 應顯示您的設備 192.168.1.xxx:5555 device
```

**方法 2: 透過 Quest 設定（Quest 3）**
1. 設定 → 系統 → 開發者 → 無線調試
2. 啟用「無線調試」
3. 記下 IP 地址和端口

#### 4. 安裝 QQQuest

```bash
# 複製專案（或下載 ZIP 並解壓）
git clone <your-repo-url>
cd QQquest

# 賦予執行權限
chmod +x run.sh

# 啟動應用（會自動創建虛擬環境並安裝依賴）
./run.sh
```

**首次執行時，`run.sh` 會自動**:
- ✅ 創建 Python 虛擬環境（`venv/`）
- ✅ 升級 pip 到最新版本
- ✅ 安裝所有 Python 依賴（見 `requirements.txt`）
- ✅ 啟動 Streamlit 應用

#### 5. 訪問應用

瀏覽器會自動打開 `http://localhost:8501`

如果沒有自動打開，請手動訪問該地址。

---

## 📦 依賴套件

### Python 依賴

所有依賴已列在 `requirements.txt` 中：

```
streamlit>=1.28.0          # Web 應用框架
pydantic>=2.0.0            # 資料驗證
tinydb>=4.8.0              # 輕量級資料庫
loguru>=0.7.0              # 日誌工具
pillow>=10.0.0             # 圖像處理
streamlit-autorefresh>=0.0.1  # 自動刷新組件
adb-shell>=0.4.4           # ADB Python 封裝
python-dotenv>=1.0.0       # 環境變數管理
```

### 外部工具

- **ADB** (Android Debug Bridge) - 設備連接和控制
- **scrcpy** - 設備鏡像和遠程控制

---

## 🛠️ 手動安裝（不使用 run.sh）

如果您想手動安裝：

```bash
# 1. 創建虛擬環境
python3 -m venv venv

# 2. 啟動虛擬環境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 3. 升級 pip
pip install --upgrade pip

# 4. 安裝依賴
pip install -r requirements.txt

# 5. 啟動應用
streamlit run app.py
```

---

## 📖 使用指南

### 1. 添加設備

1. 進入「📱 設備管理」頁面
2. 點擊右上角「➕ 新增設備」
3. 輸入 Quest 的 IP 地址（例如：`192.168.1.100`）
4. 輸入 Port（預設：`5555`）
5. 輸入設備代號（選填，例如：`Q01`）
6. 點擊「🔌 連接」

### 2. 監看設備

1. 在設備卡片上，點擊「⋮」菜單
2. 選擇「📺 監看設備」
3. scrcpy 視窗會自動開啟
4. 可使用鍵盤和滑鼠控制設備

### 3. 管理房間

1. 進入「🏠 房間管理」頁面
2. 點擊「➕ 新增房間」
3. 設定房間名稱、說明和最大設備數量
4. 在房間卡片中點擊「➕ 管理設備」添加設備

### 4. 創建動作

1. 進入「⚡ 動作管理」頁面
2. 點擊「➕ 新增動作」
3. 選擇動作類型（喚醒、休眠、執行程式等）
4. 設定動作參數
5. 保存動作

### 5. 批量操作

1. 在房間管理中，選擇房間
2. 點擊「⚡ 執行動作」
3. 選擇要執行的動作
4. 系統會並發執行到所有在線設備

---

## 🐛 故障排除

### 問題 1: 無法連接設備

**症狀**: 添加設備時顯示連接失敗

**解決方法**:
```bash
# 1. 檢查設備和電腦是否在同一網路
ping <Quest_IP>

# 2. 檢查 Quest 的 IP 地址
# 設定 → Wi-Fi → 點擊已連接的網路

# 3. 嘗試手動連接
adb connect <Quest_IP>:5555
adb devices  # 確認設備已連接

# 4. 如果連接失敗，檢查防火牆設置
```

### 問題 2: scrcpy 無法啟動

**症狀**: 點擊「監看設備」後 scrcpy 視窗未開啟

**解決方法**:
```bash
# 1. 檢查 scrcpy 是否正確安裝
scrcpy --version

# 2. 嘗試手動啟動 scrcpy
scrcpy -s <Quest_IP>:5555 --no-audio

# 3. 查看日誌獲取錯誤訊息
cat logs/qqquest_*.log

# 4. 檢查設備是否在線
adb devices
```

### 問題 3: 設備顯示離線但實際已連接

**症狀**: 設備在 `adb devices` 中顯示但在 QQQuest 中顯示離線

**解決方法**:
1. 點擊設備的「⋮」菜單
2. 選擇「🔌 重新連線」
3. 或重新整理頁面（頁面會自動同步狀態）

### 問題 4: Quest 聲音消失

**原因**: scrcpy 預設會轉發音訊

**解決方法**:
- QQQuest 已預設禁用音訊轉發（添加 `--no-audio` 參數）
- 如需手動確認，前往「⚙️ 系統設定」檢查「啟用音訊轉發」是否未勾選

### 問題 5: Python 版本不兼容

**症狀**: 安裝依賴時出現錯誤

**解決方法**:
```bash
# 檢查 Python 版本
python3 --version  # 應為 3.9 或更高

# 如果版本過低，請升級 Python
# macOS: brew install python@3.11
# Linux: sudo apt install python3.11
# Windows: 從 python.org 下載安裝
```

### 問題 6: 虛擬環境問題

**症狀**: 無法啟動虛擬環境

**解決方法**:
```bash
# 刪除舊的虛擬環境
rm -rf venv  # macOS/Linux
rmdir /s venv  # Windows

# 重新創建
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

---

## 📁 專案結構

```
QQquest/
├── app.py                    # 主應用程式入口
├── run.sh                    # 啟動腳本
├── requirements.txt          # Python 依賴
├── VERSION                   # 版本號
├── README.md                 # 本檔案（安裝指南）
├── FEATURES.md               # 系統功能說明
├── DEVELOPMENT_LOG.md        # 開發日記
├── CHANGELOG.md              # 更新日誌
│
├── config/                   # 配置模組
│   ├── settings.py          # 系統設定
│   └── constants.py         # 常量定義
│
├── core/                     # 核心功能模組
│   ├── device.py            # 設備資料模型
│   ├── device_registry.py   # 設備註冊管理
│   ├── room.py              # 房間資料模型
│   ├── room_registry.py     # 房間管理
│   ├── action.py            # 動作資料模型
│   ├── action_registry.py   # 動作管理
│   └── adb_manager.py       # ADB 命令管理
│
├── pages/                    # Streamlit 頁面
│   ├── 1_📱_設備管理.py
│   ├── 2_🏠_房間管理.py
│   ├── 3_⚡_動作管理.py
│   └── 4_⚙️_系統設定.py
│
├── utils/                    # 工具模組
│   ├── init.py              # 系統初始化
│   └── logger.py            # 日誌工具
│
├── data/                     # 資料儲存目錄
│   ├── device_registry.json
│   ├── action_registry.json
│   ├── room_registry.json
│   └── user_config.json
│
├── logs/                     # 日誌檔案目錄
└── docs/                     # 文件目錄
    └── development-notes/   # 開發筆記
```

---

## ⚙️ 設定說明

### 資料儲存位置

- 設備資料: `data/device_registry.json`
- 動作資料: `data/action_registry.json`
- 房間資料: `data/room_registry.json`
- 使用者設定: `data/user_config.json`
- 日誌檔案: `logs/`

### 設定檔案格式

**user_config.json**:
```json
{
  "scrcpy": {
    "bitrate": "8M",
    "max_size": 1024,
    "max_fps": 60,
    "enable_audio": false,
    "window_x": 0,
    "window_y": 0,
    "window_width": 0,
    "window_height": 0
  },
  "screenshot": {
    "enabled": true,
    "update_interval": 5,
    "width": 320,
    "height": 240,
    "quality": 80
  }
}
```

---

## 🔄 更新日誌

詳細的更新日誌請參見 [CHANGELOG.md](CHANGELOG.md)

### 當前版本: v1.0.0

**主要功能**:
- ✅ 設備管理（添加、編輯、移除、排序）
- ✅ 房間管理（分組、批量操作）
- ✅ 動作管理（7 種動作類型）
- ✅ 設備監看（scrcpy 集成）
- ✅ 系統設定（參數配置）
- ✅ 並發處理優化（10 倍性能提升）

---

## 📚 相關文件

- [**FEATURES.md**](FEATURES.md) - 完整系統功能說明
- [**DEVELOPMENT_LOG.md**](DEVELOPMENT_LOG.md) - 開發日記
- [**CHANGELOG.md**](CHANGELOG.md) - 詳細更新日誌
- [**docs/DOCUMENTATION_STRUCTURE.md**](docs/DOCUMENTATION_STRUCTURE.md) - 文檔結構說明

---

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

### 貢獻指南

1. Fork 本專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

---

## 📄 授權

本專案採用 [MIT License](LICENSE) 授權。

---

## 🙏 致謝

- [Streamlit](https://streamlit.io/) - Web 應用框架
- [scrcpy](https://github.com/Genymobile/scrcpy) - Android 設備鏡像工具
- [Android Debug Bridge](https://developer.android.com/tools/adb) - Android 調試工具
- [Pydantic](https://pydantic.dev/) - 資料驗證庫
- [TinyDB](https://tinydb.readthedocs.io/) - 輕量級資料庫

---

**專案維護**: QQQuest Team  
**版本**: v1.0.0  
**最後更新**: 2025-12-02
