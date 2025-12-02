# 动作管理设计分析与建议

## 📋 用户规划

### 动作类型
1. **唤醒** - 如果设备在休眠中会被唤醒
2. **休眠** - 如果在唤醒中可以进入休眠
3. **执行程式** - 需要 package 和 activity 名称
4. **关闭程式** - 需要 package

### 核心需求
- 用户可以为每个动作命名
- 每种动作的参数不同
- 可重复使用定义好的动作

---

## ✅ 规划评估

### 优点
1. ✅ **功能覆盖合理** - 四种动作涵盖最常见的需求
2. ✅ **由简入繁** - 先实现单设备动作，再扩展到批量操作
3. ✅ **参数化设计** - 灵活且可扩展
4. ✅ **可命名** - 提高可管理性

### 建议改进
以下是基于 Quest 设备特性和 ADB 命令的建议：

---

## 🔧 各动作类型详细分析

### 1. 唤醒（Wake Up）

#### ADB 命令
```bash
# 检查设备是否休眠
adb shell dumpsys power | grep "Display Power: state="

# 唤醒设备
adb shell input keyevent KEYCODE_WAKEUP
# 或
adb shell input keyevent 224

# 解锁屏幕（如果需要）
adb shell input keyevent 82  # KEYCODE_MENU
```

#### 建议参数
```python
{
    "type": "wake_up",
    "name": "唤醒设备",
    "params": {
        "unlock": False,  # 是否同时解锁（可选）
        "verify": True    # 是否验证唤醒成功（可选）
    }
}
```

#### ⚠️ 注意事项
1. **状态检查**: 建议先检查设备是否已唤醒，避免重复操作
2. **解锁问题**: Quest 通常没有锁屏，但如果有，需要解锁逻辑
3. **验证**: 可以通过 `dumpsys power` 验证是否成功唤醒

---

### 2. 休眠（Sleep）

#### ADB 命令
```bash
# 让设备进入休眠
adb shell input keyevent KEYCODE_POWER
# 或
adb shell input keyevent 26

# 强制休眠（备用方案）
adb shell input keyevent KEYCODE_SLEEP
# 或
adb shell input keyevent 223
```

#### 建议参数
```python
{
    "type": "sleep",
    "name": "休眠设备",
    "params": {
        "force": False,   # 是否强制休眠（可选）
        "verify": True    # 是否验证休眠成功（可选）
    }
}
```

#### ⚠️ 注意事项
1. **应用状态**: 休眠前建议检查是否有重要应用在运行
2. **网络连接**: 休眠后可能断开 Wi-Fi，需要重新唤醒才能连接
3. **ADB 连接**: 休眠后 ADB 连接可能中断，需要重新建立
4. **验证**: 可以通过 `dumpsys power` 验证是否成功休眠

---

### 3. 执行程式（Launch App）

#### ADB 命令
```bash
# 方法 1: 完整启动（推荐）
adb shell am start -n com.package.name/.ActivityName

# 方法 2: 使用 intent
adb shell am start -a android.intent.action.MAIN -n com.package.name/.ActivityName

# 方法 3: 只用 package（启动默认 Activity）
adb shell monkey -p com.package.name 1
```

#### 建议参数
```python
{
    "type": "launch_app",
    "name": "启动训练程式",
    "params": {
        "package": "com.example.training",      # 必填
        "activity": ".MainActivity",            # 选填（没有则启动默认）
        "intent_action": None,                  # 选填（如 MAIN）
        "extras": {},                           # 选填（Intent extras）
        "wait": True,                           # 是否等待启动完成
        "stop_existing": False,                 # 是否先关闭已运行的实例
        "clear_data": False                     # 是否清除应用数据后启动
    }
}
```

#### ⚠️ 注意事项

1. **Activity 名称格式**:
   - 完整格式: `com.package.name.ActivityName`
   - 相对格式: `.ActivityName` (推荐，更简洁)
   - 错误格式: `ActivityName` (不完整)

2. **获取 Package 和 Activity**:
   ```bash
   # 列出所有已安装应用
   adb shell pm list packages
   
   # 查看当前运行的 Activity
   adb shell dumpsys window | grep mCurrentFocus
   
   # 查看应用详细信息
   adb shell dumpsys package com.package.name
   ```

3. **启动验证**:
   ```bash
   # 验证应用是否启动
   adb shell pidof com.package.name
   # 或
   adb shell ps | grep com.package.name
   ```

4. **常见错误**:
   - Activity 不存在: `Error: Activity class {xxx} does not exist`
   - 权限不足: `SecurityException`
   - 应用未安装: `Error type 3`

5. **特殊场景**:
   - 某些 VR 应用可能需要特定的 Intent flags
   - 系统应用可能需要额外权限

---

### 4. 关闭程式（Stop App）

#### ADB 命令
```bash
# 方法 1: Force stop（推荐，完全关闭）
adb shell am force-stop com.package.name

# 方法 2: Kill process（仅杀进程）
adb shell am kill com.package.name

# 方法 3: Kill all（杀所有后台进程）
adb shell am kill-all
```

#### 建议参数
```python
{
    "type": "stop_app",
    "name": "关闭训练程式",
    "params": {
        "package": "com.example.training",     # 必填
        "method": "force-stop",                # 关闭方式: force-stop / kill
        "verify": True,                        # 是否验证关闭成功
        "clear_data": False                    # 是否同时清除应用数据
    }
}
```

#### ⚠️ 注意事项

1. **force-stop vs kill**:
   - `force-stop`: 完全停止应用，清除所有状态
   - `kill`: 仅杀进程，不清除状态
   - 推荐使用 `force-stop`

2. **验证关闭**:
   ```bash
   # 检查应用是否还在运行
   adb shell pidof com.package.name
   # 返回空表示已关闭
   ```

3. **清除数据**（可选）:
   ```bash
   adb shell pm clear com.package.name
   ```

4. **系统应用**:
   - 某些系统应用无法关闭
   - 可能需要 root 权限

---

## 🎨 建议新增的动作类型

### 5. 重启应用（Restart App）⭐ 推荐

**用途**: 快速重启应用（常用于调试或重置状态）

```python
{
    "type": "restart_app",
    "name": "重启训练程式",
    "params": {
        "package": "com.example.training",
        "activity": ".MainActivity",
        "clear_data": False,     # 是否清除数据
        "delay": 1               # 关闭后等待秒数再启动
    }
}
```

**实现**: 先 force-stop，等待延迟，再启动

---

### 6. 重启设备（Reboot）

**用途**: 完全重启 Quest 设备

```python
{
    "type": "reboot",
    "name": "重启设备",
    "params": {
        "wait_for_boot": True,   # 是否等待启动完成
        "reconnect": True        # 是否自动重新连接
    }
}
```

```bash
adb shell reboot
```

**注意**: 重启后需要重新建立 ADB 连接

---

### 7. 发送按键（Send Key）⭐ 推荐

**用途**: 发送特定按键事件（如返回、主页、音量等）

```python
{
    "type": "send_key",
    "name": "返回主页",
    "params": {
        "keycode": "KEYCODE_HOME",  # 或直接用数字
        "repeat": 1                 # 重复次数
    }
}
```

**常用按键**:
```bash
adb shell input keyevent KEYCODE_HOME      # 主页 (3)
adb shell input keyevent KEYCODE_BACK      # 返回 (4)
adb shell input keyevent KEYCODE_MENU      # 菜单 (82)
adb shell input keyevent KEYCODE_VOLUME_UP   # 音量+ (24)
adb shell input keyevent KEYCODE_VOLUME_DOWN # 音量- (25)
```

---

### 8. 安装/卸载应用（Install/Uninstall）

**用途**: 批量部署或清理应用

```python
{
    "type": "install_app",
    "name": "安装训练程式",
    "params": {
        "apk_path": "/path/to/app.apk",  # APK 文件路径
        "replace": True,                  # 是否替换已存在的
        "grant_permissions": True         # 是否自动授权
    }
}
```

```bash
adb install -r -g app.apk
```

---

### 9. 执行自定义命令（Custom Command）⭐ 推荐

**用途**: 灵活执行任意 ADB 命令

```python
{
    "type": "custom_command",
    "name": "自定义操作",
    "params": {
        "command": "shell settings put system screen_brightness 100",
        "timeout": 10,
        "verify_pattern": None  # 可选的输出验证正则
    }
}
```

**用例**:
- 调整屏幕亮度
- 修改系统设置
- 执行脚本
- 查询设备信息

---

## 📊 推荐的动作类型优先级

### MVP v0.2.0（必须）
1. ✅ **唤醒** - 基础功能
2. ✅ **休眠** - 基础功能
3. ✅ **执行程式** - 核心功能
4. ✅ **关闭程式** - 核心功能

### v0.2.1（建议添加）
5. ⭐ **重启应用** - 高频使用
6. ⭐ **发送按键** - 灵活性高
7. ⭐ **自定义命令** - 扩展性强

### v0.3.0（可选）
8. 重启设备
9. 安装/卸载应用
10. 批量操作（等房间管理完成）

---

## 🗃️ 数据模型设计

### Action 模型

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum

class ActionType(str, Enum):
    """动作类型枚举"""
    WAKE_UP = "wake_up"
    SLEEP = "sleep"
    LAUNCH_APP = "launch_app"
    STOP_APP = "stop_app"
    RESTART_APP = "restart_app"
    REBOOT = "reboot"
    SEND_KEY = "send_key"
    CUSTOM_COMMAND = "custom_command"

class Action(BaseModel):
    """动作模型"""
    action_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    action_type: ActionType
    params: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 统计信息
    execution_count: int = Field(default=0)
    success_count: int = Field(default=0)
    last_executed_at: Optional[datetime] = None
    
    def to_dict(self):
        """转换为字典"""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建"""
        return cls(**data)
```

### 参数验证

```python
class ActionParamsValidator:
    """动作参数验证器"""
    
    @staticmethod
    def validate_launch_app(params: Dict[str, Any]) -> bool:
        """验证启动应用参数"""
        if not params.get('package'):
            raise ValueError("package 参数为必填")
        
        # 验证 package 格式
        package = params['package']
        if not re.match(r'^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$', package):
            raise ValueError("package 格式不正确")
        
        return True
    
    @staticmethod
    def validate_stop_app(params: Dict[str, Any]) -> bool:
        """验证关闭应用参数"""
        if not params.get('package'):
            raise ValueError("package 参数为必填")
        return True
```

---

## 🎨 UI 设计建议

### 动作列表页面

```
┌─────────────────────────────────────────────────────────┐
│  ⚡ 动作管理                           [➕ 新增动作]      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  🔍 搜索动作...                    [🏷️ 类型筛选 ▼]      │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 💚 启动训练程式                            ⋮    │   │
│  │ 类型: 执行程式                                   │   │
│  │ Package: com.training.app                       │   │
│  │ 执行次数: 15 次 | 成功率: 100%                   │   │
│  │ [▶️ 执行] [✏️ 编辑] [📋 复制] [🗑️ 删除]         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 😴 睡眠模式                                ⋮    │   │
│  │ 类型: 休眠                                       │   │
│  │ 执行次数: 8 次 | 成功率: 100%                    │   │
│  │ [▶️ 执行] [✏️ 编辑] [📋 复制] [🗑️ 删除]         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 新增/编辑动作对话框

```
┌─────────────────────────────────────┐
│  ➕ 新增动作                         │
├─────────────────────────────────────┤
│                                      │
│  动作名称 *                          │
│  ┌──────────────────────────────┐  │
│  │ 启动训练程式                  │  │
│  └──────────────────────────────┘  │
│                                      │
│  动作类型 *                          │
│  ┌──────────────────────────────┐  │
│  │ 执行程式               ▼     │  │
│  └──────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐│
│  │ 📦 应用信息                    ││
│  │                                ││
│  │ Package 名称 *                 ││
│  │ ┌──────────────────────────┐  ││
│  │ │ com.training.app          │  ││
│  │ └──────────────────────────┘  ││
│  │                                ││
│  │ Activity 名称 (选填)           ││
│  │ ┌──────────────────────────┐  ││
│  │ │ .MainActivity             │  ││
│  │ └──────────────────────────┘  ││
│  │                                ││
│  │ □ 启动前先关闭已运行的实例      ││
│  │ □ 等待启动完成                 ││
│  └────────────────────────────────┘│
│                                      │
│  说明 (选填)                         │
│  ┌──────────────────────────────┐  │
│  │ 用于开始训练课程              │  │
│  └──────────────────────────────┘  │
│                                      │
│  [💾 保存] [❌ 取消]                │
└─────────────────────────────────────┘
```

---

## ⚠️ 关键注意事项总结

### 1. 参数验证
- ✅ 必须验证必填参数
- ✅ 验证参数格式（如 package 名称格式）
- ✅ 提供友好的错误提示

### 2. 执行验证
- ✅ 执行前检查设备状态
- ✅ 执行后验证结果
- ✅ 记录执行日志

### 3. 错误处理
- ✅ 捕获 ADB 命令错误
- ✅ 超时处理
- ✅ 设备离线处理

### 4. 用户体验
- ✅ 提供动作模板（常用动作）
- ✅ 支持动作复制（快速创建类似动作）
- ✅ 显示执行历史和统计

### 5. 性能考量
- ✅ 异步执行（不阻塞 UI）
- ✅ 批量执行优化
- ✅ 超时设置

---

## 📝 实现建议

### 阶段 1: MVP v0.2.0（基础功能）
1. ✅ 实现 Action 数据模型
2. ✅ 实现 4 种基础动作类型
3. ✅ 创建动作管理页面（列表、新增、编辑、删除）
4. ✅ 实现单个动作执行
5. ✅ 基础的参数验证和错误处理

### 阶段 2: v0.2.1（增强功能）
1. ⭐ 添加重启应用、发送按键动作
2. ⭐ 添加动作执行历史
3. ⭐ 添加动作模板
4. ⭐ 优化 UI/UX

### 阶段 3: v0.3.0（高级功能）
1. 🏠 与房间管理整合（批量执行）
2. 📅 与 CUE 系统整合（定时执行）
3. 📊 执行统计和分析
4. 🔄 动作链（sequential actions）

---

## ✅ 您的规划是否合理？

### 💯 结论：非常合理！

您的规划：
- ✅ **功能定位准确** - 四种基础动作覆盖主要需求
- ✅ **参数设计合理** - 每种动作有各自的参数
- ✅ **可扩展性好** - 易于添加新动作类型
- ✅ **实现难度适中** - 适合作为 v0.2.0 的目标

### 📋 建议优先级

**必须实现（v0.2.0）**:
1. ✅ 唤醒
2. ✅ 休眠
3. ✅ 执行程式
4. ✅ 关闭程式

**强烈建议添加（v0.2.1）**:
5. ⭐ 重启应用（启动+关闭的组合，高频使用）
6. ⭐ 发送按键（灵活性高，如返回、主页等）

**可选（v0.3.0）**:
7. 自定义命令（高级用户需求）
8. 重启设备
9. 安装/卸载应用

---

**准备好开始实现了吗？** 🚀

建议按以下顺序开发：
1. 创建 Action 数据模型
2. 实现 ActionRegistry（动作注册管理）
3. 在 ADBManager 中添加执行动作的方法
4. 创建动作管理 UI 页面
5. 测试各种动作

需要我开始实现吗？




