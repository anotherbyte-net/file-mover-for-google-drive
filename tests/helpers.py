import json
from importlib import resources
from urllib import parse

from googleapiclient import http

# testing google api:
# https://github.com/googleapis/google-api-python-client/blob/main/docs/mocks.md


class FileMoverHttpMock(http.HttpMock):
    def __init__(self, filename=None, headers=None):
        if filename:
            with resources.as_file(
                resources.files("resources").joinpath(filename)
            ) as file_path:
                filename = file_path.absolute()

        if headers is None:
            headers = self.get_status_ok()

        super().__init__(filename, headers)

    def __iter__(self):
        items = [
            self.response_headers or {},
            self.data or "",
        ]
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


class FileMoverHttpMockSequence(http.HttpMockSequence):
    def __init__(self, iterable):
        # Ensure iterable is a list, so the items can be seen more than once.
        super().__init__(list(iterable))

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

        if not result_headers:
            raise ValueError("Must provide response headers.")

        if result_headers.get("status") == "200" and not result_data:
            raise ValueError("Must provide response data.")

        return result_headers, result_data