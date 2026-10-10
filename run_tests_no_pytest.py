"""
Mini-runner temporal, NO parte de la entrega: emula el subconjunto de
pytest que usan los tests de este proyecto (fixtures, pytest.approx,
pytest.raises, clases Test*) para poder ejecutar la suite completa y
obtener un conteo real de aprobados/fallidos en un entorno sin pytest
instalado. Una vez el usuario instale requirements.txt, debe usar `pytest`
real — este script se descarta.
"""
import inspect
import sys
import traceback
import types
from pathlib import Path

# ---------------------------------------------------------------- shim ---
if "pytest" not in sys.modules:
    pytest_shim = types.ModuleType("pytest")

    class Approx:
        def __init__(self, value, rel=1e-6, abs_=1e-12):
            self.value = value
            self.rel = rel
            self.abs_ = abs_

        def __eq__(self, other):
            if self.value == 0:
                return abs(other - self.value) <= max(self.abs_, self.rel)
            return abs(other - self.value) <= max(self.abs_, abs(self.rel * self.value))

        def __repr__(self):
            return f"approx({self.value!r})"

    def approx(value, rel=1e-6, abs=1e-12):  # noqa: A002
        return Approx(value, rel=rel, abs_=abs)

    class RaisesContext:
        def __init__(self, exc_type):
            self.exc_type = exc_type

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                raise AssertionError(f"Se esperaba que lanzara {self.exc_type.__name__}, no lanzó nada")
            return issubclass(exc_type, self.exc_type)

    def raises(exc_type):
        return RaisesContext(exc_type)

    def fixture(func=None, **kwargs):
        def deco(f):
            f._is_fixture = True
            return f
        return deco(func) if func else deco

    pytest_shim.approx = approx
    pytest_shim.raises = raises
    pytest_shim.fixture = fixture

    class _Mark:
        def __getattr__(self, name):
            def deco(*a, **k):
                return lambda f: f
            return deco
    pytest_shim.mark = _Mark()

    sys.modules["pytest"] = pytest_shim


# -------------------------------------------------------------- runner ---
PASSED, FAILED, ERRORS = [], [], []


def _resolve_fixtures(func, module, instance=None):
    """Para funciones decoradas con @patch, el/los mocks los inyecta el
    propio wrapper de unittest.mock (por posición) — no son fixtures de
    pytest y no deben resolverse aquí. Se usa __wrapped__ (que @patch
    preserva) solo para *saber los nombres* de los parámetros reales, pero
    se excluyen tantos de la izquierda como parches activos tenga la
    función, y se llama al wrapper por keyword con el resto.

    Los fixtures se buscan primero en la CLASE (si la función es un método
    de una clase Test*, como en pytest) y si no, a nivel de módulo."""
    real_func = getattr(func, "__wrapped__", func)
    sig = inspect.signature(real_func)
    param_names = [p for p in sig.parameters if p != "self"]

    n_patches = len(getattr(func, "patchings", []))
    fixture_param_names = param_names[n_patches:]

    kwargs = {}
    for name in fixture_param_names:
        fixture_func = None
        if instance is not None:
            candidate = getattr(type(instance), name, None)
            if candidate is not None and getattr(candidate, "_is_fixture", False):
                fixture_func = lambda c=candidate, inst=instance: c(inst)
        if fixture_func is None:
            candidate = getattr(module, name, None)
            if candidate is not None and getattr(candidate, "_is_fixture", False):
                fixture_func = candidate
        if fixture_func is None:
            raise LookupError(f"fixture '{name}' no encontrada en {module.__name__}")
        kwargs[name] = fixture_func()
    return kwargs


def _run_test(qualname, func, module, instance=None):
    try:
        kwargs = _resolve_fixtures(func, module, instance=instance)
        func(**kwargs)
        PASSED.append(qualname)
    except AssertionError as e:
        FAILED.append((qualname, str(e), traceback.format_exc()))
    except Exception as e:  # noqa: BLE001
        ERRORS.append((qualname, f"{type(e).__name__}: {e}", traceback.format_exc()))


def run_module(path: Path):
    import importlib.util

    module_name = f"_dyntest_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    for name, obj in vars(module).items():
        if name.startswith("test_") and inspect.isfunction(obj):
            _run_test(f"{path.name}::{name}", obj, module)
        elif name.startswith("Test") and inspect.isclass(obj):
            instance = obj()
            for meth_name, meth in inspect.getmembers(obj, predicate=inspect.isfunction):
                if meth_name.startswith("test_"):
                    bound = getattr(instance, meth_name)
                    _run_test(f"{path.name}::{name}::{meth_name}", bound, module, instance=instance)


if __name__ == "__main__":
    test_dir = Path(__file__).parent / "tests"

    # Cargar conftest.py primero (activa el shim de pydantic_settings si
    # hace falta), igual que haría pytest automáticamente.
    conftest_path = test_dir / "conftest.py"
    if conftest_path.exists():
        run_module(conftest_path)
        PASSED.clear()  # conftest no tiene tests, pero por si acaso

    files = sorted(p for p in test_dir.glob("test_*.py"))
    # test_api_integration.py necesita fastapi+pytest reales (TestClient,
    # fixtures built-in como tmp_path_factory) — este mini-runner no las
    # replica; se excluye de esta pasada y se reporta aparte.
    excluded = {"test_api_integration.py"}
    files = [f for f in files if f.name not in excluded]
    if excluded:
        print(f"(Excluidos de este runner, requieren pytest+fastapi reales: {', '.join(sorted(excluded))})\n")
    print(f"Recolectando {len(files)} archivos de prueba...\n")
    for f in files:
        try:
            run_module(f)
        except Exception as e:  # noqa: BLE001
            ERRORS.append((f.name, f"ERROR AL CARGAR MÓDULO: {e}", traceback.format_exc()))

    print(f"\n{'='*70}")
    print(f"PASARON: {len(PASSED)}   FALLARON: {len(FAILED)}   ERRORES: {len(ERRORS)}")
    print(f"{'='*70}\n")

    for name, msg, tb in FAILED:
        print(f"FALLO: {name}\n  {msg}\n")
    for name, msg, tb in ERRORS:
        print(f"ERROR: {name}\n  {msg}")
        print(tb[-800:])
        print()

    sys.exit(0 if not FAILED and not ERRORS else 1)
