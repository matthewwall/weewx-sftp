# installer for SFTPGenerator
# Copyright 2018 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)

from setup import ExtensionInstaller

def loader():
    return SFTPInstaller()

class SFTPInstaller(ExtensionInstaller):
    def __init__(self):
        super(SFTPInstaller, self).__init__(
            version="0.1",
            name='sftp',
            description='Upload data using the sftp protocol',
            author="Matthew Wall",
            author_email="mwall@users.sourceforge.net",
            files=[('bin/user', ['bin/user/sftp.py'])]
            )
