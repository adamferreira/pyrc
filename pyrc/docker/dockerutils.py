try:
    import docker
    __DOCKER_AVAILABLE__ = True
except:
    __DOCKER_AVAILABLE__ = False

def docker_client():
    if __DOCKER_AVAILABLE__:
        return docker.from_env()
    return None