# SWJTU 自动课程评价工具

西南交通大学教务系统自动化课程评价脚本，可以自动完成所有待评价课程的问卷填写。

这个评课系统相当折磨人，所以我干脆ai写了一个脚本。还好我交的教务处比较简陋，ai可以写出能用的代码。

这个readme也是ai写的（

**评价结果全为最高分，主管题答案统一为 “老师讲得很好，没有意见。“**

## 配置账号信息
编辑 `config.py` 文件，填写你的学号：

```python
# 你的学号
USERNAME = "你的学号"

# 你的密码（可选）
# 留空则运行时手动输入，更安全
# 或直接填写密码（如 "YourPassword123"）以免每次输入
PASSWORD = ""
```

**安全建议：** 
- 建议将 `PASSWORD` 留空，脚本运行时会提示你输入密码。**注意：输入密码时不会显示任何字符（包括星号或点），这是正常的安全机制，直接输入后按回车即可。**
- 如果将密码写入配置文件，请确保不要将 `config.py` 上传到公开仓库

## 安装配置

### 方式一：使用 uv（推荐）

[uv](https://github.com/astral-sh/uv) 是一个快速的 Python 包管理工具，推荐使用。

1. **安装 uv**

```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 Homebrew (macOS)
brew install uv
```

2. **安装项目依赖**

```bash
cd swjtu-auto-course-evaluation
uv sync
```

3. **运行脚本**

```bash
uv run ./auto_access.py
```

### 方式二：使用 pip

如果你更习惯使用传统的 pip 方式，可以按以下步骤操作。

1. **创建虚拟环境（推荐，可以省略）**

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

2. **安装依赖**

```bash
pip install requests beautifulsoup4 pillow
```

3. **运行脚本**

```bash
python auto_access.py
```

## 使用说明

### 1. 功能特性
- 自动登录教务系统（带验证码识别提示）
- **评价结果全为最高分，主管题答案统一为 “老师讲得很好，没有意见。“**
- 自动获取所有待评价课程列表
- 批量自动填写评价问卷
- 支持密码配置或运行时输入，保障账号安全

### 1. 运行脚本

使用上述任一方式运行脚本后：

1. 程序会自动获取验证码并打开图片显示
2. 在终端中输入验证码
3. 登录成功后，自动获取待评价课程列表
4. 自动填写所有课程的评价问卷
5. 完成后显示评价结果统计

### 2. 运行示例

```bash
$ uv run ./auto_access.py
正在获取验证碼...
请在新打开的窗口中查看验证码，并在此输入：1234
正在尝试登录API...
API验证成功！
正在访问加载页面以建立完整会话...
会话建立步骤完成。

正在获取待评价课程列表...
找到 5 门待评价课程。

开始自动评价...
[1/5] 正在评价课程...
评价成功！

...

评价完成！
总共评价了 5 门课程
成功: 5 门
失败: 0 门
```

## 项目结构

```
swjtu-auto-course-evaluation/
├── auto_access.py      # 主程序文件
├── config.py          # 配置文件（账号密码）
├── pyproject.toml     # 项目依赖配置
└── README.md          # 项目说明文档
```

## 依赖说明

- `requests` - HTTP 请求库，用于与教务系统交互
- `beautifulsoup4` - HTML 解析库，用于解析课程列表页面
- `pillow` - 图像处理库，用于显示验证码图片

## 注意事项

1. 本工具仅供学习交流使用，请合理使用
2. 评价结果全为最高分，主管题答案统一为 “老师讲得很好，没有意见。“
3. 请妥善保管你的账号密码，不要将 `config.py` 上传到公开仓库
4. 如遇登录失败，请检查账号密码是否正确，或验证码是否输入准确
5. 建议在评价期限内合理安排时间使用本工具

**免责声明：** 本工具仅用于学习和研究目的，使用本工具产生的任何后果由使用者自行承担。