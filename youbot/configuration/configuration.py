import os
from typing import Dict, List, Tuple, Union
import json
import _io
from io import StringIO, TextIOWrapper
import re
import yaml
from jsonschema import validate as validate_json_schema

from youbot import ColorizedLogger

logger = ColorizedLogger('Config', 'white')


class Configuration:
    __slots__ = ('config', 'config_path', 'config_keys', 'tag')

    config: Dict
    config_path: str
    tag: str
    config_keys: List
    env_variable_tag: str = '!ENV'
    env_variable_pattern: str = r'.*?\${(\w+)}.*?'  # ${var}

    def __init__(self, config_src: Union[TextIOWrapper, StringIO, str],
                 config_schema_path: str = 'yml_schema.json'):
        """
       The basic constructor. Creates a new instance of the Configuration class.

        Args:
            config_src: The path, file or StringIO object of the configuration to load
            config_schema_path: The path, file or StringIO object of the configuration validation file
        """

        # Load the predefined schema of the configuration
        configuration_schema = self.load_configuration_schema(config_schema_path=config_schema_path)
        # Load the configuration
        self.config, self.config_path = self.load_yml(config_src=config_src,
                                                      env_tag=self.env_variable_tag,
                                                      env_pattern=self.env_variable_pattern)
        # Validate the config
        validate_json_schema(self.config, configuration_schema)
        logger.debug("Schema Validation was Successful.")
        # Set the config properties as instance attributes
        self.tag = self.config['tag']
        self.config_keys = [key for key in self.config.keys() if key != 'tag']
        logger.info(f"Configuration file loaded successfully from path: {self.config_path}")
        logger.info(f"Configuration Tag: {self.tag}")

    @staticmethod
    def load_configuration_schema(config_schema_path: str) -> Dict:
        """
        Loads the configuration schema file

        Args:
            config_schema_path: The path of the config schema

        Returns:
            configuration_schema: The loaded config schema
        """

        if config_schema_path[0] != os.sep:
            config_schema_path = '/'.join(
                [os.path.dirname(os.path.realpath(__file__)), config_schema_path])
        with open(config_schema_path) as f:
            configuration_schema = json.load(f)
        return configuration_schema

    @staticmethod
    def load_yml(config_src: Union[TextIOWrapper, StringIO, str], env_tag: str, env_pattern: str) -> \
    Tuple[Dict, str]:
        """
        Loads the configuration file
        Args:
            config_src: The path of the configuration
            env_tag: The tag that distinguishes the env variables
            env_pattern: The regex for finding the env variables

        Returns:
            config, config_path
        """
        pattern = re.compile(env_pattern)
        loader = yaml.SafeLoader
        loader.add_implicit_resolver(env_tag, pattern, None)

        def constructor_env_variables(loader, node):
            """
            Extracts the environment variable from the node's value
            :param yaml.Loader loader: the yaml loader
            :param node: the current node in the yaml
            :return: the parsed string that contains the value of the environment
            variable
            """
            value = loader.construct_scalar(node)
            match = pattern.findall(value)  # to find all env variables in line
            if match:
                full_value = value
                for g in match:
                    full_value = full_value.replace(
                        f'${{{g}}}', os.environ.get(g, g)
                    )
                return full_value
            return value

        loader.add_constructor(env_tag, constructor_env_variables)

        if isinstance(config_src, TextIOWrapper):
            logger.debug("Loading yaml from TextIOWrapper")
            config = yaml.load(config_src, Loader=loader)
            config_path = os.path.abspath(config_src.name)
        elif isinstance(config_src, StringIO):
            logger.debug("Loading yaml from StringIO")
            config = yaml.load(config_src, Loader=loader)
            config_path = "StringIO"
        elif isinstance(config_src, str):
            config_path = os.path.abspath(config_src)
            logger.debug("Loading yaml from path")
            with open(config_path) as f:
                config = yaml.load(f, Loader=loader)
        else:
            raise TypeError('Config file must be TextIOWrapper or path to a file')
        return config, config_path

    def get_config(self, config_name) -> List:
        """
        Returns the subconfig requested

        Args:
            config_name: The name of the subconfig

        Returns:
            sub_config: The sub_configs List
        """

        if config_name in self.config.keys():
            return self.config[config_name]
        else:
            raise ConfigurationError('Config property %s not set!' % config_name)

    def to_yml(self, fn: Union[str, _io.TextIOWrapper]) -> None:
        """
        Writes the configuration to a stream. For example a file.

        Args:
            fn:

        Returns:
        """

        self.config['tag'] = self.tag
        if isinstance(fn, str):
            with open(fn, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
        elif isinstance(fn, _io.TextIOWrapper):
            yaml.dump(self.config, fn, default_flow_style=False)
        else:
            raise TypeError('Expected str or _io.TextIOWrapper not %s' % (type(fn)))

    to_yaml = to_yml

    def to_json(self) -> Dict:
        """
        Returns the whole config file

        Returns:

        """
        return self.config

    # def __getitem__(self, item):
    #     return self.get_config(item)


class ConfigurationError(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
