#!/usr/bin/python

#
# Watchdog script to monitor processes. Uses plugin system for each monitor.
# Note: it's self contained (1 file) on purpose for easier deployment.
#

import sys, os, time
import ConfigParser
import optparse
import logging
from logging import handlers
import psutil, subprocess
import datetime

FULLFORMAT = "%(asctime)s  [%(levelname)s]  [%(module)s] %(message)s"

logger = logging.getLogger("watchdog")

class Settings(object):
    """Application Settings
    """
    __shared_state = {"cp": ConfigParser.RawConfigParser(allow_no_value=True),}

    def __init__(self, conffile):
        self.__dict__ = self.__shared_state
        self.cp.read(conffile)
        
    def getSection(self, section):
        """Returns the whole section in a dictionary
        """
        options = self.cp.options(section)
        result = {}
        for option in options:
            result[option] = self.cp.get(section, option)
        return result


class WatchdogPlugin(object):
    @staticmethod
    def getPlugin(plugin, name, proc, threshold, cmd):
        plugins = {'mem' : MemoryPlugin, 'cpu' : CpuPlugin }
        try:            
            return plugins[plugin](name, proc, threshold, cmd)
        except KeyError:
            raise Exception("Plugin %s does not exist" % plugin)

    def __init__(self, name, proc, threshold, cmd):
        self.name = name
        self.proc = proc
        self.threshold = threshold
        self.cmd = cmd

    def run(self):
        logger.debug("checking %s: %s" % (self.name, self.proc.pid))
        if self.check(self.threshold):
            logger.info("%s reached threshold", self.name)
            self.launcher(self.cmd)
            logger.info("%s triggered", self.name)

    def check(self, value):
        pass

    def launcher(self, cmd):
        cmdargs = cmd.split(" ")
        subprocess.call(cmdargs)

class CpuPlugin(WatchdogPlugin):
    def check(self, threshold):
        # blocking call:
        cpu = self.proc.get_cpu_percent(1)
        logger.debug("cpu: %s, threshold: %s" % (cpu, threshold))
        return cpu > threshold

class MemoryPlugin(WatchdogPlugin):
    def human(self, num, power="MB"):
        powers = ["KB", "MB", "GB", "TB"]        
        for i in powers:
            num /= 1024.0
            if power == i:
                break
        return (float(num), power)

    def check(self, threshold):
        (memrss, memvss) = self.proc.get_memory_info() # memory in bytes
        try:
            (mem, frmt) = threshold.split(" ") # (X, KB), (X, MB), ...
        except ValueError:
            (mem, frmt) = (threshold, "KB")
        
        mem = float(mem)
        memrss = self.human(memrss, frmt)
        memvss = self.human(memvss, frmt)
        hmemrss = "%.1f %s" % memrss
        hmemvss = "%.1f %s" % memvss

        logger.debug("mem: %s, %s, threshold: %s" % (hmemrss, hmemvss, threshold))                            
        return memrss[0] > mem

class Watchdog(object):
    """Watchdog
    """

    def __init__(self, settings):
        self.settings = settings
        self.wait = self.settings.cp.getint("DEFAULT", "wait")
        logger.debug("timer set to %s" % datetime.timedelta(seconds=self.wait))

    def run(self):
        logger.info("running watchdog")
        while True:
            programs = self.settings.cp.sections()
            for program in programs:
                name = self.settings.cp.get(program, "name")
                plugin = self.settings.cp.get(program, "plugin")
                threshold = self.settings.cp.get(program, "value")
                cmd = self.settings.cp.get(program, "cmd")

                for pid in psutil.get_pid_list():
                    try:
                        proc = psutil.Process(pid)
                        if name in " ".join(proc.cmdline):
                            # create plugin and execute it
                            plugin = WatchdogPlugin.getPlugin(plugin, name, proc, threshold, cmd)
                            plugin.run()
                    except psutil.error.NoSuchProcess:
                        logger.debug("NoSuchProcess: %s" % pid)
            time.sleep(self.wait)

def daemonize():
    # http://code.activestate.com/recipes/66012/
    # do the UNIX double-fork magic, see Stevens" "Advanced 
    # Programming in the UNIX Environment" for details (ISBN 0201563177)
    try:
        pid = os.fork() 
        if pid > 0:
            # exit first parent
            sys.exit(0) 
    except OSError, e: 
        print >> sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/") 
    os.setsid() 
    os.umask(0) 

    # do second fork
    try: 
        pid = os.fork() 
        if pid > 0:
            # exit from second parent, print eventual PID before
            logger.info("Daemon PID %d" % pid)
            try:
                pidfile = open("/var/run/%s.pid" % os.path.basename(__file__), "w")
                pidfile.write(str(pid))
                pidfile.close()
            except IOError:
                logger.debug("Could not open pid file")
            sys.exit(0) 
    except OSError, e: 
        print >> sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1) 


def main():
    # Setup the command line arguments.
    optp = optparse.OptionParser()

    # options.
    optp.add_option("-d", "--daemon", dest="daemon",
                    help="daemonize.", action="store_true")

    optp.add_option("-v", "--verbose", dest="verbose",
                    help="log verbosity.", action="store_true")

    optp.add_option("-c", "--conf", dest="conf",
                    help="configuration file.")

    opts, args = optp.parse_args()

    if opts.conf is None:
        print >> sys.stderr, "conf file not provided"
        optp.print_help()
        sys.exit(1)

    if opts.verbose in (None, False):
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    # log to stderr in fg
    logging.basicConfig(level=loglevel,
                            format=FULLFORMAT)

    # log to syslog in bg
    logsys = handlers.SysLogHandler("/dev/log", handlers.SysLogHandler.LOG_USER)
    logsys.setLevel(loglevel)
    logsys.setFormatter(logging.Formatter(FULLFORMAT))
    logger.addHandler(logsys)

    if opts.daemon:
        logger.debug("daemonize")
        daemonize()

    logger.debug("watchdog")
    settings = Settings(opts.conf)
    wg = Watchdog(settings)
    wg.run()

if __name__ == "__main__":    
    main()
