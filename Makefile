# Makefile for the youbot module

SHELL=/bin/bash
PYTHON_VERSION=3.8

# You can use either venv (virtualenv) or conda env by specifying the correct argument (server=<prod, circleci, local>)
ifeq ($(server),prod)
	# Use Conda
	BASE=~/anaconda3/envs/youbot
	BIN=$(BASE)/bin
	CLEAN_COMMAND="conda env remove -p $(BASE)"
	CREATE_COMMAND="conda create --prefix $(BASE) python=$(PYTHON_VERSION) -y"
	SETUP_FLAG=
	DEBUG=False
else ifeq ($(server),circleci)
	# Use Venv
	BASE=venv
	BIN=$(BASE)/bin
	CLEAN_COMMAND="rm -rf $(BASE)"
	CREATE_COMMAND="python$(PYTHON_VERSION) -m venv $(BASE)"
	SETUP_FLAG=
	DEBUG=True
else ifeq ($(server),local)
	# Use Conda
	BASE=~/anaconda3/envs/youbot
	BIN=$(BASE)/bin
	CLEAN_COMMAND="conda env remove -p $(BASE)"
	CREATE_COMMAND="conda create --prefix $(BASE) python=$(PYTHON_VERSION) -y"
#	SETUP_FLAG='--local' # If you want to use this, you change it in setup.py too
	DEBUG=True
else
	# Use Conda
	BASE=~/anaconda3/envs/youbot
	BIN=$(BASE)/bin
	CLEAN_COMMAND="conda env remove -p $(BASE)"
	CREATE_COMMAND="conda create --prefix $(BASE) python=$(PYTHON_VERSION) -y"
#	SETUP_FLAG='--local' # If you want to use this, you change it in setup.py too
	DEBUG=True
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
	@echo "make install [server=<prod|circleci|local>]"
	@echo "       Call clean delete_conda_env create_conda_env setup run_tests"
	@echo "make clean [server=<prod|circleci|local>]"
	@echo "       Delete all './build ./dist ./*.pyc ./*.tgz ./*.egg-info' files"
	@echo "make delete_env [server=<prod|circleci|local>]"
	@echo "       Delete the current conda env or virtualenv"
	@echo "make create_env [server=<prod|circleci|local>]"
	@echo "       Create a new conda env or virtualenv for the specified python version"
	@echo "make setup [server=<prod|circleci|local>]"
	@echo "       Call setup.py install"
	@echo "make run_tests [server=<prod|circleci|local>]"
	@echo "       Run all the tests from the specified folder"
	@echo "-----------------------------------------------------------------------------------------------------------"
install:
	$(MAKE) clean
	$(MAKE) delete_env
	$(MAKE) create_env
	$(MAKE) setup
	$(MAKE) run_tests
	@echo "Installation Successful!"
clean:
	$(PYTHON_BIN)python setup.py clean
delete_env:
	@echo "Deleting virtual environment.."
	eval $(DELETE_COMMAND)
create_env:
	@echo "Creating virtual environment.."
	eval $(CREATE_COMMAND)
run_tests:
	$(BIN)/python setup.py test $(SETUP_FLAG)
setup:
	$(BIN)/python setup.py install $(SETUP_FLAG)


.PHONY: help install clean delete_env create_env setup run_tests