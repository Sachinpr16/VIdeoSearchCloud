#!/usr/bin/env bash
# =============================================================================
# compile_to_pyc.sh
#
# Compiles every .py file under the project root using the langbind312 conda
# environment (Python 3.12), then replaces each .py file with its compiled
# .pyc counterpart (renamed to the same basename, e.g. app.pyc → app.py).
#
# Usage:
#   bash compile_to_pyc.sh [PROJECT_ROOT]
#
#   PROJECT_ROOT defaults to the directory containing this script.
# =============================================================================

set -euo pipefail

CONDA_ENV="langbind312"
PROJECT_ROOT="${1:-"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"}"

# ---------------------------------------------------------------------------
# Resolve the Python executable inside the conda environment
# ---------------------------------------------------------------------------
PYTHON_BIN="$(conda run -n "$CONDA_ENV" python -c 'import sys; print(sys.executable)')"
echo "[INFO] Using Python: $PYTHON_BIN"
echo "[INFO] Project root: $PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Step 1 – Compile all .py files to .pyc (optimisation level 0 = normal)
#           py_compile writes .pyc files into __pycache__/ beside each source.
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 1] Compiling all .py files …"

find "$PROJECT_ROOT" -type f -name "*.py" | while read -r py_file; do
    "$PYTHON_BIN" -m py_compile "$py_file" && echo "  [OK]  $py_file" \
        || echo "  [ERR] $py_file (skipped)"
done

# ---------------------------------------------------------------------------
# Step 2 – For every compiled .pyc inside a __pycache__/ directory, move it
#           next to the original source file and rename it to match the
#           original .py name, then delete the .py source.
#
# Python 3 stores byte-code as:
#   <pkg>/__pycache__/<module>.cpython-3XX.pyc
# We map that back to:
#   <pkg>/<module>.py  →  <pkg>/<module>.pyc
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 2] Replacing .py files with .pyc files …"

find "$PROJECT_ROOT" -type f -name "*.pyc" -path "*/__pycache__/*" | while read -r pyc_file; do

    # Directory that contains __pycache__/
    parent_dir="$(dirname "$(dirname "$pyc_file")")"

    # Filename inside __pycache__, e.g. "app.cpython-312.pyc"
    pyc_basename="$(basename "$pyc_file")"

    # Strip the ".cpython-3XX.pyc" suffix to recover the module name
    # e.g.  app.cpython-312.pyc  →  app
    module_name="${pyc_basename%.cpython-*.pyc}"

    original_py="$parent_dir/${module_name}.py"
    target_pyc="$parent_dir/${module_name}.pyc"

    # Only proceed if the matching source file still exists
    if [ -f "$original_py" ]; then
        cp "$pyc_file" "$target_pyc"
        rm -f "$original_py"
        echo "  [REPLACED] $original_py → $target_pyc"
    fi
done

# ---------------------------------------------------------------------------
# Step 3 – Clean up now-empty __pycache__ directories (optional but tidy)
# ---------------------------------------------------------------------------
echo ""
echo "[STEP 3] Removing __pycache__ directories …"
find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "[DONE] All .py files have been replaced with .pyc files."
