"""UI utility module
"""
from typing import Union


def show_progress(current: Union[int, float], total: Union[int, float], msg: str = None):
    msg_print = f'[{"#" * int(current/total*50)}{" " * int((total-current)/total*50)}] ' \
                f'({current/total*100:.1f}%)'
    if msg is not None:
        msg_print += f' {msg}'

    print(msg_print, end='\r')


def reset_progress():
    print('')
