import importlib

# Redirect the 'app' package to the actual implementation in 'backend.app'
module = importlib.import_module('backend.app')
# Expose the imported module as this package
globals().update(module.__dict__)
# Ensure submodules are correctly resolved
import sys
sys.modules[__name__] = module
