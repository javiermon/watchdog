#!/usr/bin/python
import sys, os, time
import ConfigParser
import optparse
import logging
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
                            proc = psutil.Process(pid)
                            mem = proc.get_memory_percent()
                            if mem > memthreshold:
                                logger.info("%s %s > %s", (name, mem, memthreshold))
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
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)-8s %(message)s")

    logger.info("starting watchdog")
    # Setup the command line arguments.
    optp = optparse.OptionParser()

    # options.
    optp.add_option("-d", "--daemon", dest="daemon",
                    help="daemonize.", action="store_true")

    opts, args = optp.parse_args()

    settings = Settings()
    if opts.daemon is None:
        opts.daemon = settings.cp.getboolean("DEFAULT","daemon")

    if opts.daemon:
        # daemonize
        logger.debug("daemonize")
        daemonize()

    wg = Watchdog()
    wg.run()

if __name__ == "__main__":
    main()
