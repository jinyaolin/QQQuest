# 📊 QQQuest 專案狀態

**更新時間**: 2025-11-30

## ✅ Phase 1 已完成

### 核心功能
- [x] 專案結構建立
- [x] requirements.txt
- [x] 配置系統（settings, constants）
- [x] 日誌系統（Loguru）
- [x] ADB 管理器
- [x] 設備類別（Device）
- [x] 設備註冊表（Device Registry）
- [x] USB 監控器
- [x] 資料持久化（TinyDB）

### UI 頁面
- [x] 主頁面（app.py）
- [x] 設備管理頁面（完整功能）
- [x] 房間管理頁面（佔位）
- [x] 動作管理頁面（佔位）

### 功能特色
✅ **手動新增設備**
- WiFi ADB 連接
- IP:Port 輸入
- 設備資訊自動取得

✅ **USB 自動偵測**
- 背景持續掃描
- 新設備提示對話框
- 已知設備自動連接
- USB 轉 WiFi 自動化

✅ **設備管理**
- 響應式網格卡片顯示
- 設備狀態即時監控
- 電量、溫度顯示
- 低電量/高溫警告

✅ **設備操作**
- 中斷/重新連線
- 查看序號
- 編輯設定
- 移除設備

✅ **資料持久化**
- 設備序號記憶
- 連接歷史記錄
- 自動恢復設定

## 🔄 正在開發

### Phase 2：房間管理（下一步）
- [ ] 房間 CRUD 操作
- [ ] 設備分配功能
- [ ] 房間卡片視圖
- [ ] 房間內部視圖
- [ ] 批量操作

### Phase 3：動作系統
- [ ] 五大預設動作
- [ ] 動作執行引擎
- [ ] 單台/批量執行
- [ ] 自訂動作

### Phase 4：時間碼系統
- [ ] 房間時間碼
- [ ] 設備時間同步
- [ ] Cristian's Algorithm
- [ ] 同步監控

### Phase 5：CUE 排程
- [ ] CUE 編輯器
- [ ] 時間軸視覺化
- [ ] 自動執行引擎
- [ ] CUE 管理

### Phase 6：scrcpy 整合
- [ ] scrcpy 程序管理
- [ ] 單設備鏡像
- [ ] 多設備網格鏡像

## 📁 專案結構

```
QQquest/
├── app.py                          # ✅ 主程式
├── run.sh                          # ✅ 啟動腳本
├── requirements.txt                # ✅ 相依套件
├── START_HERE.md                   # ✅ 快速開始
├── FEATURES.md                     # ✅ 功能規劃
├── README.md                       # ✅ 專案說明
│
├── pages/                          # ✅ Streamlit 頁面
│   ├── 1_📱_設備管理.py            # 完整功能
│   ├── 2_🏠_房間管理.py            # 佔位
│   └── 3_⚡_動作管理.py            # 佔位
│
├── config/                         # ✅ 配置
│   ├── settings.py                 # 系統設定
│   └── constants.py                # 常數定義
│
├── core/                           # ✅ 核心模組
│   ├── device.py                   # 設備類別
│   ├── adb_manager.py              # ADB 管理
│   ├── device_registry.py          # 設備註冊表
│   └── usb_monitor.py              # USB 監控
│
├── ui/                             # ✅ UI 組件
│   └── components/                 # 可重用組件（待開發）
│
├── utils/                          # ✅ 工具
│   └── logger.py                   # 日誌系統
│
├── data/                           # ✅ 資料儲存
│   ├── devices.json                # 設備資料
│   └── device_registry.json        # 序號註冊表
│
└── logs/                           # ✅ 日誌檔案
```

## 🎯 下一步計畫

### 優先級 P0（本週）
1. 完善設備管理頁面的編輯功能
2. 實作基礎動作系統（休眠、喚醒、啟動/關閉應用）
3. 在設備卡片中加入快速動作按鈕

### 優先級 P1（下週）
1. 實作房間管理基礎功能
2. 設備分配到房間
3. 房間內批量操作

### 優先級 P2（未來）
1. 時間碼系統
2. CUE 排程編輯器
3. scrcpy 整合

## 🐛 已知問題

1. **UI 刷新**：Streamlit 的自動刷新可能導致編輯狀態丟失
   - 解決方案：使用 session_state 保存編輯狀態

2. **USB 監控**：在某些系統上可能需要調整掃描間隔
   - 解決方案：在 settings.py 中調整 ADB_SCAN_INTERVAL

3. **設備斷線**：WiFi 不穩定可能導致設備頻繁斷線
   - 解決方案：實作自動重連機制（未來）

## 📝 使用說明

### 啟動系統

```bash
# macOS/Linux
./run.sh

# 或手動啟動
streamlit run app.py
```

### 連接設備

**方式 1：USB 自動（推薦）**
1. 插入 USB
2. 系統自動偵測
3. 輸入代號
4. 自動連接

**方式 2：手動 WiFi**
1. 點擊「新增設備」
2. 輸入 IP:Port
3. 連接

### 管理設備

- 點擊卡片右上角 ⋮ 開啟選單
- 可執行動作、加入房間、編輯、移除
- 自動顯示電量和溫度
- 低電量/高溫自動警告

## 🔧 技術細節

### 核心技術
- **框架**: Streamlit 1.28+
- **ADB**: adb-shell, pure-python-adb
- **資料庫**: TinyDB (JSON)
- **日誌**: Loguru
- **驗證**: Pydantic

### 設計模式
- **單例模式**: ADB Manager
- **觀察者模式**: USB Monitor (回調函數)
- **Repository 模式**: Device Registry
- **DTO 模式**: Device (Pydantic Model)

### 資料流
```
USB 設備 → ADB Manager → USB Monitor → Device Registry
                                    ↓
                              UI (Streamlit)
                                    ↓
                           Session State → 顯示/操作
```

## 📊 統計資訊

- **總行數**: ~3000+ 行
- **模組數**: 12 個主要檔案
- **頁面數**: 3 個 Streamlit 頁面
- **類別數**: 5 個核心類別
- **開發時間**: Phase 1 已完成

## 🎓 學習資源

- [Streamlit 文件](https://docs.streamlit.io/)
- [ADB 命令參考](https://developer.android.com/studio/command-line/adb)
- [TinyDB 文件](https://tinydb.readthedocs.io/)

## 📞 支援

- 查看日誌：`logs/qqquest_*.log`
- 查看錯誤：`logs/errors_*.log`
- 配置調整：`config/settings.py`

---

**Phase 1 開發完成！準備進入 Phase 2 🚀**

