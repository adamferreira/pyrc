try:
    import docker
    __DOCKER_AVAILABLE__ = True
except:
    __DOCKER_AVAILABLE__ = False