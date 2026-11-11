from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

    from .plugin import MutafrichesPlugin


def classFactory(iface: "QgisInterface") -> "MutafrichesPlugin":
    from .plugin import MutafrichesPlugin

    return MutafrichesPlugin(iface)
