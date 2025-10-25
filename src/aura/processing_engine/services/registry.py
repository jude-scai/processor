"""
Processor Registry

A class-based registry that maps processor names to their class implementations.
This provides a centralized way to register and retrieve processor classes.
"""

import importlib
import inspect
from pathlib import Path
from typing import Type, Dict
from ..base_processor import BaseProcessor


class Registry:
    """
    A singleton registry for processor classes.

    This allows processor classes to be registered once and then
    retrieved by name throughout the application, decoupling
    processor implementations from the orchestration logic.
    """

    _instance = None
    _registry: Dict[str, Type[BaseProcessor]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Registry, cls).__new__(cls)
            cls._instance._registry = {}
        return cls._instance

    def register_processor(self, processor_class: Type[BaseProcessor]) -> None:
        """
        Register a processor class with its defined PROCESSOR_NAME.

        Args:
            processor_class: Processor class to register

        Raises:
            ValueError: If processor class doesn't define PROCESSOR_NAME
        """
        if (
            not hasattr(processor_class, "PROCESSOR_NAME")
            or not processor_class.PROCESSOR_NAME
        ):
            raise ValueError(
                f"Processor class {processor_class.__name__} must define a PROCESSOR_NAME."
            )

        processor_name = processor_class.PROCESSOR_NAME
        if processor_name in self._registry:
            print(
                f"⚠️  Warning: Processor '{processor_name}' is already registered. Overwriting."
            )

        self._registry[processor_name] = processor_class
        print(f"✅ Registered processor: {processor_name}")

    def get_processor(self, processor_name: str) -> Type[BaseProcessor]:
        """
        Retrieve a registered processor class by its name.

        Args:
            processor_name: Name of the processor to retrieve

        Returns:
            Processor class

        Raises:
            ValueError: If processor is not registered
        """
        if processor_name not in self._registry:
            raise ValueError(f"Processor '{processor_name}' not found in registry.")
        return self._registry[processor_name]

    def is_processor_registered(self, processor_name: str) -> bool:
        """
        Check if a processor is registered.

        Args:
            processor_name: Name of the processor to check

        Returns:
            True if registered, False otherwise
        """
        return processor_name in self._registry

    def get_registered_processors(self) -> Dict[str, Type[BaseProcessor]]:
        """
        Get all registered processor names and their classes.

        Returns:
            Dictionary mapping processor names to classes
        """
        return self._registry.copy()

    def clear_registry(self) -> None:
        """Clear all registered processors (mainly for testing)."""
        self._registry.clear()


def get_registry() -> Registry:
    """
    Returns the singleton instance of the Registry.
    """
    return Registry()


current_dir = Path(__file__).parent
processors_dir = current_dir.parent / "processors"

if processors_dir.exists():
    for py_file in processors_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        relative_path = py_file.relative_to(processors_dir)
        module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
        full_module_path = f"..processors.{'.'.join(module_parts)}"  # pylint: disable=invalid-name

        try:
            module = importlib.import_module(full_module_path, package=__package__)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    obj != BaseProcessor
                    and issubclass(obj, BaseProcessor)
                    and hasattr(obj, "PROCESSOR_NAME")
                ):

                    get_registry().register_processor(obj)

        except ImportError as e:
            print(f"⚠️  Could not import {full_module_path}: {e}")
        except Exception as e:
            print(f"⚠️  Error processing {full_module_path}: {e}")
else:
    print("⚠️  Processors directory not found")
