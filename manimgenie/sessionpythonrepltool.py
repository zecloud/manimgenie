"""This is the Azure Dynamic Sessions module.

This module provides the SessionsPythonREPLTool class for
managing dynamic sessions in Azure.
"""

import re
import urllib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, BinaryIO, Callable, List, Literal, Optional, Tuple
from uuid import uuid4

import requests
from azure.core.credentials import AccessToken
from azure.identity import DefaultAzureCredential
from langchain_core.tools import BaseTool



@dataclass
class CodeBlock:
    """A code block extracted fromm an agent message."""

    code: str
    language: str

def extract_markdown_code_blocks(markdown_text: str) -> List[CodeBlock]:
    pattern = re.compile(r"```(?:\s*([\w\+\-]+))?\n([\s\S]*?)```")
    matches = pattern.findall(markdown_text)
    code_blocks: List[CodeBlock] = []
    for match in matches:
        language = match[0].strip() if match[0] else ""
        code_content = match[1]
        code_blocks.append(CodeBlock(code=code_content, language=language))
    return code_blocks



USER_AGENT = f"langchain-azure-dynamic-manim/custom (Language=Python)"


def _access_token_provider_factory() -> Callable[[], Optional[str]]:
    """Factory function for creating an access token provider function.

    Returns:
        Callable[[], Optional[str]]: The access token provider function
    """
    access_token: Optional[AccessToken] = None

    def access_token_provider() -> Optional[str]:
        nonlocal access_token
        if access_token is None or datetime.fromtimestamp(
            access_token.expires_on, timezone.utc
        ) < datetime.now(timezone.utc) + timedelta(minutes=5):
            credential = DefaultAzureCredential()
            access_token = credential.get_token("https://dynamicsessions.io/.default")
        return access_token.token

    return access_token_provider


def _sanitize_input(query: str) -> str:
    """Sanitize input to the python REPL.

    Remove whitespace, backtick & python (if llm mistakes python console as terminal)

    Args:
        query: The query to sanitize

    Returns:
        str: The sanitized query
    """
    # Removes `, whitespace & python from start
    query = re.sub(r"^(\s|`)*(?i:python)?\s*", "", query)
    # Removes whitespace & ` from end
    query = re.sub(r"(\s|`)*$", "", query)
    return query


@dataclass
class RemoteFileMetadata:
    """Metadata for a file in the session."""

    filename: str
    """The filename relative to `/mnt/data`."""

    size_in_bytes: int
    """The size of the file in bytes."""

    @property
    def full_path(self) -> str:
        """Get the full path of the file."""
        return f"/mnt/data/{self.filename}"

    @staticmethod
    def from_dict(data: dict) -> "RemoteFileMetadata":
        """Create a RemoteFileMetadata object from a dictionary."""
        properties = data.get("properties", {})
        return RemoteFileMetadata(
            filename=properties.get("filename"),
            size_in_bytes=properties.get("size"),
        )


class SessionsPythonREPLTool(BaseTool):
    r"""Azure Dynamic Sessions tool.

    Setup:
        Install ``langchain-azure-dynamic-sessions`` and create a session pool, which you can do by following the instructions [here](https://learn.microsoft.com/en-us/azure/container-apps/sessions-code-interpreter?tabs=azure-cli#create-a-session-pool-with-azure-cli).

        .. code-block:: bash

            pip install -U langchain-azure-dynamic-sessions

        .. code-block:: python

            import getpass

            POOL_MANAGEMENT_ENDPOINT = getpass.getpass("Enter the management endpoint of the session pool: ")

    Instantiation:
        .. code-block:: python

            from langchain_azure_dynamic_sessions import SessionsPythonREPLTool

            tool = SessionsPythonREPLTool(
                pool_management_endpoint=POOL_MANAGEMENT_ENDPOINT
            )


    Invocation with args:
        .. code-block:: python

            tool.invoke("6 * 7")

        .. code-block:: python

            '{\\n  "result": 42,\\n  "stdout": "",\\n  "stderr": ""\\n}'

    Invocation with ToolCall:

        .. code-block:: python

            tool.invoke({"args": {"input":"6 * 7"}, "id": "1", "name": tool.name, "type": "tool_call"})

        .. code-block:: python

            '{\\n  "result": 42,\\n  "stdout": "",\\n  "stderr": ""\\n}'
    """  # noqa: E501

    name: str = "Python_REPL"
    description: str = (
        "A Python shell. Use this to execute python commands "
        "when you need to perform calculations or computations. "
        "Input should be a valid python command. "
        "Returns a JSON object with the result, stdout, and stderr. "
    )

    sanitize_input: bool = True
    """Whether to sanitize input to the python REPL."""

    pool_management_endpoint: str
    """The management endpoint of the session pool. Should end with a '/'."""

    access_token_provider: Callable[[], Optional[str]] = (
        _access_token_provider_factory()
    )
    """A function that returns the access token to use for the session pool."""

    session_id: str = str(uuid4())
    """The session ID to use for the code interpreter. Defaults to a random UUID."""

    response_format: Literal["content_and_artifact"] = "content_and_artifact"

    def _build_url(self, path: str) -> str:
        pool_management_endpoint = self.pool_management_endpoint
        if not pool_management_endpoint:
            raise ValueError("pool_management_endpoint is not set")
        if not pool_management_endpoint.endswith("/"):
            pool_management_endpoint += "/"
        encoded_session_id = urllib.parse.quote(self.session_id)
        query = f"identifier={encoded_session_id}"#&api-version=2024-02-02-preview"
        query_separator = "&" if "?" in pool_management_endpoint else "?"
        full_url = pool_management_endpoint + path + query_separator + query
        return full_url

    def createfile(self,pythoncode:str,scene_name:str):
        """Create a python code file in the session."""
        access_token = self.access_token_provider()
        api_url = self._build_url("manim/create")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        pyfile=scene_name+".py"
        datatosend = BytesIO((pyfile + "\n" + pythoncode).encode('utf-8'))
        
        response = requests.post(api_url, headers=headers, data=datatosend)
        try:
            response.raise_for_status()
        except Exception as e:
            print(response.text)
            raise e
        if response.status_code == 200:
            return True

    def execute(self,scene_name:str) -> Any:
        """Execute Python code in the session."""

        access_token = self.access_token_provider()
        api_url = self._build_url("manim/generate")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        
        body = { 
            "command": "manim -qh "+scene_name+".py "+scene_name +" -o "+scene_name+".mp4"  
        }  

        response = requests.post(api_url, headers=headers, json=body)
        try:
            response.raise_for_status()
        except Exception as e:
            print(response.text)
            if response.status_code == 500:
                response = requests.post(api_url, headers=headers, json=body)
                response.raise_for_status()
            else:
                raise e
        response_json = response.json()
        return response_json

    def _run(self, python_code: str, **kwargs: Any) -> Tuple[str, dict]:
        match = re.search(r'class\s+(\w+)', python_code)
        if match:
            scene_name = match.group(1)
        else:
            return "No class name found in the code"
        if(self.createfile(python_code,scene_name)):
            response = self.execute(scene_name)
        else:
            return "Error creating file",{}
        if response.get("status") == "success":
            result = response.get("output")
        else:
            result = response.get("message")
        return result,response



    def download_file(
        self, *, remote_file_path: str, local_file_path: Optional[str] = None
    ) -> BinaryIO:
        """Download a file from the session.

        Args:
            remote_file_path: The path to download the file from,
                relative to `/mnt/data`.
            local_file_path: The path to save the downloaded file to.
                If not provided, the file is returned as a BufferedReader.

        Returns:
            BinaryIO: The data of the downloaded file.
        """
        access_token = self.access_token_provider()
        api_url = self._build_url(f"manim/get_video")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
        }
        body= {
                "videofile": remote_file_path.replace("'","")
            }
        response = requests.post(api_url, headers=headers, json=body)
        try:
            response.raise_for_status()
        except Exception as e:
            print(response.text)
            if response.status_code == 404:
                response = requests.post(api_url, headers=headers, json=body)
                response.raise_for_status()
            raise e

        if local_file_path:
            with open(local_file_path, "wb") as f:
                f.write(response.content)

        return BytesIO(response.content)
