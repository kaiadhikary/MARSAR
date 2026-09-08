# Offline dependency wheelhouse

On a connected preparation host, download wheels matching the target Linux and
Python version:

```text
python -m pip download -r requirements.txt --dest wheelhouse
```

Transfer this directory with the source bundle. The disconnected build uses:

```text
python -m pip install --no-index --find-links=wheelhouse -r requirements.txt
```

Do not run `pip download`, `curl`, `wget`, `apt`, or package-manager network
operations inside the offline Docker build.
