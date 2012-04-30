import os
import ConfigParser
from optparse import OptionParser
import logging

CONFIG='watchdog.ini'

logger = logging.getLogger('watchdog')

def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')

    # Setup the command line arguments.
    optp = OptionParser()

    # JID and password options.
    optp.add_option("-d", "--daemon", dest="daemon",
                    help="daemonize.", type='str')

    opts, args = optp.parse_args()
    
    if opts.daemon is not None:
        # daemonize
        bots_ids = botconfig.config['bots'][:opts.bots]    


if __name__ == '__main__':
    main()




