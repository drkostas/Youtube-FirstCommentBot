from setuptools import setup, find_packages, Command
import os


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system("rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info")


# Load Requirements
with open("requirements.txt") as f:
    requirements = f.readlines()

# For the cases you want a different package to be installed on local and prod environments
# import subprocess
# LOCAL_ARG = '--local'
# if LOCAL_ARG in sys.argv:
#     index = sys.argv.index(LOCAL_ARG)  # Index of the local argument
#     sys.argv.pop(index)  # Removes the local argument in order to prevent the setup() error
#     subprocess.check_call([sys.executable, "-m", "pip", "install", 'A package that works locally'])
# else:
#     subprocess.check_call([sys.executable, "-m", "pip", "install", 'A package that works on production'])

# Load README
with open("README.md") as readme_file:
    readme = readme_file.read()


COMMANDS = ["youbot_main = youbot.main:main"]

data_files = []
# data_files = ['youbot/configuration/yml_schema.json']

setup(
    author="drkostas",
    author_email="georgiou.kostas94@gmail.com",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    cmdclass={
        "clean": CleanCommand,
    },
    data_files=[("", data_files)],
    description=(
        "A bot that takes a list of youtube channels and posts the first comment in"
        " every new video."
    ),
    entry_points={"console_scripts": COMMANDS},
    license="MIT license",
    long_description=readme,
    include_package_data=True,
    keywords="youbot",
    name="youbot",
    # package_dir={'': '.'},
    packages=find_packages(include=["youbot", "youbot.*"]),
    # py_modules=['main'],
    test_suite="tests",
    url="https://github.com/drkostas/Youtube-FirstCommentBot",
    version="2.1",
    zip_safe=False,
)
