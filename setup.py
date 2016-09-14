import io
from setuptools import setup

with io.open('README.md', encoding='utf-8') as f:
    README = f.read()

setup(
    name='starpicker',
    version='0.5.0',
    url='https://github.com/skypicker/starpicker',
    author='Bence Nagy',
    author_email='bence@skypicker.com',
    download_url='https://github.com/skypicker/starpicker/releases',
    description='A tool that periodically checks sites for feedback about an entity and posts the findings to Slack',
    long_description=README,
    packages=['starpicker'],
    install_requires=[
        'beautifulsoup4<5',
        'redis<3',
        'requests<3',
        'textblob<0.10',
    ],
    entry_points={'console_scripts': 'starpicker=starpicker.run:main'},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ]
)
