subscribers = {}


def subscribe(event_type: str, callback):
    global subscribers

    if event_type not in subscribers:
        subscribers[event_type] = []

    subscribers[event_type].append(callback)


def post_event(event_type: str, *args, **kwargs):
    global subscribers
    if event_type not in subscribers:
        return False

    for sub in subscribers[event_type]:
        sub(*args, **kwargs)