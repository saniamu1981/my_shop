import os
import sys
import subprocess

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    manage_py = os.path.join(project_dir, "manage.py")

    if not os.path.exists(manage_py):
        print(f"ERROR: manage.py not found in {project_dir}")
        sys.exit(1)

    print("Starting Django server...")
    print(f"Project dir: {project_dir}")
    print(f"Python: {sys.executable}")
    print("-" * 50)
    sys.stdout.flush()

    cmd = [sys.executable, manage_py, "runserver"]

    try:
        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        for line in process.stdout:
            print(line, end='')
            sys.stdout.flush()

        process.wait()
        sys.exit(process.returncode)

    except KeyboardInterrupt:
        print("\nStopping server...")
        process.terminate()
        process.wait()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
