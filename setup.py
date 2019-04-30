import setuptools

VERSION = "0.2.2"

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="intouch-client",
    version=VERSION,
    author="David Bonnes",
    author_email="zxdavb@gmail.com",
    description="A aiohttp-based client for Intergas Intouch Lan2RF systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zxdavb/intouch-client",
    download_url = 'https://github.com/zxdavb/intouch-client/archive/VERSION.tar.gz',
    packages=setuptools.find_packages(),
    keywords = ['intergas', 'intouch', 'lan2rf'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ],
)
