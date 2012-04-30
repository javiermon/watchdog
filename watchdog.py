#!/usr/bin/python
import sys, os, time
import ConfigParser
import optparse
import logging
from logging import handlers
import psutil, subprocess

CONFIG="watchdog.ini"

logger = logging.getLogger("watchdog")

class Settings(object):
    """Application Settings
    """
    __shared_state = {"cp": ConfigParser.RawConfigParser(allow_no_value=True),}

    def __init__(self):
        self.__dict__ = self.__shared_state
        self.cp.read(CONFIG)
        
    def getSection(self, section):
        """Returns the whole section in a dictionary
        """
        options = self.cp.options(section)
        result = {}
        for option in options:
            result[option] = self.cp.get(section, option)
        return result


class Watchdog(object):
    """Watchdog
    """

    def __init__(self):
        self.settings = Settings()
        self.wait = self.settings.cp.getint("DEFAULT", "wait")
      
    def human(self, num, power="MB"):
        powers = ["KB", "MB", "GB", "TB"]        
        for i in powers:
            num /= 1024.0
            if power == i:
                break
        return (float(num), power)

    def run(self):
        while True:
            programs = self.settings.cp.sections()
            for program in programs:
                name = self.settings.cp.get(program, "name")
                memthreshold = self.settings.cp.get(program, "mem")
                cmd = self.settings.cp.get(program, "cmd")
                for pid in psutil.get_pid_list():
                    try:
                        if name in " ".join(psutil.Process(pid).cmdline):
                            logger.debug("checking %s: %s" % (name, pid))
                            proc = psutil.Process(pid)
                            (memrss, memvss) = proc.get_memory_info() # memory in bytes
                            try:
                                (mem, frmt) = memthreshold.split(" ") # (X, KB), (X, MB), ...
                            except:
                                (mem, frmt) = (memthreshold, "KB")
                    
                            mem = float(mem)
                            memrss = self.human(memrss, frmt)
                            memvss = self.human(memvss, frmt)
                            hmemrss = "%.1f %s" % memrss
                            hmemvss = "%.1f %s" % memvss

                            logger.debug("mem: %s, %s, threshold: %s" % (hmemrss, hmemvss, memthreshold))                            
                            if memrss[0] > mem:
                                logger.info("%s reached threshold", name)
                                cmdargs = cmd.split(" ")
                                subprocess.call(cmdargs)
                                logger.info("%s restarted", name)
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
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror) 
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
            sys.exit(0) 
    except OSError, e: 
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1) 


def main():
    # Setup the command line arguments.
    optp = optparse.OptionParser()

    # options.
    optp.add_option("-d", "--daemon", dest="daemon",
                    help="daemonize.", action="store_true")

    optp.add_option("-v", "--verbose", dest="verbose",
                    help="log verbosity.", action="store_true")

    opts, args = optp.parse_args()

    if opts.verbose in (None, False):
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    logging.basicConfig(level=loglevel,
                            format="%(levelname)-8s %(message)s")

    logsys = handlers.SysLogHandler("/dev/log",handlers.SysLogHandler.LOG_USER)
    logsys.setLevel(logging.DEBUG)
    logger.addHandler(logsys)

    logger.info("starting watchdog")
    if opts.daemon in (None, False):
        settings = Settings()
        opts.daemon = settings.cp.getboolean("DEFAULT","daemon")

    if opts.daemon:
        # daemonize
        logger.debug("daemonize")
        daemonize()

    wg = Watchdog()
    wg.run()

if __name__ == "__main__":
    main()
