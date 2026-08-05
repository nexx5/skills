"""
RedFox API 统一搜索脚本。

用法:
  python redfox_search.py <平台> <关键词> [--lib 优质库|广域库] [--offset N] [--sort 类型] [--config 路径]

平台: xiaohongshu, gongzhonghao
库级别（仅公众号有效）: 优质库（默认）, 广域库

两级搜索策略（由 AI 决定是否降级）:
  1. 先调 --lib 优质库
  2. 若结果不足，再调 --lib 广域库
"""

import json
import os
import sys
import urllib.request
import urllib.error

CONFIG_DEFAULTS = {
    "api_key": "",
    "base_url": "https://redfox.hk"
}

PLATFORMS = {
    "xiaohongshu": {
        "premium": {
            "search_article": "/story/api/xhsUser/searchArticle",
            "search_user": "/story/api/xhsUser/searchUser"
        }
    },
    "gongzhonghao": {
        "premium": {
            "search_article": "/story/api/gzhData/searchArticle",
            "search_user": "/story/api/gzhData/searchUser"
        },
        "broad": {
            "search_article": "/story/api/gzh/data/searchArticle",
            "search_user": "/story/api/gzh/data/searchUser"
        }
    }
}

SORT_TYPES = {
    "default": "_0",
    "newest": "_2",
    "hot": "_4"
}


def load_config(config_path=None):
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return {**CONFIG_DEFAULTS, **json.load(f)}
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(skill_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return {**CONFIG_DEFAULTS, **json.load(f)}
    env_key = os.environ.get("REDFOX_API_KEY", "")
    return {**CONFIG_DEFAULTS, "api_key": env_key}


def search(config, platform, lib, keyword, offset=0, sort_type="default"):
    if platform not in PLATFORMS:
        return {"error": f"不支持的平台: {platform}，可选: {list(PLATFORMS.keys())}"}
    if lib not in PLATFORMS[platform]:
        return {"error": f"平台 '{platform}' 不支持库级别 '{lib}'，可选: {list(PLATFORMS[platform].keys())}"}

    api_key = config.get("api_key", "").strip()
    if not api_key:
        return {"error": "未配置 REDFOX_API_KEY，请在 config.json 中设置或通过环境变量 REDFOX_API_KEY 传入"}

    base_url = config.get("base_url", "https://redfox.hk").rstrip("/")
    path = PLATFORMS[platform][lib]["search_article"]
    url = f"{base_url}{path}"

    sort_val = SORT_TYPES.get(sort_type, sort_type)
    body = {"keyword": keyword, "offset": offset, "sortType": sort_val}

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "REDFOX_API_KEY": api_key,
            "X-API-Key": api_key
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 2000:
                return {"success": True, "data": result.get("data", {}), "platform": platform, "lib": lib}
            else:
                return {"success": False, "error": f"API 返回错误: code={result.get('code')}, msg={result.get('msg')}"}
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"请求失败: {e.reason}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "响应不是有效 JSON"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RedFox API 搜索")
    parser.add_argument("platform", choices=["xiaohongshu", "gongzhonghao"], help="平台")
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument("--lib", choices=["premium", "broad"], default="premium", help="库级别（默认优质库）")
    parser.add_argument("--offset", type=int, default=0, help="分页偏移")
    parser.add_argument("--sort", choices=["default", "newest", "hot"], default="default", help="排序方式")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--raw", action="store_true", help="输出原始 JSON")
    args = parser.parse_args()

    config = load_config(args.config)
    lib_label = "优质库" if args.lib == "premium" else "广域库"

    result = search(config, args.platform, args.lib, args.keyword, args.offset, args.sort)

    if args.raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)

    data = result.get("data", {})
    items = data.get("list", [])
    total = data.get("total", 0)
    has_more = data.get("hasMore", False)

    print(f"平台: {args.platform} | 库: {lib_label} | 关键词: {args.keyword}")
    print(f"结果数: {total} | 是否还有更多: {'是' if has_more else '否'}")
    print()

    for i, item in enumerate(items):
        title = item.get("workTitle") or item.get("title") or "(无标题)"
        url = item.get("workUrl") or ""
        author = item.get("accountNickname") or item.get("author") or ""
        likes = item.get("workLikedCount") or item.get("likeCount") or 0
        reads = item.get("workReadedCount") or item.get("readCount") or 0
        time = item.get("workPublishTime") or item.get("publishTime") or ""
        print(f"{i+1}. {title}")
        if author:
            print(f"   作者: {author}")
        print(f"   互动: {likes}赞 / {reads}阅读")
        print(f"   时间: {time}")
        print(f"   链接: {url}")
        print()


if __name__ == "__main__":
    main()
