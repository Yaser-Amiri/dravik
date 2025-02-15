from typing import cast

from dravik.services import AppServices
from textual.app import App
from textual.reactive import reactive

from dravik.models import AppState

# The whole thing is a workaround, since type of "self.app" in the
# textual widgets is always "App[object]"


def get_app_state(app: App[object]) -> AppState:
    state = getattr(app, "state", None)
    assert isinstance(state, AppState)
    return state


def mutate_app_state(app: App[object]) -> None:
    state = getattr(app.__class__, "state", None)
    assert state is not None
    app.mutate_reactive(cast(reactive[AppState], state))


def get_app_services(app: App[object]) -> AppServices:
    services = getattr(app, "services", None)
    assert isinstance(services, AppServices)
    return services
