import setuptools

options = {
	"name": "webwombat",
	"version": "0.0.1",
	"scripts": [],
    "entry_points": {'console_scripts': ['wombat=webwombat.__main__:main']},
	"author": "Cole Wilson",
	"author_email": "me@cole.ws",
	"description": "desc...",
	"long_description": "desc...",
	"long_description_content_type": "text/markdown",
	"url": "https://github.com/cole-wilson/webwombat",
	"packages": setuptools.find_packages(),
	"install_requires": ['requests', 'setuptools', 'lark', 'blessed', 'cryptography', 'brotli'],
	"classifiers": ["Programming Language :: Python :: 3"],
	"python_requires": '>=3.6',
	"package_data": {"": ['*.cube', '*.lark', '*.html'], },
	"license": "MIT",
	"keywords": '',
	"setup_requires": ['wheel'],
}

custom_options = {}

if __name__ == "__main__":
	setuptools.setup(**custom_options, **options)
