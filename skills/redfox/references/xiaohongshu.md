# 小红书 API 参考 (RedFoxHub)

仅有 **优质库**，无广域库。搜索信息不足时无法降级。

## 搜索作品

`POST /story/api/xhsUser/searchArticle`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | String | 是 | 搜索关键词 |
| offset | Integer | 否 | 分页偏移（默认 0，每页约 20 条） |
| sortType | String | 否 | 排序：`default`(默认)、`newest`(最新) |

### 响应字段 (data.list[])

| 字段 | 类型 | 说明 |
|---|---|---|
| workId | String | 作品 ID |
| workTitle | String | 作品标题 |
| workDesc | String | 作品描述 |
| coverUrl | String | 封面图 URL |
| workUrl | String | 作品链接 |
| workPublishTime | String | 发布时间 |
| accountNickname | String | 作者昵称 |
| accountUserid | String | 作者小红书 ID |
| workLikedCount | Integer | 点赞数 |
| workCommentsCount | Integer | 评论数 |
| workCollectedCount | Integer | 收藏数 |
| workReadedCount | Integer | 阅读数 |
| workSharedCount | Integer | 转发数 |
| workType | String | 类型：`normal`(图文) / `video`(视频) |

## 搜索账号

`POST /story/api/xhsUser/searchUser`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | String | 是 | 搜索关键词 |
| offset | Integer | 否 | 分页偏移 |
| sortType | String | 否 | 排序方式 |

### 响应字段 (data.list[])

| 字段 | 类型 | 说明 |
|---|---|---|
| accountName | String | 账号名称 |
| accountAvatar | String | 头像 URL |
| accountId | String | 平台展示 ID |
| accountDesc | String | 账号简介 |
| accountFans | Integer | 粉丝数 |
| accountTotalWorks | Integer | 总作品数 |
| accountLikes | Integer | 总获赞数 |
| accountCollectes | Integer | 总收藏数 |
| province / city | String | 所在地 |
