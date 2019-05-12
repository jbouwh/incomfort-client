import setuptools

VERSION = "0.2.9"

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="incomfort-client",
    version=VERSION,
    author="David Bonnes",
    author_email="zxdavb@gmail.com",
    description="A aiohttp-based client for Intergas InComfort/InTouch Lan2RF systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zxdavb/incomfort-client",
    download_url = 'https://github.com/zxdavb/incomfort-client/archive/VERSION.tar.gz',
    packages=setuptools.find_packages(),
    keywords=['intergas', 'incomfort', 'intouch', 'lan2rf'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ],
)
