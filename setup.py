import setuptools

options = {
	"name": "webwombat",
	"version": "0.0.2",
	"scripts": [],
    "entry_points": {'console_scripts': ['wombat=webwombat.__main__:main']},
	"author": "Cole Wilson",
	"author_email": "me@cole.ws",
	"description": "lightweight proxy server with extreme configuration options",
	"long_description": "# webwombat\n[View on GitHub](https://github.com/cole-wilson/webwombat)",
	"long_description_content_type": "text/markdown",
	"url": "https://github.com/cole-wilson/webwombat",
	"packages": setuptools.find_packages(),
	"install_requires": ['requests', 'setuptools', 'lark', 'blessed', 'cryptography', 'brotli', 'websockets'],
	"classifiers": ["Programming Language :: Python :: 3"],
	"python_requires": '>=3.6',
	"package_data": {"": ['*.cube', '*.lark', '*.html', '*.js'], },
	"license": "MIT",
	"keywords": '',
	"setup_requires": ['wheel'],
}

custom_options = {}

if __name__ == "__main__":
	setuptools.setup(**custom_options, **options)
