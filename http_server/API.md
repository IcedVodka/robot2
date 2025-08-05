# 药品抓取系统 API 文档

## 基本信息

- 基础URL: `http://localhost:5000`
- 所有请求和响应均使用 JSON 格式
- 所有响应都包含 `status` 字段，表示请求的处理状态

## API 端点

### 1. 处理任务

#### 发起处方识别

```http
POST /process/1
```

发起一个处方识别任务。

**响应示例：**
```json
{
    "status": "accepted",
    "message": "任务已接受",
    "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 发起药品抓取

```http
POST /process/2
```

发起一个药品抓取任务。

**请求体：**
```json
{
    "medicines": [
        {
            "name": "阿司匹林",
            "status": "pending"
        }
    ]
}
```

**响应示例：**
```json
{
    "status": "accepted",
    "message": "任务已接受",
    "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 2. 获取待抓取药品列表

```http
GET /pending_medicines
```

获取当前系统中待抓取的药品列表。

**响应示例：**
```json
{
    "status": "success",
    "medicines": [
        {
            "name": "阿司匹林",
            "status": "pending"
        },
        {
            "name": "布洛芬",
            "status": "pending"
        }
    ]
}
```

### 3. 查询任务状态

```http
GET /task/{task_id}
```

查询指定任务的执行状态。

**响应示例（处理中）：**
```json
{
    "status": "processing",
    "action": "1"
}
```

**响应示例（完成）：**
```json
{
    "status": "completed",
    "action": "1",
    "result": [
        {
            "name": "阿司匹林",
            "status": "pending"
        }
    ]
}
```

**响应示例（失败）：**
```json
{
    "status": "failed",
    "action": "1",
    "error": "处理失败的具体原因"
}
```

### 4. 删除任务

```http
DELETE /task/{task_id}
```

删除指定的任务记录（仅可删除已完成或失败的任务）。

**响应示例：**
```json
{
    "status": "success",
    "message": "任务已删除"
}
```

## 任务状态说明

任务在处理过程中可能具有以下状态：

- `pending`: 等待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败

## 错误处理

所有错误响应都会包含错误信息：

```json
{
    "status": "error",
    "message": "错误描述信息"
}
```

常见错误状态码：
- 400: 请求参数错误
- 404: 资源不存在
- 500: 服务器内部错误

## 使用示例

请参考 `test_client.py` 文件中的示例代码，该文件展示了如何使用Python代码调用这些API端点。 