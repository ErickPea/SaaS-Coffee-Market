"""
conftest.py — configuración compartida de pytest.

Incluye un shim MÍNIMO y temporal de `pydantic_settings`, activo SOLO si el
paquete real no está instalado. Se usó para poder ejecutar
tests/providers/*.py con mocks durante el desarrollo, en un sandbox sin
acceso a red para instalar dependencias. En cuanto instales
requirements.txt normalmente, este shim queda inerte (se detecta el
paquete real y no se toca sys.modules) — no afecta producción ni el
comportamiento real de Settings.
"""
import os
import sys
import types

try:
    import pydantic_settings  # noqa: F401
    _HAS_REAL_PYDANTIC_SETTINGS = True
except ImportError:
    _HAS_REAL_PYDANTIC_SETTINGS = False

if not _HAS_REAL_PYDANTIC_SETTINGS:
    shim = types.ModuleType("pydantic_settings")

    def SettingsConfigDict(**kwargs):
        return dict(kwargs)

    class BaseSettings:
        """Shim mínimo: toma los defaults anotados en la clase y les aplica
        overrides desde variables de entorno (MAYUSCULAS), sin la
        validación de tipos real de Pydantic. Suficiente para instanciar
        `Settings` en pruebas de providers; NO se usa en la app real."""

        def __init__(self, **overrides):
            annotations: dict = {}
            for klass in reversed(type(self).__mro__):
                annotations.update(getattr(klass, "__annotations__", {}))
            for name in annotations:
                default = getattr(type(self), name, None)
                env_value = os.environ.get(name.upper())
                value = overrides.get(name, env_value if env_value is not None else default)
                setattr(self, name, value)

    shim.BaseSettings = BaseSettings
    shim.SettingsConfigDict = SettingsConfigDict
    sys.modules["pydantic_settings"] = shim
    print("\n[conftest] pydantic_settings no está instalado: usando shim mínimo solo para pruebas.", file=sys.stderr)
