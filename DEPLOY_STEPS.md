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

### 部署后验证（云函数日志应看到 [BOOT] 输出）

云函数「日志」页应出现：
```
[BOOT][HH:MM:SS] === 开始启动 coco-api (scf_bootstrap) ===
[BOOT][HH:MM:SS] 工作目录: /var/task
[BOOT][HH:MM:SS] 使用 Python: /usr/bin/python3
[BOOT][HH:MM:SS] pip 版本: pip 23.x
[BOOT][HH:MM:SS] env DASHSCOPE_API_KEY = [已设置]
[BOOT][HH:MM:SS] env USE_CLOUD_DB = [已设置]
[BOOT][HH:MM:SS] 检测到 requirements.txt，开始安装依赖...
[PIP] Successfully installed ...
[BOOT][HH:MM:SS] 模块导入全部成功 ✅
[BOOT][HH:MM:SS] 启动 uvicorn → 0.0.0.0:9000
INFO: Uvicorn running on http://0.0.0.0:9000
```

### 验证命令（拿到公网 URL 后，本机终端执行）

```bash
# 1. 健康检查（Swagger 文档页）
curl -o /dev/null -w "%{http_code}\n" https://<你的函数地址>/docs
#   期望: 200

# 2. 登录 API（测试数据库连通 + admin 账号）
curl -s -X POST https://<你的函数地址>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@app.com","password":"123456"}'
#   期望: {"access_token":"eyJ..."}

# 3. 知识库问答（测试 FAISS 检索 + DeepSeek）
curl -s -X POST https://<你的函数地址>/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <上一步token>" \
  -d '{"message":"会员多少钱","history":[],"session_id":"verify","user_id":1}'
#   期望: code=0 且回答含定价信息
```

### 日志为空时的排查

| 现象 | 可能原因 | 处理 |
| :--- | :--- | :--- |
| 无任何 [BOOT] 日志 | bootstrap 未执行（执行方法填错 / zip 无 scf_bootstrap / 无执行位）| 确认执行方法=`scf_bootstrap`；zip 含 scf_bootstrap；脚本开头有 chmod 自修复 |
| 有 [BOOT] 但卡在 pip install | 容器无外网或下载慢 | 等待（180s 超时后继续）；或将依赖预装进镜像 |
| 有 [PIP] 报错 | 依赖安装失败 | 看具体包名（如 faiss-cpu 需网络）；确认 requirements.txt |
| 卡在 [IMPORT] FATAL | 代码导入失败 | 看 [IMPORT] 错误详情（多为依赖版本冲突）|
| uvicorn 起来了但访问 450/443 | 网关到 9000 端口未就绪 | 确认 uvicorn 监听 0.0.0.0:9000；VPC/安全组放行 |

## 常见问题

| 问题 | 排查 |
| :--- | :--- |
| 启动报错 `aiomysql not found` | 云函数安装依赖时网络问题，重试部署或确认 requirements.txt 含 aiomysql |
| 数据库连接失败 | 确认 VPC 选择正确（与 MySQL 同 VPC）、密码正确、连接串格式无误 |
| 索引重建慢 | FAISS 重建需读取知识库 8 个 md 文件；首次冷启动约 10-30 秒 |
| 时区差异 | 云数据库 MySQL 时间为本地时区，不影响功能 |
| 访问返回 450 | 函数启动未就绪（bootstrap 未拉起 9000），看日志定位卡在哪一步 |
| 访问返回 443 | 网络/网关层错误，检查 VPC、访问路径、函数是否部署完成 |
