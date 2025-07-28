# TODO(bjafek) this sucks - figure out a better package manager to do this
export PROJECT_DIR="$(pwd)"
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"


python3 $1
