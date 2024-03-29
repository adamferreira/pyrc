try:
    import docker
    __DOCKER_AVAILABLE__ = True
except:
    __DOCKER_AVAILABLE__ = False

def docker_available() -> bool:
    return __DOCKER_AVAILABLE__

def docker_client():
    if __DOCKER_AVAILABLE__:
        return docker.from_env()
    return None