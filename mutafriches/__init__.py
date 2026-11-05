def classFactory(iface):  # noqa: N802 (nom imposé par QGIS)
    from .plugin import MutafrichesPlugin

    return MutafrichesPlugin(iface)
