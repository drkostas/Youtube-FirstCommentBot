# Makefile for the youbot module
.ONESHELL:
SHELL=/bin/bash
PYTHON_VERSION=3.8
ENV_NAME="youbot"

# You can use either venv (venv) or conda env
# by specifying the correct argument (env=<conda, venv>)
ifeq ($(env),venv)
	# Use Venv
	BASE=venv
	BIN=$(BASE)/bin
	CREATE_COMMAND="python$(PYTHON_VERSION) -m venv $(BASE)"
	DELETE_COMMAND="rm -rf $(BASE)"
	ACTIVATE_COMMAND="source venv/bin/activate"
	DEACTIVATE_COMMAND="deactivate"
else
	# Use Conda
	BASE=~/anaconda3/envs/$(ENV_NAME)
	BIN=$(BASE)/bin
	CREATE_COMMAND="conda create --prefix $(BASE) python=$(PYTHON_VERSION) -y"
	DELETE_COMMAND="conda env remove -p $(BASE)"
	ACTIVATE_COMMAND="conda activate -p $(BASE)"
	DEACTIVATE_COMMAND="conda deactivate"
endif

# To load a env file use env_file=<path to env file>
# e.g. make release env_file=.env
ifneq ($(env_file),)
	include $(env_file)
#	export
endif

all:
	$(MAKE) help
help:
	@echo
	@echo "-----------------------------------------------------------------------------------------------------------"
	@echo "                                              DISPLAYING HELP                                              "
	@echo "-----------------------------------------------------------------------------------------------------------"
	@echo "Use make <make recipe> [server=<prod|circleci|local>] to specify the server"
	@echo "Prod, and local are using conda env, circleci uses virtualenv. Default: local"
	@echo
	@echo "make help"
	@echo "       Display this message"
	@echo "make install [env=<conda|venv>] [env_file=<path to env file>]"
	@echo "       Call clean delete_conda_env create_conda_env setup run_tests"
	@echo "make clean [env=<conda|venv>] [env_file=<path to env file>]"
	@echo "       Delete all './build ./dist ./*.pyc ./*.tgz ./*.egg-info' files"
	@echo "make delete_env [env=<conda|venv>] [env_file=<path to env file>]"
	@echo "       Delete the current conda env or virtualenv"
	@echo "make create_env [env=<conda|venv>] [env_file=<path to env file>]"
	@echo "       Create a new conda env or virtualenv for the specified python version"
	@echo "make requirements [env=<conda|venv>] [env_file=<path to env file>]"
	@echo "       Install the requirements from the requirements.txt"
	@echo "make setup [env=<conda|venv>] [env_file=<path to env file>]"
	@echo "       Call setup.py install"
	@echo "make run_tests [env=<conda|venv>] [env_file=<path to env file>]"
	@echo "       Run all the tests from the specified folder"
	@echo "-----------------------------------------------------------------------------------------------------------"
install:
	$(MAKE) clean
	$(MAKE) delete_env
	$(MAKE) create_env
	$(MAKE) requirements
	$(MAKE) setup
	$(MAKE) run_tests
	@echo -e "\033[0;31m############################################"
	@echo
	@echo "Installation Successful!"
	@echo "To activate the conda environment run:"
	@echo '    conda activate youbot'
clean:
	$(PYTHON_BIN)python setup.py clean
delete_env:
	@echo "Deleting virtual environment.."
	eval $(DELETE_COMMAND)
create_env:
	@echo "Creating virtual environment.."
	eval $(CREATE_COMMAND)
requirements:
	pip install -r requirements.txt
setup:
	$(BIN)/pip install setuptools
	$(BIN)/python setup.py install $(SETUP_FLAG)
run_tests:
	$(BIN)/python setup.py test $(SETUP_FLAG)


.PHONY: help install clean delete_env create_env requirements setup run_tests