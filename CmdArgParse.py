import sys
import argparse

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--addr", help = "server IP Address (default = 127.0.0.1)", type = str)
    parser.add_argument("--port", help = "server Port (default = 49152)", type = int)
    args = parser.parse_args()

    return(args)