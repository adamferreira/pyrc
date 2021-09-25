import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyrc",
    version="0.0.1",
    author="Adam Ferreira",
    author_email="adam.ferreira.dc@gmail.com",
    description="Python Remote Computing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/adamferreira/pyrc",
    project_urls={},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"pyrc": "pyrc"},
    packages = ["pyrc", "pyrc.remote", "pyrc.system", "pyrc.event"],
    test_suite="pyrc.tests",
    #packages=setuptools.find_packages(where="pyrc"),
    python_requires=">=3.0",
    install_requires=[
       "paramiko",
       "scp",
       "rich"
   ],
)
