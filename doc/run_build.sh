if [ ! -d ".venv_doc" ] ; then
  python -m venv .venv_doc
  source ./venv_doc/bin/activate
  python -m pip install -r requirements.txt
fi

source ./venv_doc/bin/activate

sphinx-build -M html . build/
