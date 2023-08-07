from flask import request

from src.FileManager import Cache
from src.Recorder import RecordManager
from src.main_web_UI import WebUI


class APIServer(WebUI):
    works_keys = {
        10: (
            "作品ID",
            "作品描述",
            "发布时间",
            "UID",
            "作者昵称",
            "账号标识",
            "下载链接",
            "原声信息",
            "静态封面图",
            "动态封面图"),
        8: (
            "作品ID",
            "作品描述",
            "发布时间",
            "UID",
            "作者昵称",
            "账号标识",
            "下载链接",
            "原声信息"),
        6: (
            "主播昵称",
            "直播标题",
            "推流地址",
            "直播封面",
            "观看次数",
            "在线观众",
        ),
        17: RecordManager.Comment_Title,
        21: RecordManager.User_Title[1:],
    }

    def __init__(self, colour, blacklist, xb, user_agent, code, settings):
        super().__init__(colour, blacklist, xb, user_agent, code, settings)

    def update_parameters(self, parameters):
        parameters = {
            i: j for i,
            j in parameters.items() if i in self.settings_keys}
        settings = self.settings.read()
        for i, j in parameters.items():
            settings[i] = j
        self.settings.update(settings)
        if c := parameters.get("cookie"):
            self.cookie.extract(c, 0)
        self.configuration(filename=self.filename)

    def add_params(self, params=None, **kwargs):
        save, root, params_ = self.record.run(
            self._data["root"], format_=self._data["save"], **kwargs)
        if not params:
            return save, root, params_
        params["save"] = save
        params["root"] = root
        params["params"] = params_

    def format_data(self, data: list):
        result = []
        if not data:
            return result
        keys = self.works_keys[len(data[0])]
        for item in data:
            dict_ = {keys[i]: j for i, j in enumerate(item)}
            result.append(dict_)
        return result

    def check_url(self, data: dict, **kwargs):
        url = data.get('url')
        url = self.request.run_alone(url, solo=True, **kwargs)
        return url[0] if url else {"message": "url error"}

    @staticmethod
    def request_failed():
        return {
            "message": "request failed",
        }

    def run_server(self, app):
        @app.route('/init/', methods=['POST'])
        def init():
            self.update_parameters(request.json)
            return {"message": "success"}

        @app.route('/account/', methods=['POST'])
        def account():
            if isinstance(
                    url := self.check_url(
                        request.json,
                        user=True),
                    dict):
                return url
            params = {
                "num": 0,
                "mark": "",
                "url": url,
                "mode": request.json.get('mode', "post"),
                "earliest": request.json.get('earliest', ""),
                "latest": request.json.get('latest', ""),
            }
            self.manager = Cache(
                self.logger,
                self._data["root"],
                type_="UID",
                mark=self.mark,
                name=self.nickname)
            self.add_params(params)
            self.download.download = False
            self.request.pages = request.json.get('pages', self._data["pages"])
            if not self.get_account_works(**params):
                return self.request_failed()
            return {
                "video": self.format_data(self.download.video_data),
                "image": self.format_data(self.download.image_data),
                "message": "success",
            }

        @app.route('/detail/', methods=['POST'])
        def detail():
            if isinstance(url := self.check_url(request.json), dict):
                return url
            save, root, params = self.add_params()
            with save(root, **params) as data:
                self.download.data = data
                self.download.download = False
                data = self.download.run_alone(url, False)
            if not data:
                return self.request_failed()
            return {
                "detail": self.format_data(data),
                "message": "success",
            }

        @app.route('/live/', methods=['POST'])
        def live():
            self.request.headers['Referer'] = "https://live.douyin.com"
            if not (
                    data := self.request.run_live(
                        request.json.get('url'),
                        True)):
                return self.request_failed()
            self.request.headers['Referer'] = "https://www.douyin.com/"
            return {
                "live": self.format_data(data),
                "message": "success",
            }

        @app.route('/comment/', methods=['POST'])
        def comment():
            if isinstance(url := self.check_url(request.json), dict):
                return url
            save, root, params = self.add_params(type_="comment")
            self.request.pages = request.json.get('pages', self._data["pages"])
            with save(root, name=f"作品{url}_评论数据", **params) as data:
                self.request.run_comment(url, data, True)
            return {
                "comment": self.format_data(self.request.comment_data),
                "message": "success",
            }

        @app.route('/mix/', methods=['POST'])
        def mix():
            if isinstance(
                    url := self.check_url(
                        request.json,
                        value="合集ID"),
                    dict):
                return url
            self.manager = Cache(
                self.logger,
                self._data["root"],
                type_="MIX",
                mark=self.mark,
                name=self.nickname)
            params = {"mark": ""}
            self.add_params(params, type_="mix")
            params["mix_info"] = self.get_mix_info(url, False)
            if not params["mix_info"]:
                return {
                    "message": "Request to collection data failed"
                }
            self.download.download = False
            self.download_mix(**params)
            return {
                "video": self.format_data(self.download.video_data),
                "image": self.format_data(self.download.image_data),
                "message": "success",
            }

        @app.route("/user/", methods=["POST"])
        def user():
            if isinstance(
                    url := self.check_url(
                        request.json,
                        user=True),
                    dict):
                return url
            self.request.url = url
            if not (data := self.request.run_user()):
                self.logger.warning(f"{url} 获取账号数据失败")
                return {
                    "message": "Request for account data failed"
                }
            save, root, params = self.add_params(type_="user")
            with save(root, name="UserData", **params) as file:
                self.request.save_user(file, data)
            return {
                "account": self.format_data([data]),
                "message": "success",
            }

        return app
