import logging
from typing import Awaitable, Callable

from litestar import Litestar
from litestar.datastructures import State
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState
from taskiq.cli.utils import import_object

logger = logging.getLogger("taskiq.litestar")


def startup_event_generator(
    broker: AsyncBroker,
    app_path: str,
) -> Callable[[TaskiqState], Awaitable[None]]:
    """
    Generate a startup event.

    This function is used to generate a function that
    starts Litestar app and adds dependencies context to the broker.
    """

    async def startup_event(state: TaskiqState) -> None:
        if not broker.is_worker_process:
            return
        app = import_object(app_path)
        if not isinstance(app, Litestar):
            app = app()

        if not isinstance(app, Litestar):
            raise TypeError(f"{app_path} is not a Litestar app")

        ctx = app.lifespan()
        state._litestar_lifespan = ctx  # noqa: SLF001
        await ctx.__aenter__()
        populate_dependency_context(broker, app)

    return startup_event


def shutdown_event_generator(
    broker: AsyncBroker,
) -> Callable[[TaskiqState], Awaitable[None]]:
    """
    Generate shutdown event.

    This function is used to generate a function that
    shutdowns Litestar app.
    """

    async def shutdown_event(state: TaskiqState) -> None:
        if not broker.is_worker_process:
            return
        try:
            await state._litestar_lifespan.__aexit__(None, None, None)  # noqa: SLF001
        # We have this warning, because we exit the context manager
        # in a different task that were used to open it.
        except RuntimeError as exc:
            logger.warning(exc)

    return shutdown_event


def init(broker: AsyncBroker, app: str) -> None:
    """
    Initialize integraton.

    This function adds startup and shutdown events
    that are the same as your Litestar app's lifespan.
    """
    broker.add_event_handler(
        TaskiqEvents.WORKER_STARTUP,
        startup_event_generator(broker, app),
    )
    broker.add_event_handler(
        TaskiqEvents.WORKER_SHUTDOWN,
        shutdown_event_generator(broker),
    )


def populate_dependency_context(broker: AsyncBroker, app: Litestar) -> None:
    """
    Populate dependency context.

    This function adds Litestar app and its state to the broker's dependency context.
    """
    broker.add_dependency_context(
        {
            Litestar: app,
            State: app.state,
        },
    )
