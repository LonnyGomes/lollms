######
# Project       : lollms
# File          : binding.py
# Author        : ParisNeo with the help of the community
# license       : Apache 2.0
# Description   : 
# This is an interface class for lollms bindings.
######
from typing import Dict, Any
from pathlib import Path
from typing import Callable
from lollms.paths import LollmsPaths
from ascii_colors import ASCIIColors

import tempfile
import requests
import shutil
import os
import yaml
import importlib
import subprocess
from lollms.config import TypedConfig, InstallOption
from lollms.main_config import LOLLMSConfig
import urllib
import inspect
from enum import Enum

__author__ = "parisneo"
__github__ = "https://github.com/ParisNeo/lollms_bindings_zoo"
__copyright__ = "Copyright 2023, "
__license__ = "Apache 2.0"
class BindingType(Enum):
    """Binding types."""
    
    TEXT_ONLY = 0
    """This binding only supports text."""
    
    TEXT_IMAGE = 1
    """This binding supports text and image."""

    TEXT_IMAGE_VIDEO = 2
    """This binding supports text, image and video."""

    TEXT_AUDIO = 3
    """This binding supports text and audio."""

class LLMBinding:
    
    def __init__(
                    self,
                    binding_dir:Path,
                    lollms_paths:LollmsPaths,
                    config:LOLLMSConfig, 
                    binding_config:TypedConfig,
                    installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY,
                    supported_file_extensions='*.bin',
                    binding_type:BindingType=BindingType.TEXT_ONLY,
                    models_dir_names:list=None,
                    notification_callback:Callable=None
                ) -> None:
        
        self.binding_type           = binding_type

        self.binding_dir            = binding_dir
        self.binding_folder_name    = binding_dir.stem
        self.lollms_paths           = lollms_paths
        self.config                 = config
        self.binding_config         = binding_config

        self.supported_file_extensions         = supported_file_extensions
        self.seed                   = config["seed"]
        self.notification_callback  = notification_callback

        self.configuration_file_path = lollms_paths.personal_configuration_path/"bindings"/self.binding_folder_name/f"config.yaml"
        self.configuration_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.binding_config.config.file_path = self.configuration_file_path

        # Installation
        if (not self.configuration_file_path.exists() or installation_option==InstallOption.FORCE_INSTALL) and installation_option!=InstallOption.NEVER_INSTALL:
            self.install()
            self.binding_config.config.save_config()
        else:
            self.load_binding_config()

        if models_dir_names is not None:
            config.lollms_paths.binding_models_paths=[config.lollms_paths.personal_models_path / models_dir_name for models_dir_name in models_dir_names]
            self.models_folders = config.lollms_paths.binding_models_paths
            self.models_dir_names = models_dir_names
        else:
            config.lollms_paths.binding_models_paths= [config.lollms_paths.personal_models_path / self.binding_folder_name]
            self.models_folders = config.lollms_paths.binding_models_paths
            self.models_dir_names = [self.binding_folder_name]
        for models_folder in self.models_folders:
            models_folder.mkdir(parents=True, exist_ok=True)

    def notify(self, content:str, status:bool=True):
        if self.notification_callback:
            self.notification_callback(content, status)


    def settings_updated(self):
        """
        To be implemented by the bindings
        """
        pass

    def handle_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle client requests.

        Args:
            data (dict): A dictionary containing the request data.

        Returns:
            dict: A dictionary containing the response, including at least a "status" key.

        This method should be implemented by a class that inherits from this one.

        Example usage:
        ```
        handler = YourHandlerClass()
        request_data = {"command": "some_command", "parameters": {...}}
        response = handler.handle_request(request_data)
        ```
        """        
        return {"status":True}

    def print_class_attributes(self, cls, show_layers=False):
        for attr in cls.__dict__:
            if isinstance(attr, property) or isinstance(attr, type):
                continue
            value = getattr(cls, attr)
            if attr!="tensor_file_map": 
                ASCIIColors.red(f"{attr}: ",end="")
                ASCIIColors.yellow(f"{value}")
            elif show_layers:
                ASCIIColors.red(f"{attr}: ")
                for k in value.keys():
                    ASCIIColors.yellow(f"{k}")
                
    def get_parameter_info(self, cls):
        # Get the signature of the class
        sig = inspect.signature(cls)
        
        # Print each parameter name and value
        for name, param in sig.parameters.items():
            if param.default is not None:
                print(f"{name}: {param.default}")
            else:
                print(f"{name}: Not specified")

    def __str__(self) -> str:
        return self.config["binding_name"]+f"({self.config['model_name']})"
    
    def download_and_install_wheel(self, url):
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        try:
            # Download the wheel file
            response = requests.get(url)
            if response.status_code == 200:
                # Save the downloaded file to the temporary directory
                wheel_path = os.path.join(temp_dir, 'package.whl')
                with open(wheel_path, 'wb') as file:
                    file.write(response.content)

                # Install the wheel file using pip
                subprocess.check_call(['pip', 'install', wheel_path])

                # Clean up the temporary directory
                shutil.rmtree(temp_dir)
                print('Installation completed successfully.')
            else:
                print('Failed to download the file.')

        except Exception as e:
            print('An error occurred during installation:', str(e))
            shutil.rmtree(temp_dir)

    def get_file_size(self, url):
        # Send a HEAD request to retrieve file metadata
        response = urllib.request.urlopen(url)
        
        # Extract the Content-Length header value
        file_size = response.headers.get('Content-Length')
        
        # Convert the file size to integer
        if file_size:
            file_size = int(file_size)
        
        return file_size
    
    def build_model(self):
        """
        Build the model.

        This method is responsible for constructing the model for the LOLLMS class.

        Returns:
            the model
        """        
        return None
    
    def destroy_model(self):
        """
        destroys the current model
        """
        pass

    def install(self):
        """
        Installation procedure (to be implemented)
        """
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
        ASCIIColors.red(f"Installing {self.binding_folder_name}")
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

    def uninstall(self):
        """
        UnInstallation procedure (to be implemented)
        """
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
        ASCIIColors.red(f"UnInstalling {self.binding_folder_name}")
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

    def searchModelParentFolder(self, model_name:str, model_type=None):
        model_path=None
        if model_type is not None:
            for mn in self.models_folders:
                if mn.name.lower() == model_type.lower():
                    return mn
        for mn in self.models_folders:
            if mn.name in model_name.lower():
                model_path = mn
                break
        if model_path is None:
            model_path = self.models_folders[0]
        return model_path


    def searchModelPath(self, model_name:str):
        model_path=None
        for mn in self.models_folders:
            if mn.name in model_name.lower():
                if mn.name == "ggml":
                    try:
                        idx = model_name.index("-GGML")
                        models=[m for m in mn.iterdir() if model_name[:idx].lower() in m.name.lower()]
                        model_path = mn/models[0].name
                    except:
                        model_path = mn/model_name
                elif mn.name == "gguf":
                    try:
                        idx = model_name.index("-GGUF")
                        models=[m for m in mn.iterdir() if model_name[:idx].lower() in m.name.lower()]
                        model_path = mn/models[0].name
                    except:
                        model_path = mn/model_name
                else:
                    model_path = mn/model_name
                break
        if model_path is None:
            model_path = self.models_folders[0]/model_name
        return model_path
    
    def get_model_path(self):
        """
        Retrieves the path of the model based on the configuration.

        If the model name ends with ".reference", it reads the model path from a file.
        Otherwise, it constructs the model path based on the configuration.

        Returns:
            str: The path of the model.
        """
        if self.config.model_name is None:
            return None
        
        if self.config.model_name.endswith(".reference"):
            ASCIIColors.yellow("Loading a reference model:")
            ref_path = self.searchModelPath(self.config.model_name)
            if ref_path.exists():
                with open(str(ref_path), 'r') as f:
                    model_path = Path(f.read())
                ASCIIColors.yellow(model_path)
            else:
                return None
        else:
            model_path = self.searchModelPath(self.config.model_name)

        return model_path

    
    def get_current_seed(self):
        return self.seed
    
    def load_binding_config(self):
        """
        Load the content of local_config.yaml file.

        The function reads the content of the local_config.yaml file and returns it as a Python dictionary.

        Args:
            None

        Returns:
            dict: A dictionary containing the loaded data from the local_config.yaml file.
        """
        try:
            self.binding_config.config.load_config()
        except:
            self.binding_config.config.save_config()
        self.binding_config.sync()

    def save_config_file(self, path):
        """
        Load the content of local_config.yaml file.

        The function reads the content of the local_config.yaml file and returns it as a Python dictionary.

        Args:
            None

        Returns:
            dict: A dictionary containing the loaded data from the local_config.yaml file.
        """     
        self.binding_config.config.save_config(self.configuration_file_path)

    def generate_with_images(self, 
                 prompt:str,
                 images:list=[],
                 n_predict: int = 128,
                 callback: Callable[[str, int, dict], bool] = None,
                 verbose: bool = False,
                 **gpt_params ):
        """Generates text out of a prompt and a bunch of images
        This should be implemented by child class

        Args:
            prompt (str): The prompt to use for generation
            images(list): A list of images to interpret
            n_predict (int, optional): Number of tokens to prodict. Defaults to 128.
            callback (Callable[[str, int, dict], None], optional): A callback function that is called everytime a new text element is generated. Defaults to None.
            verbose (bool, optional): If true, the code will spit many informations about the generation process. Defaults to False.
        """
        pass
    


    def generate(self, 
                 prompt:str,
                 n_predict: int = 128,
                 callback: Callable[[str, int, dict], bool] = None,
                 verbose: bool = False,
                 **gpt_params ):
        """Generates text out of a prompt
        This should be implemented by child class

        Args:
            prompt (str): The prompt to use for generation
            n_predict (int, optional): Number of tokens to prodict. Defaults to 128.
            callback (Callable[[str, int, dict], None], optional): A callback function that is called everytime a new text element is generated. Defaults to None.
            verbose (bool, optional): If true, the code will spit many informations about the generation process. Defaults to False.
        """
        pass
    def tokenize(self, prompt:str):
        """
        Tokenizes the given prompt using the model's tokenizer.

        Args:
            prompt (str): The input prompt to be tokenized.

        Returns:
            list: A list of tokens representing the tokenized prompt.
        """
        return prompt.split(" ")

    def detokenize(self, tokens_list:list):
        """
        Detokenizes the given list of tokens using the model's tokenizer.

        Args:
            tokens_list (list): A list of tokens to be detokenized.

        Returns:
            str: The detokenized text as a string.
        """
        return " ".join(tokens_list)


    def embed(self, text):
        """
        Computes text embedding
        Args:
            text (str): The text to be embedded.
        Returns:
            List[float]
        """
        pass


    def list_models(self, config:dict):
        """Lists the models for this binding
        """
        models = []
        for models_folder in self.models_folders:
            if models_folder.name in ["ggml","gguf"]:
                models+=[f.name for f in models_folder.iterdir() if f.suffix in self.supported_file_extensions or f.suffix==".reference"]
            else:
                models+=[f.name for f in models_folder.iterdir() if f.is_dir() and not f.stem.startswith(".") or f.suffix==".reference"]
        return models
    

    def get_available_models(self):
        # Create the file path relative to the child class's directory
        full_data = []
        for models_dir_name in self.models_dir_names:
            file_path = self.lollms_paths.models_zoo_path/f"{models_dir_name}.yaml"
            with open(file_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
                full_data+=yaml_data
        
        return full_data
           

    @staticmethod
    def vram_usage():
        try:
            output = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.total,memory.used,gpu_name', '--format=csv,nounits,noheader'])
            lines = output.decode().strip().split('\n')
            vram_info = [line.split(',') for line in lines]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
            "nb_gpus": 0
            }
        
        ram_usage = {
            "nb_gpus": len(vram_info)
        }
        
        if vram_info is not None:
            for i, gpu in enumerate(vram_info):
                ram_usage[f"gpu_{i}_total_vram"] = int(gpu[0])*1024*1024
                ram_usage[f"gpu_{i}_used_vram"] = int(gpu[1])*1024*1024
                ram_usage[f"gpu_{i}_model"] = gpu[2].strip()
        else:
            # Set all VRAM-related entries to None
            ram_usage["gpu_0_total_vram"] = None
            ram_usage["gpu_0_used_vram"] = None
            ram_usage["gpu_0_model"] = None
        
        return ram_usage

    @staticmethod
    def clear_cuda():
        import torch
        ASCIIColors.red("*-*-*-*-*-*-*-*")
        ASCIIColors.red("Cuda VRAM usage")
        ASCIIColors.red("*-*-*-*-*-*-*-*")
        print(LLMBinding.vram_usage())
        try:
            torch.cuda.empty_cache()
        except Exception as ex:
            ASCIIColors.error("Couldn't clear cuda memory")
        ASCIIColors.red("Cleared cache")
        ASCIIColors.red("*-*-*-*-*-*-*-*")
        ASCIIColors.red("Cuda VRAM usage")
        ASCIIColors.red("*-*-*-*-*-*-*-*")
        print(LLMBinding.vram_usage())


# ===============================

class BindingBuilder:
    def build_binding(
                        self, 
                        config: LOLLMSConfig, 
                        lollms_paths:LollmsPaths,
                        installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY,
                        notification_callback:Callable=None
                    )->LLMBinding:

        binding:LLMBinding = self.getBinding(config, lollms_paths, installation_option)
        return binding(
                config,
                lollms_paths=lollms_paths,
                installation_option = installation_option,
                notification_callback=notification_callback
                )
    
    def getBinding(
                        self, 
                        config: LOLLMSConfig, 
                        lollms_paths:LollmsPaths,
                        installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY
                    )->LLMBinding:
        
        if len(str(config.binding_name).split("/"))>1:
            binding_path = Path(config.binding_name)
        else:
            binding_path = lollms_paths.bindings_zoo_path / config["binding_name"]

        # define the full absolute path to the module
        absolute_path = binding_path.resolve()
        # infer the module name from the file path
        module_name = binding_path.stem
        # use importlib to load the module from the file path
        loader = importlib.machinery.SourceFileLoader(module_name, str(absolute_path / "__init__.py"))
        binding_module = loader.load_module()
        binding:LLMBinding = getattr(binding_module, binding_module.binding_name)
        return binding
    
class ModelBuilder:
    def __init__(self, binding:LLMBinding):
        self.binding = binding
        self.model = None
        self.build_model() 

    def build_model(self):
        self.model = self.binding.build_model()

    def get_model(self):
        return self.model

