"""Platform checks that also work with python-for-android's Linux platform tag."""
import os
import sys

IS_ANDROID = sys.platform == "android" or "ANDROID_ARGUMENT" in os.environ
