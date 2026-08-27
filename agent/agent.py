from __future__ import annotations

import threading
import time

import requests

from .tools import (
    TOOLS,
    find_files,
    git_diff,
    git_status,
    read_file,
    search_code,
)


SYSTEM_PROMPT = """
You are a local senior software architect engineering agent
working on a real repository.

The repository can contain:

- Java
- Spring
- JavaScript
- TypeScript
- C++
- Lua
- XML
- JSON
- YAML
- game-development code

IMPORTANT RULES:

1. Never invent a file.
2. Never invent a class.
3. Never invent a function.
4. Never invent a path.
5. Search the repository before making claims.
6. If an exact filename isn't found, try partial searches.
7. Read relevant files before explaining them.
8. Follow references between files when useful.
9. Give repository-relative paths.
10. Give line numbers when available.
11. Use tools until you have enough evidence.
12. Do not modify files.
13. Do not execute arbitrary shell commands.

You are primarily a codebase investigation agent.
"""


TOOL_FUNCTIONS = {

    "search_code": search_code,

    "find_files": find_files,

    "read_file": read_file,

    "git_status": git_status,

    "git_diff": git_diff,
}


class Agent:

    def __init__(
        self,
        repo,
        config,
        activity=None,
    ):

        self.repo = repo

        self.config = config

        self.activity = activity


    def request(
        self,
        messages,
    ):

        response = requests.post(

            (
                f"{self.config.ollama_url}"
                "/api/chat"
            ),

            json={

                "model":
                    self.config.model,

                "messages":
                    messages,

                "tools":
                    TOOLS,

                "stream":
                    False,

                "think":
                    True,
            },

            timeout=300,
        )

        response.raise_for_status()

        return response.json()


    def execute(
        self,
        name,
        arguments,
    ):

        fn = TOOL_FUNCTIONS.get(name)

        if fn is None:

            return (
                f"ERROR: unknown tool "
                f"'{name}'."
            )


        try:

            if name == "search_code":

                return fn(
                    self.repo,
                    arguments.get(
                        "query",
                        "",
                    ),
                    arguments.get(
                        "file_types"
                    ),
                )


            if name == "find_files":

                return fn(
                    self.repo,
                    arguments.get(
                        "pattern",
                        "",
                    ),
                )


            if name == "read_file":

                return fn(
                    self.repo,
                    arguments.get(
                        "path",
                        "",
                    ),
                )


            return fn(self.repo)


        except Exception as exc:

            return (
                f"ERROR executing "
                f"{name}: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )


    def run(
        self,
        question,
        max_iterations=12,
    ):

        messages = [

            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },

            {
                "role": "user",
                "content": (
                    f"Repository root:\n"
                    f"{self.repo}\n\n"
                    f"Developer request:\n"
                    f"{question}"
                ),
            },
        ]


        for _ in range(max_iterations):

            if self.activity:

                self.activity.start(
                    "Thinking..."
                )


            result = {
                "response": None,
                "error": None,
            }


            def worker():

                try:

                    result["response"] = (
                        self.request(messages)
                    )

                except Exception as exc:

                    result["error"] = exc


            thread = threading.Thread(
                target=worker
            )

            thread.start()


            while thread.is_alive():

                if self.activity:

                    self.activity.refresh()

                time.sleep(0.08)


            thread.join()


            if result["error"]:

                if self.activity:

                    self.activity.error(
                        "Ollama request failed"
                    )

                raise result["error"]


            if self.activity:

                self.activity.success(
                    "Thinking complete"
                )


            response = result["response"]

            message = response.get(
                "message",
                {},
            )

            tool_calls = message.get(
                "tool_calls",
                [],
            )

            content = message.get(
                "content",
                "",
            )


            # No more tools.
            # Model is finished.

            if not tool_calls:

                return (
                    content
                    or
                    "The model returned "
                    "an empty response."
                )


            messages.append(message)


            for call in tool_calls:

                function = call.get(
                    "function",
                    {},
                )

                name = function.get(
                    "name",
                    "",
                )

                arguments = function.get(
                    "arguments",
                    {},
                )


                if not isinstance(
                    arguments,
                    dict,
                ):

                    arguments = {}


                if self.activity:

                    self.activity.start(
                        f"Running {name}"
                    )


                tool_result = self.execute(
                    name,
                    arguments,
                )


                if len(tool_result) > 40000:

                    tool_result = (
                        tool_result[:40000]
                        +
                        "\n\n[OUTPUT TRUNCATED]"
                    )


                if self.activity:

                    if tool_result.startswith(
                        "ERROR"
                    ):

                        self.activity.error(
                            f"{name} failed"
                        )

                    elif tool_result.startswith(
                        "No "
                    ):

                        self.activity.warning(
                            f"{name}: nothing found"
                        )

                    else:

                        self.activity.success(
                            f"{name} complete"
                        )


                messages.append(
                    {
                        "role": "tool",

                        "tool_name": name,

                        "content": tool_result,
                    }
                )


        return (
            "The agent reached its "
            "maximum number of iterations."
        )