#!/usr/bin/env python3
import re
import sys
import argparse


def bump_version(version_file, part='revision'):
    """
    Bump the version in the specified file.

    Args:
        version_file: Path to the file containing the version
        part: Which part of the version to bump ('revision' or 'minor')

    Returns:
        The new version string
    """
    # Read the current version
    with open(version_file, 'r') as f:
        content = f.read()

    # Extract the current version
    version_match = re.search(r"VERSION = '([^']*)'", content)
    if not version_match:
        print(f"Error: Could not find VERSION in {version_file}")
        sys.exit(1)

    current_version = version_match.group(1)
    print(f"Current version: {current_version}")

    # Split the version into parts
    parts = current_version.split('.')
    if len(parts) < 3:
        # Ensure we have at least 3 parts
        parts.extend(['0'] * (3 - len(parts)))

    # Bump the appropriate part
    if part == 'minor':
        parts[1] = str(int(parts[1]) + 1)
        parts[2] = '0'  # Reset patch version
        new_version = '.'.join(parts)
        print(f"Bumping minor version to: {new_version}")
    else:  # revision/patch
        parts[2] = str(int(parts[2]) + 1)
        new_version = '.'.join(parts)
        print(f"Bumping revision to: {new_version}")

    # Update the version in the file
    new_content = re.sub(
        r"VERSION = '[^']*'", f"VERSION = '{new_version}'", content)
    with open(version_file, 'w') as f:
        f.write(new_content)

    # Return the new version for use in the Makefile
    print(new_version)
    return new_version


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bump version in a file')
    parser.add_argument('file', help='File containing the version')
    parser.add_argument('--part', choices=['revision', 'minor'], default='revision',
                        help='Which part of the version to bump (default: revision)')

    args = parser.parse_args()
    bump_version(args.file, args.part)
