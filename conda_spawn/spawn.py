import pexpect
import signal
import sys

def main():
    # Disable Ctrl+C (SIGINT)
    def disable_ctrl_c(signum, frame):
        print("\nCtrl+C is disabled. Use Ctrl+D to exit.")

    signal.signal(signal.SIGINT, disable_ctrl_c)

    # Start a bash shell with pexpect
    shell = pexpect.spawn('/bin/bash', encoding='utf-8')

    # Preconfigure the shell
    shell.sendline('export CUSTOM_VAR="Hello, custom shell!"')
    shell.sendline('echo "Custom shell configured. Type Ctrl+D to exit. Ctrl+C is disabled."')

    # Hand over interaction to the user
    print("\nStarting interactive shell...\n")
    sys.stdout.flush()  # Ensure output is displayed immediately
    try:
        # Start interactive mode
        shell.interact()
    except OSError:
        pass  # Handle shell exit gracefully
    finally:
        print("\nShell exited. Goodbye!")

if __name__ == "__main__":
    main()
