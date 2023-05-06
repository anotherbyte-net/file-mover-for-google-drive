import json
import pathlib
import typing
from importlib import resources
from urllib import parse

from googleapiclient import http

# testing google api:
# https://github.com/googleapis/google-api-python-client/blob/main/docs/mocks.md


class FileMoverHttpMock(http.HttpMock):
    def __init__(
        self,
        filename: typing.Optional[typing.Union[str, pathlib.Path]] = None,
        headers: typing.Optional[typing.Mapping[str, str]] = None,
    ):
        if filename:
            with resources.as_file(
                resources.files("resources").joinpath(filename)
            ) as file_path:
                filename = file_path.absolute()

        if headers is None:
            headers = self.get_status_ok()

        super().__init__(filename, headers)

    def __iter__(self):
        items = [self.response_headers or {}, self.response_str]
        for item in items:
            yield item

    @classmethod
    def get_status_ok(cls):
        return {"status": "200"}

    @classmethod
    def get_status_bad_request(cls):
        return {"status": "400"}

    @classmethod
    def get_status_not_found(cls):
        return {"status": "404"}

    @property
    def request_data(self) -> typing.Mapping:
        return json.loads(self.data).get("request", {}) if self.data else {}

    @property
    def request_str(self) -> str:
        return json.dumps(self.request_data) if self.request_data else b""

    @property
    def response_data(self) -> typing.Mapping:
        return json.loads(self.data).get("response", {}) if self.data else {}

    @property
    def response_str(self) -> str:
        return json.dumps(self.response_data) if self.response_data else b""

    def __str__(self):
        req_data = self.request_data
        req_method_id = req_data.get("methodId")
        req_method = req_data.get("method")
        req_uri = req_data.get("uri")
        req = f"{req_method_id}: {req_method} {req_uri}"

        res_data = self.response_data
        res_files = res_data.get("files", [])
        res_perms = res_data.get("permissions", [])
        if res_files:
            res = f"{len(res_data)} files"
        elif res_perms:
            res = f"{len(res_data)} permissions"
        else:
            res = "dict"
        return f"Response: {res}; Request: {req};"

    def __repr__(self):
        return str(self)


class FileMoverHttpMockSequence(http.HttpMockSequence):
    def __init__(self, iterable):
        # Ensure iterable is a list, so the items can be seen more than once.
        items = list(iterable)
        super().__init__(items)
        self._provided_items = list(iterable)

    def request(
        self,
        uri,
        method="GET",
        body=None,
        headers=None,
        redirections=1,
        connection_type=None,
    ):
        if not self._iterable or len(self._iterable) < 1:
            parsed_url = parse.urlparse(uri)
            parsed_qs = parse.parse_qs(parsed_url.query)
            params = {
                "path": parsed_url.path,
                "query": parsed_qs,
                "method": method,
                "body": body,
            }
            raise ValueError(f"No mock available: " f"{json.dumps(params, indent=2)}'.")

        result_headers, result_data = super().request(
            uri, method, body, headers, redirections, connection_type
        )

        provided = self._provided_items.pop(0)
        expected_uri = provided.request_data.get("uri")
        if uri != expected_uri:
            assert uri == expected_uri

        if not result_headers:
            raise ValueError("Must provide response headers.")

        if result_headers.get("status") == "200" and not result_data:
            raise ValueError("Must provide response data.")

        return result_headers, result_data
