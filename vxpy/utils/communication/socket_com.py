"""Unified length-prefixed socket protocol for multiple payload types.
"""
import json
import socket
import struct
from typing import Any, Optional, Tuple

import numpy as np

# Low-level framing


_HDR = struct.Struct('!I')  # 4-byte unsigned length, network byte order


def _send_all(sock: socket.socket, data: bytes) -> None:
    view = memoryview(data)
    total = 0
    while total < len(view):
        sent = sock.send(view[total:])
        if sent == 0:
            raise ConnectionError('socket connection broken during send')
        total += sent


def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError(f'peer closed while expecting {n} bytes (got {len(buf)})')
        buf += chunk
    return bytes(buf)


def send_msg(sock: socket.socket, payload: bytes, *, max_len: int = 64 * 1024 * 1024) -> None:
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        raise TypeError('payload must be bytes-like')
    length = len(payload)
    if length > max_len:
        raise ValueError(f'payload length {length} exceeds max_len {max_len}')
    _send_all(sock, _HDR.pack(length))
    if length:
        _send_all(sock, payload)


def recv_msg(sock: socket.socket, *, max_len: int = 64 * 1024 * 1024) -> bytes:
    (length,) = _HDR.unpack(_recv_exactly(sock, _HDR.size))
    if length > max_len:
        raise ValueError(f'announced length {length} exceeds max_len {max_len}')
    return _recv_exactly(sock, length) if length else b''


def set_nodelay(sock: socket.socket, enabled: bool = True):
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, int(enabled))


# Header internal

def _send_header(sock: socket.socket, header: dict) -> None:
    data = json.dumps(header, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    send_msg(sock, data)


def _recv_header(sock: socket.socket) -> dict:
    data = recv_msg(sock)
    header = json.loads(data.decode('utf-8'))
    if not isinstance(header, dict) or 'type' not in header:
        raise ValueError('invalid header: missing type')
    return header


# Type handlers

def send_bytes(sock: socket.socket, b: bytes) -> None:
    _send_header(sock, {'type': 'bytes'})
    send_msg(sock, b)


def recv_bytes(sock: socket.socket) -> bytes:
    hdr = _recv_header(sock)
    if hdr.get('type') != 'bytes':
        raise ValueError(f'unexpected type {hdr.get("type")} (expected bytes)')
    return recv_msg(sock)


def send_text(sock: socket.socket, s: str, *, encoding: str = 'utf-8') -> None:
    _send_header(sock, {'type': 'text', 'encoding': encoding})
    send_msg(sock, s.encode(encoding))


def recv_text(sock: socket.socket) -> str:
    hdr = _recv_header(sock)
    if hdr.get('type') != 'text':
        raise ValueError(f'unexpected type {hdr.get("type")} (expected text)')
    enc = hdr.get('encoding', 'utf-8')
    return recv_msg(sock).decode(enc)


def send_json(sock: socket.socket, obj: Any, *, ensure_ascii: bool = False) -> None:
    meta = {'type': 'json', 'ensure_ascii': bool(ensure_ascii)}
    _send_header(sock, meta)
    data = json.dumps(obj, ensure_ascii=ensure_ascii, separators=(',', ':')).encode('utf-8')
    send_msg(sock, data)


def recv_json(sock: socket.socket) -> Any:
    hdr = _recv_header(sock)
    if hdr.get('type') != 'json':
        raise ValueError(f'unexpected type {hdr.get("type")} (expected json)')
    return json.loads(recv_msg(sock).decode('utf-8'))


def _array_order(a) -> str:
    # Prefer 'F' only if it's exclusively Fortran contiguous
    if a.flags['F_CONTIGUOUS']:
        return 'F'
    return 'C'


def send_ndarray(sock: socket.socket, arr, *, max_len_bytes: int = 2**31 - 1) -> None:
    if not isinstance(arr, np.ndarray):
        raise TypeError('arr must be a numpy.ndarray')

    order = _array_order(arr)
    if order == 'C' and not arr.flags['C_CONTIGUOUS']:
        arr = np.ascontiguousarray(arr)
    elif order == 'F' and not arr.flags['F_CONTIGUOUS']:
        arr = np.asfortranarray(arr)

    hdr = {
        'type': 'ndarray',
        'dtype': arr.dtype.str,   # includes byteorder, e.g. '<f8'
        'shape': arr.shape,
        'order': order,
    }
    _send_header(sock, hdr)

    raw = arr.tobytes(order=order)
    if len(raw) > max_len_bytes:
        raise ValueError(f'ndarray payload {len(raw)} exceeds max_len_bytes {max_len_bytes}')
    send_msg(sock, raw, max_len=max_len_bytes)


def _bytes_needed(shape: Tuple[int, ...], itemsize: int, max_len_bytes: int) -> int:
    n = 1
    for d in shape:
        if d < 0:
            raise ValueError('negative dimension in shape')
        n *= d
        if n > (max_len_bytes // max(1, itemsize)):
            raise ValueError('shape implies more bytes than max_len_bytes')
    return n * itemsize


def recv_ndarray(sock: socket.socket, *, copy: bool = False, max_len_bytes: int = 2**31 - 1):
    if np is None:
        raise RuntimeError('numpy is not available')

    hdr = _recv_header(sock)
    if hdr.get('type') != 'ndarray':
        raise ValueError(f'unexpected type {hdr.get("type")} (expected ndarray)')

    dtype = np.dtype(hdr['dtype'])
    shape = tuple(int(x) for x in hdr['shape'])
    order = hdr.get('order', 'C')

    expected = _bytes_needed(shape, int(dtype.itemsize), max_len_bytes)
    raw = recv_msg(sock, max_len=max_len_bytes)
    if len(raw) != expected:
        raise ValueError(f'byte count mismatch: expected {expected}, got {len(raw)}')

    arr = np.frombuffer(raw, dtype=dtype, count=expected // dtype.itemsize).reshape(shape, order=order)
    if copy:
        arr = arr.copy(order=order)
    return arr


def send_pickle(sock: socket.socket, obj: Any) -> None:
    import pickle
    _send_header(sock, {'type': 'pickle'})
    send_msg(sock, pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))


def recv_pickle(sock: socket.socket) -> Any:
    import pickle
    hdr = _recv_header(sock)
    if hdr.get('type') != 'pickle':
        raise ValueError(f'unexpected type {hdr.get("type")} (expected pickle)')
    return pickle.loads(recv_msg(sock))


# Unified handlers

def send_any(sock: socket.socket, obj: Any, *, allow_pickle: bool = False) -> None:
    if isinstance(obj, (bytes, bytearray, memoryview)):
        send_bytes(sock, obj)
    elif isinstance(obj, str):
        send_text(sock, obj)
    elif isinstance(obj, np.ndarray):
        send_ndarray(sock, obj)
    elif isinstance(obj, (dict, list, tuple, int, float, bool)) or obj is None:
        # JSON-safe; tuples become lists on the other end
        send_json(sock, obj)
    elif allow_pickle:
        send_pickle(sock, obj)
    else:
        raise TypeError('unsupported type for send_any; pass allow_pickle=True to pickle arbitrary objects')


def recv_any(sock: socket.socket, *, allow_pickle: bool = False) -> Any:
    # Get header message first
    hdr = _recv_header(sock)
    t = hdr.get('type')

    if t == 'bytes':
        return recv_msg(sock)

    if t == 'text':
        enc = hdr.get('encoding', 'utf-8')
        return recv_msg(sock).decode(enc)

    if t == 'json':
        return json.loads(recv_msg(sock).decode('utf-8'))

    if t == 'ndarray':
        dtype = np.dtype(hdr['dtype'])
        shape = tuple(int(x) for x in hdr['shape'])
        order = hdr.get('order', 'C')
        expected = _bytes_needed(shape, int(dtype.itemsize), 2**31 - 1)
        raw = recv_msg(sock, max_len=2**31 - 1)
        if len(raw) != expected:
            raise ValueError(f'byte count mismatch: expected {expected}, got {len(raw)}')
        arr = np.frombuffer(raw, dtype=dtype, count=expected // dtype.itemsize).reshape(shape, order=order)
        return arr

    if t == 'pickle' and allow_pickle:
        import pickle
        return pickle.loads(recv_msg(sock))

    raise ValueError(f'unsupported or disallowed type: {t}')
