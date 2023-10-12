import logging

from litestar import Litestar
from litestar.datastructures import State
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState
from taskiq.cli.utils import import_object

logger = logging.getLogger("taskiq.litestar")


def startup_event_generator(broker: AsyncBroker, app_path: str) -> None:
    async def startup_event(state: TaskiqState) -> None:
        if not broker.is_worker_process:
            return
        app = import_object(app_path)
        if not isinstance(app, Litestar):
            app = app()

        if not isinstance(app, Litestar):
            raise TypeError(f"{app_path} is not a Litestar app")

        ctx = app.lifespan()
        state._litestar_lifespan = ctx
        await ctx.__aenter__()
        broker.add_dependency_context(
            {
                Litestar: app,
                State: app.state,
            },
        )

    return startup_event


def shutdown_event_generator(broker: AsyncBroker) -> None:
    async def shutdown_event(state: TaskiqState) -> None:
        if not broker.is_worker_process:
            return
        try:
            await state._litestar_lifespan.__aexit__(None, None, None)
        except RuntimeError as exc:
            logger.warning(exc)

    return shutdown_event


def init(broker: AsyncBroker, app: str) -> None:
    broker.add_event_handler(
        TaskiqEvents.WORKER_STARTUP,
        startup_event_generator(broker, app),
    )
    broker.add_event_handler(
        TaskiqEvents.WORKER_SHUTDOWN,
        shutdown_event_generator(broker),
    )
