# conda-spawn

Activate conda environments in new shell processes.

> [!IMPORTANT]
> This project is still in early stages of development. Don't use it in production (yet).
> We do welcome feedback on what the expected behaviour should have been if something doesn't work!

## What is this?

This is a replacement subcommand for `conda activate` and `conda deactivate`.

Instead of writing state to your current shell session, `conda spawn -n ENV-NAME` will spawn a new shell with your activated environment. To deactivate, exit the process with <kbd>Ctrl</kbd>+<kbd>C</kbd> or <kbd>Ctrl</kbd>+<kbd>D</kbd>.

## Why?

In a nutshell, this provides a cleaner activation experience without state leakage. See the Rationale section in our documentation for more details.

## Contributing

Please refer to [`CONTRIBUTING.md`](/CONTRIBUTING.md).
