"""Only inspected adapters belong here; never infer compatibility by version."""
import importlib

ADAPTERS = {'26.1002.7124.0': 'windows_patch', '26.1007.2314.0': 'windows_patch_26_1007', '26.1007.9446.0': 'windows_patch_26_1007_9446'}


def adapter_for(version):
    name = ADAPTERS.get(version)
    if name is None:
        raise ValueError('Uninspected Windows package: ' + str(version))
    adapter = importlib.import_module(name)
    if adapter.VERSION != version:
        raise ValueError('Adapter version does not match its registry entry')
    return adapter
