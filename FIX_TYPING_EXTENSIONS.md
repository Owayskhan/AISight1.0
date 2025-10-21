# Fixing typing_extensions Import Error

## Problem
```
ImportError: cannot import name 'Sentinel' from 'typing_extensions' (/agents/python/typing_extensions.py)
```

This error occurs because there's a conflicting `typing_extensions.py` file in `/agents/python/` that's being imported instead of the proper `typing_extensions` package.

## Solution Options

### Option 1: Force Reinstall typing-extensions (Recommended)
```bash
pip install --force-reinstall --no-cache-dir typing-extensions>=4.5.0
```

### Option 2: Update PYTHONPATH Order
Ensure the virtual environment's site-packages comes before `/agents/python/`:
```bash
export PYTHONPATH="/tmp/8de10184744b6f2/antenv/lib/python3.12/site-packages:/agents/python:/opt/startup/app_logs"
```

### Option 3: Remove Conflicting File (If Safe)
If `/agents/python/typing_extensions.py` is not needed:
```bash
# Backup first
cp /agents/python/typing_extensions.py /tmp/typing_extensions.py.backup
# Remove or rename
mv /agents/python/typing_extensions.py /agents/python/typing_extensions.py.old
```

### Option 4: Install in System Python
If running in a constrained environment:
```bash
python3.12 -m pip install --user --upgrade typing-extensions>=4.5.0 pydantic>=2.0.0
```

## Verification
After applying fix, test with:
```bash
python3 -c "from typing_extensions import Sentinel; print('✅ typing_extensions works!')"
```

## Root Cause
The error happens because:
1. Python looks for modules in PYTHONPATH order
2. `/agents/python/` is in the path before site-packages
3. An older or incomplete `typing_extensions.py` exists there
4. `pydantic_core` needs `Sentinel` from typing_extensions 4.5+

## Quick Test Without Full Install
Test if the API imports work:
```bash
cd /home/asmaa/projects/AISight1.0
python3 -c "
import sys
sys.path.insert(0, '.')
# Try importing our modules
from core.queries.context_builder import build_context_from_brand_and_category
print('✅ context_builder imports OK')
"
```
