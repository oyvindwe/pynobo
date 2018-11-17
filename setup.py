import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nobo",
    version="0.0.1",
    author="Echo Romeo",
    author_email="post@undereksponert.no",
    description="Python 3 socket interface for Nobø Hub / Nobø Energy Control",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/echoromeo/pynobo",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPLv3",
        "Operating System :: OS Independent",
    ],
)