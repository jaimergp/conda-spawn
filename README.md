# conda-spawn

Activate conda environments in new shell processes.

> [!IMPORTANT]
> This project is still in early stages of development. Don't use it in production (yet).
> We do welcome feedback on what the expected behaviour should have been if something doesn't work!

## What is this?

This is a replacement subcommand for `conda activate` and `conda deactivate`.

Instead of writing state to your current shell session, `conda spawn -n ENV-NAME` will spawn a new shell with your activated environment. To deactivate, exit the process with <kbd>Ctrl</kbd>+<kbd>D</kbd>, or run the command `exit`.

## Installation

This is a `conda` plugin and goes in the `base` environment:

```bash
conda install -n base conda-forge::conda-spawn
```

Since it only relies on the `conda` entry point being on `PATH`, you will probably want to remove all the shell initialization stuff from your profiles with:

```bash
conda init --reverse
```

Then, make sure you have added `$CONDA_ROOT/condabin` to your PATH, with `$CONDA_ROOT` being the path to your conda installation. For example, assuming you installed `conda` in `~/conda`, your `~/.bashrc` would need this line:

```bash
export PATH="${PATH}:${HOME}/conda/condabin"
```

On Windows, open the Start Menu and search for "environment variables". You will be able to add the equivalent location (e.g. `C:\Users\username\conda\condabin`) to the `PATH` variable via the UI.

## Why?

The main reasons include:

- Cleaner shell interaction with no need for a `conda` shell function.
- Avoid messing with existing shell processes.
- Faster shell startup when `conda` is not needed.
- Simpler installation and bookkeeping.

## FAQ

### I can't use this in my scripts anymore!

For in-script usage, please consider these replacements for `conda activate`:

For Unix shell scripts:

```bash
eval "$(conda shell.posix activate <ENV-NAME>)"
```

For Windows CMD scripts:

```cmd
FOR /F "tokens=*" %%g IN ('conda shell.cmd.exe activate <ENV-NAME>') do @CALL %%g
```

For Windows Powershell scripts:

```powershell
conda shell.posix activate <ENV-NAME> | Out-String | Invoke-Expression
```

For example, if you want to create a new environment and activate it, it would look like this:

```bash
# Assumes `conda` is in PATH
conda create -n new-env python numpy
eval "$(conda shell.posix activate new-env)"
python -c "import numpy"
```

## Contributing

Please refer to [`CONTRIBUTING.md`](/CONTRIBUTING.md).
