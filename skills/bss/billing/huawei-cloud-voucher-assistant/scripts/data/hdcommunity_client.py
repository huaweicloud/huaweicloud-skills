"""HDCommunitySoService 成长中心前端 API 匿名客户端（零依赖）。

通过 devdata.huaweicloud.com 的 fwdo 转发路径匿名访问成长中心公开数据
（任务列表），无需 Cookie/CSRF/appcode。

积分查询（bonus-beans）走 fwdu 路径需登录态，本客户端不提供。

接口来源：成长中心前端 JS chunk 48/477 逆向（HDGrowthPortal 1.0.29）。
"""


import json
import os
from urllib import error as urlerror
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT = 15
DEFAULT_BASE = "https://devdata.huaweicloud.com"
FWDO_PREFIX = "/rest/developer/fwdo/rest/developer/servlet/hdcommunitysoservice/v1/growth"

CYCLE_CN = {
    "LIMIT": "仅一次",
    "DAILY": "每日",
    "WEEKLY": "每周",
    "MONTHLY": "每月",
}


class HdgrowthWebError(Exception):
    """成长中心前端 API 错误。"""
    pass


class HdgrowthWebClient:
    """成长中心前端 API 匿名客户端（fwdo 路径，无需认证）。

    Args:
        base_url: API 域名，默认 https://devdata.huaweicloud.com。
        timeout: 请求超时（秒），默认 15。
    """

    def __init__(self, base_url=None, timeout=DEFAULT_TIMEOUT):
        self.base_url = (
            base_url
            or os.environ.get("HDGROW_WEB_BASE")
            or DEFAULT_BASE
        ).rstrip("/")
        self.timeout = timeout

    def _post(self, path, payload=None):
        url = self.base_url + FWDO_PREFIX + path
        data = json.dumps(payload or {}).encode("utf-8")
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urlerror.HTTPError as e:
            raise HdgrowthWebError("HTTP %s %s" % (e.code, url))
        except urlerror.URLError as e:
            raise HdgrowthWebError("网络错误 %s" % (e.reason,))

    def list_missions(self, page_no=1, page_size=20):
        """返回成长中心任务列表（公开字段）。

        对应 POST .../growth/mission/query-mission-list-by-condition。

        返回每项: {"task_id", "task_name", "points", "cycle", "category",
                  "description", "guide", "url", "is_finish"}。
        fwdo 匿名访问不含个人完成状态，is_finish 恒为 False。
        """
        data = self._post(
            "/mission/query-mission-list-by-condition",
            {"page_no": page_no, "page_size": page_size},
        )
        tasks = []
        for r in data.get("QueryMissionDtoList") or []:
            rule = (r.get("rule_list") or [{}])[0]
            cycle_type = rule.get("mission_cycle_type") or ""
            tasks.append({
                "task_id": r.get("id"),
                "task_name": r.get("title"),
                "points": int(r.get("bonus", 0) or 0),
                "cycle": CYCLE_CN.get(cycle_type, cycle_type),
                "category": r.get("categoryName", ""),
                "description": r.get("description", ""),
                "guide": r.get("guide", ""),
                "url": r.get("url", ""),
                "is_finish": bool(r.get("is_finish")),
            })
        return tasks