from typing import Callable, List, Dict

subscribers: Dict[str, List[Callable]] = {}


def subscribe(event_name: str, callback: Callable):
    global subscribers

    if event_name not in subscribers:
        subscribers[event_name] = []

    subscribers[event_name].append(callback)


def emit(event_name: str, *args, **kwargs):
    global subscribers
    if event_name not in subscribers:
        return False

    for sub in subscribers[event_name]:
        sub(*args, **kwargs)
