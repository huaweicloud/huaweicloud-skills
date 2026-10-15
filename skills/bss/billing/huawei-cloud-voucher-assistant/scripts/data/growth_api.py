"""Growth-center (开发者成长中心) 任务列表数据源 adapter。

通过 fwdo 匿名端点查询成长中心公开任务列表（零配置，无需 Cookie/CSRF/appcode）。
积分余额（个人数据，bonus-beans）需 fwdu 登录态，本适配器不提供。
"""


from data.hdcommunity_client import HdgrowthWebClient


class GrowthAdapter:
    """开发者成长中心任务数据源统一接口。"""

    def list_point_tasks(self):
        """返回任务列表，每项:
        {"task_id", "task_name", "points", "cycle", "category",
         "description", "guide", "url", "is_finish"}。
        """
        raise NotImplementedError


class HdgrowthWebAdapter(GrowthAdapter):
    """基于成长中心前端 API（fwdo 匿名路径）的任务列表适配器。

    无需 Cookie/CSRF/appcode，零配置可用。
    只提供公开任务列表（不含个人完成状态）。

    Args:
        client: 已构造的 HdgrowthWebClient；缺省用环境变量构造。
        **client_kwargs: 透传给 HdgrowthWebClient（base_url 等）。
    """

    def __init__(self, client=None, **client_kwargs):
        self.client = client or HdgrowthWebClient(**client_kwargs)

    def list_point_tasks(self, page_no=1, page_size=20):
        return self.client.list_missions(page_no=page_no, page_size=page_size)


def get_adapter(**client_kwargs):
    """工厂：返回 fwdo 匿名任务列表适配器（零配置，始终可用）。"""
    return HdgrowthWebAdapter(**client_kwargs)