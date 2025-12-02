# 静态预览截图实现方案

## 📸 核心概念

**静态预览截图**：在设备卡片上显示设备屏幕的静态截图，每隔几秒自动更新。

---

## ❓ **是否需要 scrcpy library？**

### ✅ **答案：不需要！**

**原因**：
- scrcpy 本身**不是一个 Python library**
- scrcpy 是一个独立的**应用程序**（用 C 语言编写）
- 静态截图只需要 **ADB 命令**即可实现

---

## 🔧 **实现方案**

### **方案 1：使用 ADB 的 screencap 命令**（推荐 ✅）

#### **实现代码**

```python
def get_device_screenshot(device_id: str) -> Optional[Image.Image]:
    """
    通过 ADB 获取设备截图
    
    Args:
        device_id: 设备的连接字串 (serial 或 IP:Port)
    
    Returns:
        PIL Image 对象，失败返回 None
    """
    try:
        # 方法 1: screencap 输出到文件，然后 pull（较慢）
        # adb -s {device_id} shell screencap -p /sdcard/screenshot.png
        # adb -s {device_id} pull /sdcard/screenshot.png
        
        # 方法 2: screencap 直接输出到 stdout（推荐，更快）
        cmd = ['adb', '-s', device_id, 'shell', 'screencap', '-p']
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=5
        )
        
        if result.returncode != 0:
            logger.error(f"截图失败: {device_id}")
            return None
        
        # 处理 Windows 的换行符问题
        # ADB 在某些情况下会将 \n 转换为 \r\n
        img_bytes = result.stdout.replace(b'\r\n', b'\n')
        
        # 解码图像
        from PIL import Image
        import io
        
        img = Image.open(io.BytesIO(img_bytes))
        
        logger.debug(f"截图成功: {device_id}, 尺寸: {img.size}")
        return img
        
    except subprocess.TimeoutExpired:
        logger.error(f"截图超时: {device_id}")
        return None
    except Exception as e:
        logger.error(f"截图失败: {device_id} - {e}")
        return None
```

#### **优点**
- ✅ 简单直接
- ✅ 不需要额外的 library
- ✅ 性能好
- ✅ 可靠稳定

#### **缺点**
- ⚠️ 每次都需要执行 ADB 命令（约 0.5-1 秒）
- ⚠️ 如果频繁截图会有一定开销

---

### **方案 2：使用 adbutils library**（可选）

#### **安装**
```bash
pip install adbutils pillow
```

#### **实现代码**

```python
from adbutils import adb
from PIL import Image
import io

def get_device_screenshot_v2(device_id: str) -> Optional[Image.Image]:
    """
    使用 adbutils 库获取设备截图
    
    Args:
        device_id: 设备的连接字串
    
    Returns:
        PIL Image 对象，失败返回 None
    """
    try:
        # 连接设备
        device = adb.device(serial=device_id)
        
        # 获取截图（返回 PNG 格式的 bytes）
        screenshot_bytes = device.screencap()
        
        # 转换为 PIL Image
        img = Image.open(io.BytesIO(screenshot_bytes))
        
        logger.debug(f"截图成功: {device_id}, 尺寸: {img.size}")
        return img
        
    except Exception as e:
        logger.error(f"截图失败: {device_id} - {e}")
        return None
```

#### **优点**
- ✅ 代码更简洁
- ✅ 纯 Python 实现
- ✅ 提供了更多 ADB 功能

#### **缺点**
- ⚠️ 需要额外依赖
- ⚠️ 可能与现有 ADB 命令冲突

---

### **方案对比**

| 特性 | ADB 命令 | adbutils |
|------|---------|----------|
| 依赖 | ✅ 无需额外依赖 | ⚠️ 需要 adbutils |
| 代码复杂度 | 🟡 中等 | 🟢 简单 |
| 性能 | 🟢 好 | 🟢 好 |
| 兼容性 | 🟢 最好 | 🟡 一般 |
| 推荐 | ✅ **推荐** | 🟡 可选 |

---

## 🎨 **在 Streamlit 中显示**

### **实现示例**

```python
def render_device_card_with_preview(device: Device):
    """渲染带预览截图的设备卡片"""
    
    with st.container():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 左侧：设备预览截图
            if device.is_online:
                # 从缓存获取或生成新截图
                screenshot = get_cached_screenshot(device.device_id)
                
                if screenshot:
                    # 调整大小以适应卡片
                    screenshot_resized = screenshot.resize((200, 150))
                    st.image(screenshot_resized, use_column_width=True)
                else:
                    st.info("📷 无法获取预览")
            else:
                st.warning("🔌 设备离线")
        
        with col2:
            # 右侧：设备信息
            st.markdown(f"### {device.display_name}")
            st.markdown(f"**状态**: {'🟢 在线' if device.is_online else '🔴 离线'}")
            st.markdown(f"**序号**: `{device.serial}`")
            
            # 操作按钮
            if st.button("📺 监看设备", key=f"scrcpy_{device.device_id}"):
                # 启动 scrcpy（实时监看）
                start_scrcpy(device)
            
            if st.button("🔄 更新预览", key=f"refresh_{device.device_id}"):
                # 强制更新截图
                clear_screenshot_cache(device.device_id)
                st.rerun()
```

---

## 💾 **缓存策略**

为了避免频繁执行 ADB 命令，应该使用缓存：

```python
import time
from typing import Dict, Tuple

# 缓存: device_id -> (screenshot, timestamp)
_screenshot_cache: Dict[str, Tuple[Image.Image, float]] = {}

# 缓存有效期（秒）
CACHE_DURATION = 5  # 5 秒内使用缓存

def get_cached_screenshot(device_id: str) -> Optional[Image.Image]:
    """
    获取缓存的截图，如果缓存过期则重新获取
    
    Args:
        device_id: 设备 ID
    
    Returns:
        PIL Image 对象，失败返回 None
    """
    current_time = time.time()
    
    # 检查缓存
    if device_id in _screenshot_cache:
        screenshot, timestamp = _screenshot_cache[device_id]
        
        # 如果缓存未过期，直接返回
        if current_time - timestamp < CACHE_DURATION:
            logger.debug(f"使用缓存的截图: {device_id}")
            return screenshot
    
    # 缓存过期或不存在，重新获取
    logger.debug(f"获取新截图: {device_id}")
    screenshot = get_device_screenshot(device_id)
    
    if screenshot:
        # 更新缓存
        _screenshot_cache[device_id] = (screenshot, current_time)
    
    return screenshot

def clear_screenshot_cache(device_id: str = None):
    """
    清除截图缓存
    
    Args:
        device_id: 指定设备 ID，如果为 None 则清除所有缓存
    """
    if device_id:
        _screenshot_cache.pop(device_id, None)
        logger.debug(f"清除缓存: {device_id}")
    else:
        _screenshot_cache.clear()
        logger.debug("清除所有缓存")
```

---

## 🔄 **自动更新**

使用 `st_autorefresh` 自动更新预览：

```python
from streamlit_autorefresh import st_autorefresh

# 每 5 秒自动刷新页面
count = st_autorefresh(interval=5000, key="preview_refresh")

# 页面刷新时，缓存会自动过期（如果超过 5 秒）
# 然后重新获取截图
```

---

## 📊 **性能考量**

### **单次截图开销**

```
ADB screencap 命令:
- 执行时间: 0.5 - 1.5 秒
- 数据量: 约 100KB - 500KB（PNG 格式）
- CPU 占用: 低
```

### **多设备场景**

假设有 10 台设备：

```python
# ❌ 不好的做法：顺序获取所有截图
for device in devices:
    screenshot = get_device_screenshot(device.device_id)  # 每个 1 秒
# 总时间: 10 秒！

# ✅ 好的做法：使用缓存 + 异步
import asyncio

async def get_all_screenshots():
    tasks = [
        asyncio.create_subprocess_exec(
            'adb', '-s', device.device_id, 'shell', 'screencap', '-p',
            stdout=asyncio.subprocess.PIPE
        )
        for device in devices
    ]
    results = await asyncio.gather(*tasks)
    # 总时间: 约 1-2 秒（并行执行）
```

---

## 🎯 **推荐实现**

### **分阶段实现**

#### **阶段 1：基础版本**（推荐先实现）

```python
# 在设备卡片上添加一个"预览"按钮
if st.button("📷 预览", key=f"preview_{device.device_id}"):
    screenshot = get_device_screenshot(device.device_id)
    if screenshot:
        st.image(screenshot, caption=device.display_name)
```

**优点**：
- ✅ 简单
- ✅ 按需获取（不浪费资源）
- ✅ 快速实现（15 分钟）

---

#### **阶段 2：自动预览**（可选）

```python
# 在设备卡片上始终显示预览
# 使用缓存避免频繁截图
screenshot = get_cached_screenshot(device.device_id)
if screenshot:
    st.image(screenshot, use_column_width=True)
```

**优点**：
- ✅ 用户体验好
- ✅ 自动更新

**缺点**：
- ⚠️ 有一定资源开销
- ⚠️ 需要实现缓存机制

---

#### **阶段 3：优化版本**（未来）

```python
# 使用异步获取所有截图
# 添加加载状态
# 支持点击放大
# 支持手动刷新
```

---

## 🆚 **与 scrcpy 的区别**

| 功能 | 静态预览截图 | scrcpy |
|------|------------|--------|
| 目的 | 📸 快速查看状态 | 📺 实时监看和控制 |
| 实现 | ADB screencap | scrcpy 应用程序 |
| 更新频率 | 3-5 秒 | 60 fps |
| 延迟 | 0.5-1.5 秒 | < 50ms |
| 交互 | ❌ 无法交互 | ✅ 完整控制 |
| 资源占用 | 🟢 低 | 🟡 中 |
| 使用场景 | 快速查看多台设备 | 深入操作单台设备 |

---

## ✅ **总结**

### **静态预览截图实现方式**

1. **使用 ADB 的 `screencap` 命令**（推荐 ✅）
   - 不需要 scrcpy
   - 不需要 scrcpy library（scrcpy 本身也不是 library）
   - 只需要 ADB + PIL/Pillow

2. **实现步骤**
   ```
   执行: adb -s {device} shell screencap -p
   ↓
   获取: PNG 格式的图像数据
   ↓
   解码: 使用 PIL.Image.open()
   ↓
   显示: st.image()
   ```

3. **与 scrcpy 的关系**
   - 静态预览：用 ADB 截图
   - 实时监看：用 scrcpy 应用程序
   - 两者互不影响，各有用途

---

**日期**：2025-12-01  
**结论**：静态预览不需要 scrcpy library，使用 ADB screencap 即可 ✅

