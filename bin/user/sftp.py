# Copyright 2018 Matthew Wall
# Distributed under the terms of GPLv3
"""
Generator for weewx that uploads data using sftp.  Copy everything from a
designated local directory to a remote directory, using the sftp protocol.

This generator is intended to be functionally equivalent to the FTP generator
in weewx, but using a different protocol.

The sftp protocol is not the same as the ftps protocol!  The ftps protocol
is supported by the standard FTP generator in weewx.  This generator uses sftp,
which requires the pysftp module.

Based on the FTP generator in weewx, with help from the SFTP generator
implemented by davies-barnard.
"""

import os
import time

try:
    from six.moves import cPickle
except ImportError:
    import cPickle

import weewx
import weewx.reportengine
from weeutil.weeutil import to_bool

try:
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)

    def logdbg(msg, label=None):
        if label is None:
            label = 'sftp'
        log.debug("%s: %s" % (label, msg))
    def loginf(msg, label=None):
        if label is None:
            label = 'sftp'
        log.info("%s: %s" % (label, msg))
    def logerr(msg, label=None):
        if label is None:
            label = 'sftp'
        log.error("%s: %s" % (label, msg))
except ImportError:
    import syslog

    def logmsg(level, msg, label):
        if label is None:
            label = 'sftp'
        syslog.syslog(level, '%s: %s' % (label, msg))
    def logdbg(msg, label=None):
        logmsg(syslog.LOG_DEBUG, msg, label)
    def loginf(msg, label=None):
        logmsg(syslog.LOG_INFO, msg, label)
    def logerr(msg, label=None):
        logmsg(syslog.LOG_ERR, msg, label)


VERSION = "0.7"


class SFTPUploader(object):

    def __init__(self, server, user, password, local_root, remote_root,
                 private_key=None, private_key_pass=None,
                 port=22, name='SFTP', max_tries=3, debug=0):
        import pysftp
        self.server = server
        self.user = user
        self.password = password
        self.private_key = private_key
        self.private_key_pass = private_key_pass
        self.local_root = os.path.normpath(local_root)
        self.remote_root = os.path.normpath(remote_root)
        self.port = port
        self.name = name
        self.max_tries = max_tries
        self.debug = debug
        logdbg("local_root=%s" % self.local_root)
        logdbg("remote_root=%s" % self.remote_root)
        logdbg("server=%s port=%s user=%s" % (server, port, user))

    def run(self):
        import pysftp
        n_uploaded = 0
        (timestamp, fileset) = self.get_last_upload()
        con = None
        try:
            logdbg("connecting to %s@%s" % (self.user, self.server))
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None
            for cnt in range(self.max_tries):
                try:
                    con = pysftp.Connection(host=self.server,
                                            username=self.user,
                                            password=self.password,
                                            port=self.port,
                                            private_key=self.private_key,
                                            private_key_pass=self.private_key_pass,
                                            cnopts=cnopts)
                    break
                except pysftp.ConnectionException as e:
                    logerr("connect %s of %s failed: %s" %
                           (cnt + 1, self.max_tries, e))
            else:
                logerr("failed %s attempts for %s@%s" %
                       (self.max_tries, self.user, self.server))
                return n_uploaded

            for (dirpath, unused_dirs, filenames) in os.walk(self.local_root):
                # strip out the common local root directory
                local_rel_dir_path = dirpath.replace(self.local_root, '.')
                if self._skip_dir(local_rel_dir_path):
                    continue
                # this is the absolute path to the remote directory
                remote_dir_path = os.path.normpath(
                    os.path.join(self.remote_root, local_rel_dir_path))
                # create the remote directory
                self._make_remote_dir(con, remote_dir_path)
                # iterate over all members of the local directory
                for filename in filenames:
                    full_local_path = os.path.join(dirpath, filename)
                    # see if this file can be skipped
                    if self._skip_file(timestamp, fileset, full_local_path):
                        continue
                    full_remote_path = os.path.join(remote_dir_path, filename)
                    for cnt in range(self.max_tries):
                        try:
                            con.put(full_local_path, full_remote_path)
                        except (OSError, IOError) as e:
                            loginf("attempt %s of %s failed: %s" %
                                   (cnt + 1, self.max_tries, e))
                        else:
                            n_uploaded += 1
                            fileset.add(full_local_path)
                            logdbg("uploaded file %s" % full_remote_path)
                            break
                    else:
                        logerr("failed to upload file %s" % full_remote_path)
        finally:
            if con is not None:
                try:
                    con.quit()
                except Exception:
                    pass
        timestamp = time.time()
        self.save_last_upload(timestamp, fileset)
        return n_uploaded

    def get_last_upload(self):
        """read the time and members of the last upload from local root"""
        tsfile = os.path.join(self.local_root, "#%s.last" % self.name)
        try:
            with open(tsfile, "rb") as f:
                timestamp = cPickle.load(f)
                fileset = cPickle.load(f)
        except (IOError, EOFError, cPickle.PickleError):
            timestamp = 0
            fileset = set()
            try:
                os.remove(tsfile)
            except OSError:
                pass
        return (timestamp, fileset)

    def save_last_upload(self, timestamp, fileset):
        """save the time and members of the last upload in the local root"""
        tsfile = os.path.join(self.local_root, "#%s.last" % self.name)
        try:
            with open(tsfile, "wb") as f:
                cPickle.dump(timestamp, f)
                cPickle.dump(fileset, f)
        except IOError as e:
            loginf("failed to save upload time: %s" % e)

    def _make_remote_dir(self, con, remote_dir_path):
        """create remote directory using the server connection"""
        logdbg("create remote directory %s" % remote_dir_path)
        for _ in range(self.max_tries):
            try:
                if not con.isdir(remote_dir_path):
                    con.mkdir(remote_dir_path)
                break
            except OSError as e:
                logdbg("create remote directory failed: %s" % e)
        else:
            logdbg("create remote directory failed")

    def _skip_dir(self, local_dir):
        for x in ['.svn', 'CVS', '.git']:
            if x in local_dir:
                return True
        return False

    def _skip_file(self, timestamp, fileset, full_local_path):
        # resolve the local file
        filename = os.path.basename(full_local_path)

        # ignore temporary files
        if (filename[0] == '#' or
            filename.startswith('.#') or
            filename[-1] == '~'):
            return True

        # does the file appear in the fileset?
        flag = True
        if full_local_path not in fileset:
            flag = False

        # has the file been updated/changed since last upload?
        ftime = os.stat(full_local_path).st_mtime
        if ftime > timestamp:
            flag = False

        return flag


class SFTPGenerator(weewx.reportengine.ReportGenerator):

    def run(self):
        log_success = to_bool(self.skin_dict.get('log_success', True))
        t1 = time.time()
        if 'HTML_ROOT' in self.skin_dict:
            local_root = os.path.join(
                self.config_dict['WEEWX_ROOT'],
                self.skin_dict['HTML_ROOT'])
        else:
            local_root = os.path.join(
                self.config_dict['WEEWX_ROOT'],
                self.config_dict.get('StdReport', {}).get('HTML_ROOT', 'public_html'))

        logdbg("running SFTPGenerator %s" % VERSION)

        try:
            uploader = SFTPUploader(
                server=self.skin_dict['server'],
                user=self.skin_dict['user'],
                password=self.skin_dict.get('password'),
                private_key=self.skin_dict.get('private_key'),
                private_key_pass=self.skin_dict.get('private_key_pass'),
                local_root=local_root,
                remote_root=self.skin_dict['path'],
                port=int(self.skin_dict.get('port', 22)),
                name=self.skin_dict.get('REPORT_NAME', 'SFTP'),
                max_tries=int(self.skin_dict.get('max_tries', 3)),
                debug=int(self.skin_dict.get('debug', 0)))
        except KeyError as e:
            loginf("upload not possible: missing parameter %s" % e,
                   "sftpgenerator")
            return
        except ImportError as e:
            loginf("upload not possible: %s" % e, "sftpgenerator")
            return

        try:
            n = uploader.run()
        except () as e:
            logerr("%s" % e, "sftpgenerator")
            return

        t2 = time.time()
        if log_success:
            loginf("transferred %d files in %0.2f seconds" % (n, (t2 - t1)),
                   "sftpgenerator")


# entry point for testing this code
# PYTHONPATH=bin python bin/user/sftp.py weewx.conf
if __name__ == '__main__':
    import configobj
    import optparse
    import socket
    parser = optparse.OptionParser()
    parser.add_option("--config", dest="config_path", metavar="CONFIG_FILE",
                      default="/home/weewx/weewx.conf",
                      help="Use configuration file CONFIG_FILE")
    parser.add_option("--report", default="SFTP",
                      help="Use the specified report from StdReport")
    parser.add_option("--debug", action="store_true",
                      help="Enable verbose logging")
    (options, args) = parser.parse_args()

    debug = 0
    if options.debug:
        weewx.debug = 1
        debug = 1

    cfg = dict()
    try:
        cfg = configobj.ConfigObj(options.config_path)
    except IOError:
        pass

    stdrep = cfg.get('StdReport', {})
    skin = stdrep.get(options.report, {})
    config_dict = {
        'WEEWX_ROOT': cfg.get('WEEWX_ROOT', '/home/weewx'),
        'StdReport': {
            'HTML_ROOT': stdrep.get('HTML_ROOT', '/var/www/html')
            }
        }
    skin_dict = {
        'server': skin.get('server', 'localhost'),
        'port': skin.get('port', 22),
        'user': skin.get('user', 'username'),
        'password': skin.get('password', 'password'),
        'path': skin.get('path', '/pub'),
        'debug': skin.get('debug', debug),
        }

    print("connect to %s:%s" % (skin_dict['server'], skin_dict['port']))
    print("destination: %s" % skin_dict['path'])
    print("username: %s" % skin_dict['user'])
    socket.setdefaulttimeout(10)
    gen = SFTPGenerator(
        config_dict, skin_dict, gen_ts=None, first_run=None, stn_info=None)
    gen.run()
