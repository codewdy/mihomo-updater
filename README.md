# mihomo-updater

用于自动更新 mihomo 订阅配置。

## 使用 Docker Compose 启动

1. 进入 `docker-compose` 目录：

   ```bash
   cd docker-compose
   ```

2. 复制环境变量模板并填写必填项：

   ```bash
   cp .env.example .env
   ```

   至少需要在 `.env` 中填写：
   - `SUB_URL`：订阅地址（必填）
   - `SECRET`：可选，REST API 密钥

3. （推荐）设置当前用户 UID/GID，避免 `data` 目录权限问题：

   ```bash
   export HOST_UID=$(id -u) HOST_GID=$(id -g)
   ```

4. 启动服务：

   ```bash
   docker compose up -d
   ```

5. 查看日志：

   ```bash
   docker compose logs -f
   ```

6. 停止服务：

   ```bash
   docker compose down
   ```

默认端口映射（可在 `.env` 中修改）：
- `HOST_PORT` -> `7890`
- `HOST_API_PORT` -> `9090`
