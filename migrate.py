#!/usr/bin/python3
import sys
import lib.migrate as migrate


if len(sys.argv) < 2:
    print("Usage example : ./migrate.py [PROJECT_IDENTIFIER]")
    sys.exit(1)

project_identifier = sys.argv[-1]
if not migrate.bootstrap(project_identifier):
    print("Project with identifier '{0}' not found on src database".format(
        project_identifier
    ))
    sys.exit(1)

print("all tasks finished successfully.")
