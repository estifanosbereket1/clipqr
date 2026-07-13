import socket

CANDIDATE_PORTS = [8421, 8733, 9142, 9387, 7654, 6789, 8901, 7321]


def is_port_available(port: int) -> bool:
    """
    Attempts to bind a socket to the given port on all interfaces, the same
    way uvicorn will when the app actually starts. If binding succeeds, the
    port is free; we immediately release it since we're only testing, not
    actually claiming it yet.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def get_available_ports(limit: int = 4) -> list[int]:
    """
    Checks the curated candidate list and returns up to `limit` ports
    confirmed available right now.
    """
    available = []
    for port in CANDIDATE_PORTS:
        if is_port_available(port):
            available.append(port)
        if len(available) >= limit:
            break
    return available


def _standalone_test():
    print("Checking candidate ports...")
    for port in CANDIDATE_PORTS:
        status = "available" if is_port_available(port) else "in use"
        print(f"  {port}: {status}")

    print("\nTop available picks:", get_available_ports())


if __name__ == "__main__":
    _standalone_test()
