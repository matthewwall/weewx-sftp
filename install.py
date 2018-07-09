# installer for SFTPGenerator
# Copyright 2018 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)

from setup import ExtensionInstaller

def loader():
    return SFTPInstaller()

class SFTPInstaller(ExtensionInstaller):
    def __init__(self):
        super(SFTPInstaller, self).__init__(
            version="0.2",
            name='sftp',
            description='Upload data using the sftp protocol',
            author="Matthew Wall",
            author_email="mwall@users.sourceforge.net",
            config={
                'StdReport': {
                    'sftp': {
                        'skin': 'sftp',
                        'user': 'replace_me',
                        'password': '"replace_me"',
                        'server': 'replace with the sftp server name',
                        'port': 2222,
                        'path': 'replace with the sftp destination path'}}},
            files=[('bin/user', ['bin/user/sftp.py']),
                   ('skins/sftp', ['skins/sftp/skin.conf'])]
            )
