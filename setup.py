from setuptools import setup

setup(
	name = 'intouchclient',
	version = '0.1.0',
	description = 'Python client for connecting to Lan2RF gateway',
	url = 'https://github.com/zxdavb/evohome-client/',
	download_url = 'https://github.com/zxdavb/intouch-client/tarball/0.2.8',
	author = 'David Bonnes',
	author_email = 'evohome@andrew-stock.com',
	license = 'Apache 2',
	classifiers = [
		'Development Status :: 3 - Alpha',
	],
	keywords = ['intouch'],
	packages = ['intouchclient'],
	install_requires = ['aiohttp']
)