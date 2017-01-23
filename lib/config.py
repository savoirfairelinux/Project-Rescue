import sys, yaml

try:
    file_config = open('config.yml')
except FileNotFoundError:
    print("config.yml file not found.")
    sys.exit(1)

config = yaml.safe_load(file_config)
file_config.close()
