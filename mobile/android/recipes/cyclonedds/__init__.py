"""Build the upstream CycloneDDS Python C extension for the target Python."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from pythonforandroid.recipe import Recipe


class CycloneDDSRecipe(Recipe):
    version = "11.0.1"
    url = None
    depends = ["python3"]

    def should_build(self, arch):
        return True

    def build_arch(self, arch):
        root = Path(os.environ["INSIGHT_SOURCE_ROOT"])
        source = root / "deps/cyclonedds-python"
        native = root / "build/android-dds/install"
        # Install through the recipe so rebuilding a p4a distribution cannot
        # discard the library previously copied by Buildozer's add_libs step.
        libs = Path(self.ctx.get_libs_dir(arch.arch))
        libs.mkdir(parents=True, exist_ok=True)
        shutil.copy2(native / "lib/libddsc.so", libs / "libddsc.so")
        python = Recipe.get_recipe("python3", self.ctx)
        if not python.version.startswith("3.11."):
            raise RuntimeError("This Android probe requires Python 3.11")
        target = Path(self.ctx.get_python_install_dir(arch.arch)) / "cyclonedds"
        shutil.copytree(source / "cyclonedds", target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.so", "*.dylib", "__library__.py"))
        # Android's native library loader resolves the APK's lib/arm64-v8a entry.
        (target / "__library__.py").write_text('in_wheel = True\nlibrary_path = "libddsc.so"\n')
        # Qt does not export the WebView JNI functions required by p4a's
        # android module, imported eagerly by its patched ctypes.util.
        # The wheel loader above resolves libddsc directly; only import the
        # optional search helper when the fallback search is actually used.
        internal = target / "internal.py"
        text = internal.read_text()
        old = 'from ctypes.util import find_library\n'
        marker = '            lib = find_library("ddsc")'
        if text.count(old) != 1 or text.count(marker) != 1:
            raise RuntimeError("CycloneDDS loader changed; review Android loader patch")
        internal.write_text(text.replace(old, '').replace(
            marker, '            from ctypes.util import find_library\n' + marker))
        shutil.copy2(source / "LICENSE", target / "LICENSE")
        env = self.get_recipe_env(arch)
        # Collector storage comes from realloc and is not zero-initialized.
        # serdata_to_sample requires a fresh, empty sample container.
        clayer_source = (source / "clayer/pysertype.c").read_text()
        collector_marker = "  bool ok;\n  if (info->valid_data)"
        if clayer_source.count(collector_marker) != 1:
            raise RuntimeError("CycloneDDS collector changed; review sample initialization patch")
        clayer_source = clayer_source.replace(
            collector_marker,
            "  state->containers[state->count] = (ddspy_sample_container_t){0};\n" + collector_marker)
        patched_source = Path(self.get_build_dir(arch.arch)) / "pysertype.c"
        patched_source.parent.mkdir(parents=True, exist_ok=True)
        patched_source.write_text(clayer_source)
        command = shlex.split(env["CC"]) + [
            "-shared", "-fPIC", "-O2",
            "-I" + python.include_root(arch.arch),
            "-I" + str(native / "include"),
            "-I" + str(source / "clayer"),
            str(patched_source),
            "-L" + str(native / "lib"), "-lddsc",
            "-L" + python.link_root(arch.arch), "-lpython3.11",
            "-o", str(target / "_clayer.so"),
        ]
        subprocess.run(command, env=env, check=True)


recipe = CycloneDDSRecipe()
