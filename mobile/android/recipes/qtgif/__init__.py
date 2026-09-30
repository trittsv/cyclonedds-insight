"""Package Qt's GIF decoder where Android's Qt plugin loader searches."""
from pathlib import Path
import shutil

from pythonforandroid.recipe import Recipe


class QtGifRecipe(Recipe):
    version = "1"
    url = None
    depends = ["PySide6"]

    def should_build(self, arch):
        return True

    def build_arch(self, arch):
        filename = f"libplugins_imageformats_qgif_{arch.arch}.so"
        source = (Path(self.ctx.get_python_install_dir(arch.arch))
                  / "PySide6/Qt/plugins/imageformats" / filename)
        if not source.is_file():
            raise RuntimeError(f"Qt GIF plugin is missing from the Android wheel: {source}")
        # Qt on Android scans flat native-library directories, not the desktop
        # plugins/imageformats hierarchy left inside the Python wheel bundle.
        destination = Path(self.ctx.get_libs_dir(arch.arch))
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination / filename)


recipe = QtGifRecipe()
