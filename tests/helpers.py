import csv
import json
import pathlib
import re
import shutil
import typing
from importlib import resources
from urllib import parse

from googleapiclient import http

# testing google api:
# https://github.com/googleapis/google-api-python-client/blob/main/docs/mocks.md


def get_resource_path(end_path: str):
    full_path = resources.files("resources").joinpath(end_path)
    with resources.as_file(full_path) as file_path:
        result = file_path.absolute()
    return result


def rename_resources():
    resources_path = resources.files("resources")
    with resources.as_file(resources_path) as file_path:
        resources_dir = file_path.absolute()

    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}.\d{6}-response.json$")
    for res_dir in resources_dir.iterdir():
        if not res_dir.is_dir():
            continue
        if res_dir.name == "raw-req-res":
            continue
        res_files = sorted([i for i in res_dir.iterdir() if i.is_file()])
        for index, res_file in enumerate(res_files):
            if not res_file.is_file():
                continue
            match = pattern.match(res_file.name)
            if not match:
                continue
            new_file = res_file.with_stem(f"api-{index + 1:03}")
            shutil.move(res_file, new_file)


def check_reports(output_items: list[dict]):
    actual_report_paths = []
    for output_item in output_items:
        report_class = output_item["report_class"]
        actual_path = output_item["actual_path"]
        expected_path = output_item["expected_path"]

        actual_file = next(actual_path.iterdir())
        actual_report_paths.append(actual_file)

        actual_csv = csv.DictReader(actual_file.read_text().splitlines())
        actual_reports = [report_class(**row) for row in actual_csv]

        expected_file = get_resource_path(expected_path)
        expected_csv = csv.DictReader(expected_file.read_text().splitlines())
        expected_reports = [report_class(**row) for row in expected_csv]

        assert actual_reports == expected_reports
    return actual_report_paths


def api_json_files(dir_name: str):
    files = sorted(
        [
            i
            for i in get_resource_path(dir_name).iterdir()
            if i.is_file() and i.name.startswith("api-") and i.suffix == ".json"
        ]
    )
    return files


def compare_logs(actual_logs_raw, name: str, reports_paths: list[pathlib.Path]) -> None:
    actual_logs = [(lvl, msg) for lg, lvl, msg in actual_logs_raw]
    expected_logs_file = get_resource_path(f"{name}/expected_logs.csv")

    expected_logs = list(csv.DictReader(expected_logs_file.read_text().splitlines()))
    for index, i in enumerate(expected_logs):
        for reports_path in reports_paths:
            report_type = reports_path.stem.split("-")[-1]
            prefix = f"Writing {report_type} report"
            msg = i.get("message")
            if msg and msg.startswith(prefix):
                i["message"] = f"Writing {report_type} report '{reports_path.name}'."
        expected_logs[index] = (int(i.get("level")), i.get("message"))

    assert actual_logs == expected_logs


class FileMoverHttpMock(http.HttpMock):
    def __init__(
        self,
        filename: typing.Optional[typing.Union[str, pathlib.Path]] = None,
        headers: typing.Optional[typing.Mapping[str, str]] = None,
    ):
        self._filename = filename
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

        # ensure actual request matches expected request
        provided = self._provided_items.pop(0)
        expected_uri = provided.request_data.get("uri")
        if uri != expected_uri:
            assert uri == expected_uri

        expected_method = provided.request_data.get("method")
        if method != expected_method:
            assert method == expected_method

        expected_body = provided.request_data.get("body")
        if body is None and expected_body is not None or body != expected_body:
            assert body == expected_body

        # execute the request
        result_headers, result_data = super().request(
            uri, method, body, headers, redirections, connection_type
        )

        # check the response
        if not result_headers:
            raise ValueError("Must provide response headers.")

        if (
            result_headers.get("status") == "200"
            and method != "DELETE"
            and not result_data
        ):
            raise ValueError("Must provide response data.")

        return result_headers, result_data
