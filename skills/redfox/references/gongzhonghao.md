# 公众号 API 参考 (RedFoxHub)

两级库：

| 库级别 | 前缀路径 | 特点 |
|---|---|---|
| **优质库** (premium) | `/story/api/gzhData/` | 搜索结果含基本信息，不含正文 |
| **广域库** (broad) | `/story/api/gzh/data/` | 搜索结果含 `content` 字段（HTML 正文全文），覆盖面更广 |

## 搜索作品

### 优质库

`POST /story/api/gzhData/searchArticle`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | String | 是 | 搜索关键词 |
| offset | Integer | 否 | 分页偏移（0 开始，每页 +20） |
| sortType | String | 否 | `_0`(默认综合) / `_2`(最新) / `_4`(最热按阅读量) |

### 广域库

`POST /story/api/gzh/data/searchArticle`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | String | 是 | 搜索关键词 |
| offset | Integer | 否 | 分页偏移 |
| sortType | String | 否 | `0`(默认综合) / `2`(最新) / `4`(最热) |

### 响应字段 (data.list[])

| 字段 | 类型 | 优质库 | 广域库 | 说明 |
|---|---|---|---|---|
| workUuid | String | ✓ | ✓ | 作品 UUID |
| title | String | ✓ | ✓ | 文章标题 |
| summary | String | ✓ | ✓ | 摘要 |
| content | String | ✗ | ✓ | HTML 正文全文 |
| workUrl | String | ✓ | ✓ | 文章链接 |
| coverUrl | String | ✓ | ✓ | 封面图 |
| publishTime | String | ✓ | ✓ | 发布时间 |
| author | String | ✓ | ✓ | 作者昵称 |
| readCount | Integer | ✓ | ✓ | 阅读量 |
| watchCount | Integer | ✓ | ✓ | 在看数 |
| likeCount | Integer | ✓ | ✓ | 点赞数 |
| commentCount | Integer | ✓ | ✓ | 评论数 |
| collectCount | Integer | ✓ | ✓ | 收藏数 |
| shareCount | Integer | ✓ | ✓ | 转发数 |
| isOriginal | Integer | ✓ | ✓ | 是否原创（0=否, 1=是） |
| accountType | String | ✓ | ✓ | 账号分类 |
| bizInfo | String | ✗ | ✓ | 公众号采集 ID |
| originalAuthor | String | ✓ | ✓ | 原始作者 |
| orderNum | Integer | ✓ | ✓ | 文章发布位置（0=头条） |

## 搜索账号

### 优质库

`POST /story/api/gzhData/searchUser`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | String | 是 | 搜索关键词 |
| offset | Integer | 否 | 分页偏移 |
| sortType | String | 否 | `_0`(默认) / `_2`(最新) / `_4`(最热) |

### 广域库

`POST /story/api/gzh/data/searchUser`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | String | 是 | 搜索关键词 |
| offset | Integer | 否 | 分页偏移 |

### 响应字段 (data.list[])

| 字段 | 类型 | 优质库 | 广域库 | 说明 |
|---|---|---|---|---|
| accountName | String | ✓ | ✓ | 公众号名称 |
| account | String | ✓ | ✓ | 微信号 |
| wxId | String | ✗ | ✓ | 原始 ID |
| avatarUrl | String | ✓ | ✓ | 头像 URL |
| description | String | ✓ | ✓ | 账号简介 |
| verifyInfo | String | ✓ | ✓ | 认证信息 |
| qrcodeUrl | String | ✓ | ✓ | 二维码 |
| tags | String | ✓ | ✗ | 账号标签 |
| accountType | String | ✓ | ✗ | 账号分类 |
| redfoxIndex | Double | ✓ | ✗ | 红狐指数 |
| bizInfo | String | ✗ | ✓ | 采集 ID |
