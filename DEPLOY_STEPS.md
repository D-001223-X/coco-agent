# CloudBase 云函数部署步骤

> 前置：已开通 CloudBase 免费体验版，已创建云数据库（MySQL），已获取连接串。
> 打包文件：`backend.zip`（已生成，见项目根目录）

## 步骤 1：创建云函数

1. 登录 CloudBase 控制台
2. 左侧菜单 → 云函数/托管 → 云函数
3. 点击「新建云函数」
4. 函数名称：`coco-api`
5. 函数类型：**HTTP 云函数**
6. 运行时：**Python 3.11**
7. 代码来源：**本地上传 zip 包** → 选择 `backend.zip`
8. **执行方法**：填 **`scf_bootstrap`**（Custom Runtime 启动脚本）

> ⚠️ CloudBase HTTP 云函数 = Custom Runtime，必须有 `scf_bootstrap` 启动脚本。
> 之前的 `app.main:app` 入口是事件函数模式，会触发 `filename not matched: scf_bootstrap` 错误。

## 步骤 2：配置环境变量

在云函数「环境变量」中逐条添加（值来自 `cloudbase_env.txt`）：

| 变量名 | 值 |
| :--- | :--- |
| `DASHSCOPE_API_KEY` | 你的阿里云百炼 API Key |
| `WORKSPACE_ID` | 你的阿里云百炼 Workspace ID |
| `USE_CLOUD_DB` | `true` |
| `CLOUDBASE_DATABASE_URL` | `mysql+aiomysql://coco_user:你的密码@172.17.0.15:3306/coco-agent-d3gns13n9b4b12883?charset=utf8mb4` |

> ⚠️ 数据库密码请使用云数据库创建时设置的实际密码替换。

## 步骤 3：高级配置

- 内存：256MB
- 超时时间：30秒
- VPC：选择 `vpc-hqgotgem`（与 MySQL 同 VPC）

> 若云函数运行时仅支持 Python 3.11（本项目 requires-python >=3.13）：
> 可尝试直接部署（代码兼容 3.11 大概率可用），或改用「云托管/容器」方式。
> 依赖安装：CloudBase 上传 zip 后会自动执行 `pip install -r requirements.txt`；
> 本包使用 `pyproject.toml`，如需 requirements.txt 请先转换：
> `uv export --format requirements-txt -o requirements.txt` 或手动列出依赖。

## 步骤 4：部署

点击「完成」或「部署」，等待 1-2 分钟。

## 步骤 5：获取公网地址

1. 进入云函数详情页
2. 找到「触发管理」或「访问服务」
3. 复制 HTTP 访问地址（类似 `https://xxx.service.tcloudbase.com/coco-api`）

## 步骤 6：更新前端环境变量

1. 进入 EdgeOne Pages 项目控制台
2. 找到「环境变量」
3. 更新 `VITE_API_BASE_URL` = 上一步复制的地址
4. 保存，等待自动重新部署

## 步骤 7：验证

- [ ] 访问 `<云函数地址>/api/auth/login`（POST，`{"email":"admin@app.com","password":"123456"}`）返回 token
- [ ] 知识库问答正常（FAISS 检索生效，云函数冷启动会自动重建索引）
- [ ] 口语陪练对话正常（DeepSeek API）
- [ ] 管理后台登录 + 知识库/Prompt/Agent 追踪可用

## 常见问题

| 问题 | 排查 |
| :--- | :--- |
| 启动报错 `aiomysql not found` | 云函数安装依赖时网络问题，重试部署或确认 requirements.txt 含 aiomysql |
| 数据库连接失败 | 确认 VPC 选择正确（与 MySQL 同 VPC）、密码正确、连接串格式无误 |
| 索引重建慢 | FAISS 重建需读取知识库 8 个 md 文件；首次冷启动约 10-30 秒 |
| 时区差异 | 云数据库 MySQL 时间为本地时区，不影响功能 |
