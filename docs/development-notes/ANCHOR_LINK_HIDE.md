# 隐藏标题锚点链接图标

## 🎯 问题描述

在设备卡片中，设备名称使用了 Markdown 标题格式（`### 设备名称`），Streamlit 会自动为标题生成锚点链接，显示为一个链接图标：

```html
<a href="#q01" class="st-emotion-cache-yinll1 et2rgd21">
  <svg>...</svg>
</a>
```

这个锚点链接图标：
- 当前没有实际用途
- 影响界面美观
- 占用空间

## ✅ 解决方案

在页面配置后添加全局 CSS，隐藏所有标题旁的锚点链接图标。

## 🔧 实现代码

在 `pages/1_📱_設備管理.py` 中添加：

```python
# 隱藏標題旁的錨點鏈接圖標
st.markdown("""
    <style>
    /* 隱藏標題旁的錨點鏈接圖標 */
    a.st-emotion-cache-yinll1,
    a[class*="st-emotion-cache"][href^="#"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)
```

## 📊 CSS 说明

### 选择器 1：`a.st-emotion-cache-yinll1`
- 针对特定类名的锚点链接
- `st-emotion-cache-yinll1` 是 Streamlit 为锚点链接生成的类名

### 选择器 2：`a[class*="st-emotion-cache"][href^="#"]`
- 更广泛的选择器，匹配所有符合条件的锚点
- `[class*="st-emotion-cache"]`：类名包含 `st-emotion-cache`
- `[href^="#"]`：href 属性以 `#` 开头（锚点链接）

### 样式：`display: none !important;`
- 完全隐藏元素
- `!important` 确保样式优先级最高

## 🎨 效果

**修改前**：
```
[🟢 Q01 🔗]  ⋮
```
（设备名称旁有链接图标）

**修改后**：
```
[🟢 Q01]  ⋮
```
（链接图标已隐藏）

## 🔄 如需恢复

如果未来需要使用这些锚点链接（例如，用于页面内导航或分享特定设备），只需：

### 方法 1：移除 CSS
删除或注释掉上述 CSS 代码。

### 方法 2：条件显示
根据设置决定是否显示：

```python
from config.settings import get_user_config

config = get_user_config()
if not config.get('ui', {}).get('show_anchor_links', False):
    st.markdown("""
        <style>
        a[class*="st-emotion-cache"][href^="#"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
```

## 💡 其他可能的用途

锚点链接未来可用于：

1. **页面内导航**
   - 从设备列表快速跳转到特定设备
   - 例如：点击侧边栏链接跳转到对应设备卡片

2. **分享链接**
   - 分享特定设备的 URL
   - 例如：`http://localhost:8501/設備管理#q01`

3. **批量操作**
   - 多选设备时显示锚点
   - 用于标识选中的设备

4. **房间视图**
   - 在房间管理中，链接到特定设备
   - 点击设备名称跳转到设备详情

## 📝 注意事项

1. **CSS 类名可能变化**
   - Streamlit 更新后，`st-emotion-cache-yinll1` 可能改变
   - 使用通配符选择器 `[class*="st-emotion-cache"]` 提高兼容性

2. **影响范围**
   - 这个 CSS 会隐藏**整个页面**的所有标题锚点链接
   - 包括页面标题、设备卡片标题等

3. **性能影响**
   - CSS 规则非常轻量，对性能无影响

## 🧪 测试

### 步骤 1：启动应用
```bash
cd /Users/jinyaolin/QQquest
./run.sh
```

### 步骤 2：检查设备卡片
1. 前往「📱 設備管理」页面
2. 查看任一设备卡片
3. **验证**：设备名称旁边没有链接图标（🔗）

### 步骤 3：检查其他标题
1. 检查页面标题
2. 检查其他使用 Markdown 标题的地方
3. **验证**：所有锚点链接图标都已隐藏

## ✅ 总结

通过添加简单的 CSS 规则，我们成功隐藏了 Streamlit 自动生成的标题锚点链接图标，使界面更加简洁美观。

**修改位置**：`pages/1_📱_設備管理.py`
**影响范围**：整个设备管理页面的所有标题锚点链接
**可逆性**：随时可以恢复

---

**日期**：2025-12-01
**状态**：✅ 已实现

