# Taskiq Litestar

This project adds integration with [Litestar](https://litestar.dev/) to [TaskIQ](https://taskiq-python.github.io/).

Mainly this project focuses on running starup and shutdown events declared in your litestar app
on worker nodes. This will allow you to access application's state and data from within your tasks.

Also we add a few dependencies that you can depend on in your tasks.
* `State` from `litestar.datastructures`;
* `Litestar` from `litestar`.

# Installation

```bash
pip install taskiq-litestar
```

# Usage

Here we have a script called `test_script.py` so the listestar app can be found at `test_script:app`. We use strings to resolve application to bypass circular imports.

In the declared task I depend on a state.

```python
from contextlib import asynccontextmanager

from litestar import Litestar, get
from litestar.datastructures import State
from taskiq import TaskiqDepends
from taskiq_redis import ListQueueBroker

import taskiq_litestar

broker = ListQueueBroker("redis://localhost:6379/0")

taskiq_litestar.init(
    broker,
    "test_script:app",
)


@asynccontextmanager
async def app_lifespan(app: Litestar) -> None:
    """Lifespan generator."""
    if not broker.is_worker_process:
        await broker.startup()

    app.state.value = "abc123"

    yield

    if not broker.is_worker_process:
        await broker.shutdown()


@broker.task()
async def my_task(state: State = TaskiqDepends()) -> None:
    """My task."""
    print("a", state.dict())  # noqa: T201


@get("/")
async def index() -> str:
    """Index get handler."""
    await my_task.kiq()
    return "Task sent"


app = Litestar([index], lifespan=[app_lifespan])
```

# Manually update dependency context

When using InMemoryBroker you can manually update the dependency context.
This might come handy when setting up tests.

```python
import taskiq_litestar
from taskiq import InMemoryBroker

broker = InMemoryBroker()

app = FastAPI()

taskiq_fastapi.init(broker, "test_script:app")
taskiq_fastapi.populate_dependency_context(broker, app)
```
