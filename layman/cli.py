#!/usr/bin/python
# -*- coding: utf-8 -*-
#################################################################################
# LAYMAN ACTIONS
#################################################################################
# File:       cli.py
#
#             Handles layman actions via the command line interface.
#
# Copyright:
#             (c) 2010 - 2011
#                   Gunnar Wrobel
#                   Brian Dolbec
#             Distributed under the terms of the GNU General Public License v2
#
# Author(s):
#             Gunnar Wrobel <wrobel@gentoo.org>
#             Brian Dolbec <brian.dolbec@gmail.com
#
''' Provides the command line actions that can be performed by layman.'''

__version__ = "$Id: cli.py 2011-01-15 23:52 PST Brian Dolbec$"


import os, sys

from layman.api import LaymanAPI
from layman.utils import (decode_selection, encoder, get_encoding,
    pad, terminal_width)
from layman.constants import NOT_OFFICIAL_MSG, NOT_SUPPORTED_MSG



class ListPrinter(object):
    def __init__(self, config):
        self.config = config
        self.output = self.config['output']
        if not self.config['width']:
            self.width = terminal_width()
        else:
            self.width = self.config['width']
        self.srclen = self.width - 43
        self._encoding_ = get_encoding(self.output)
        if config['verbose']:
            self.my_lister = self.short_list # self.long_list
        else:
            self.my_lister = self.short_list

    def print_shortdict(self, info, complain):
        #print "ListPrinter.print_tuple()",info
        ids = sorted(info)
        #print "ids =======>", ids, "\n"
        for _id in ids:
            overlay = info[_id]
            #print "overlay =", overlay
            summary, supported, official = overlay
            self.print_overlay(summary, supported, official, complain)

    def print_shortlist(self, info, complain):
        #print "ListPrinter.print_shortlist()",info
        for summary, supported, official in info:
            self.print_overlay(summary, supported, official, complain)


    def print_fulldict(self, info, complain):
        ids = sorted(info)
        #print "ids =======>", ids, "\n"
        for ovl in ids:
            overlay = info[ovl]
            #print overlay
            self.print_overlay(self.my_lister(overlay),
                               overlay['supported'],
                               overlay['official'],
                               complain)


    def print_overlay(self, summary, supported, official, complain):
        # Is the overlay supported?
        if supported:
            # Is this an official overlay?
            if official:
                self.output.info(summary, 1)
            # Unofficial overlays will only be listed if we are not
            # checking or listing verbose
            elif complain:
                # Give a reason why this is marked yellow if it is a verbose
                # listing
                if self.config['verbose']:
                    self.output.warn(NOT_OFFICIAL_MSG, 1)
                self.output.warn(summary, 1)
        # Unsupported overlays will only be listed if we are not checking
        # or listing verbose
        elif complain:
            # Give a reason why this is marked red if it is a verbose
            # listing
            if self.config['verbose']:
                self.output.error(NOT_SUPPORTED_MSG)
            self.output.error(summary)


    def short_list(self, overlay):
        '''
        >>> print short_list(overlay)
        wrobel                    [Subversion] (https://o.g.o/svn/dev/wrobel         )
        '''
        name   = pad(overlay['name'], 25)

        if len(set(e for e in overlay['src_types'])) == 1:
            _type = overlay['src_types'][0]
        else:
            _type = '%s/..' % overlay['src_type'][0]
        mtype  = ' [' + pad(_type, 10) + ']'

        source = ', '.join(overlay['src_uris'])

        if len(source) > self.srclen:
            source = source.replace("overlays.gentoo.org", "o.g.o")
        source = ' (' + pad(source, self.srclen) + ')'

        return encoder(name + mtype + source, self._encoding_)


class Main(object):
    '''Performs the actions the user selected.
    '''

    def __init__(self, config):
        self.config = config
        #print "config.keys()", config.keys()
        self.output = config['output']
        self.api = LaymanAPI(config,
                             report_errors=True,
                             output=config.output)
        # Given in order of precedence
        self.actions = [('fetch',      'Fetch'),
                        ('add',        'Add'),
                        ('sync',       'Sync'),
                        ('info',       'Info'),
                        ('sync_all',   'Sync'),
                        ('delete',     'Delete'),
                        ('list',       'ListRemote'),
                        ('list_local', 'ListLocal'),]

    def __call__(self):
        # Make fetching the overlay list a default action
        if not 'nofetch' in self.config.keys():
            # Actions that implicitely call the fetch operation before
            fetch_actions = ['sync', 'sync_all', 'list']
            for i in fetch_actions:
                if i in self.config.keys():
                    # Implicitely call fetch, break loop
                    self.Fetch()
                    break

        result = 0

        # Set the umask
        umask = self.config['umask']
        try:
            new_umask = int(umask, 8)
            old_umask = os.umask(new_umask)
        except Exception, error:
            self.output.die('Failed setting to umask "' + umask +
                '"!\nError was: ' + str(error))

        for action in self.actions:

            self.output.debug('Checking for action', 7)

            if action[0] in self.config.keys():
                try:
                    result += getattr(self, action[1])()
                except Exception, error:
                    self.output.error(self.api.get_errors())
                    result = -1  # So it cannot remain 0, i.e. success
                    break

        # Reset umask
        os.umask(old_umask)

        if not result:
            sys.exit(0)
        else:
            sys.exit(1)


    def Fetch(self):
        ''' Fetches the overlay listing.
        '''
        return self.api.fetch_remote_list()


    def Add(self):
        ''' Adds the selected overlays.
        '''
        selection = decode_selection(self.config['add'])
        if 'ALL' in selection:
            selection = self.api.get_available()
        self.output.debug('Adding selected overlays', 6)
        result = self.api.add_repos(selection)
        if result:
            self.output.info('Successfully added overlay(s) '+\
                ', '.join(selection) +'.', 2)
        else:
            errors = self.api.get_errors()
            self.output.warn('Failed to add overlay(s).\nError was: '
                             + str('\n'.join(errors)), 2)
        return result



    def Sync(self):
        ''' Syncs the selected overlays.
        '''
        selection = decode_selection(self.config['sync'])
        if self.config['sync_all'] or 'ALL' in selection:
            selection = self.api.get_installed()
        self.output.debug('Updating selected overlays', 6)
        return self.api.sync(selection)


    def Delete(self):
        ''' Deletes the selected overlays.
        '''
        selection = decode_selection(self.config['delete'])
        if 'ALL' in selection:
            selection = self.api.get_installed()
        self.output.debug('Deleting selected overlays', 6)
        result = self.api.delete_repos(selection)
        if result:
            self.output.info('Successfully deleted overlay(s) ' +\
                ', '.join(selection) + '.', 2)
        else:
            errors = self.api.get_errors()
            self.output.warn('Failed to delete overlay(s).\nError was: '
                             + str('\n'.join(errors)), 2)
        return result


    def Info(self):
        ''' Print information about the specified overlays.
        '''
        selection = decode_selection(self.config['info'])
        if 'ALL' in selection:
            selection = self.api.get_available()
        info = self.api.get_info_str(selection)

        for overlay in info:
            # Is the overlay supported?
            self.output.info(overlay[0], 1)
            if not overlay[1]:
                self.output.warn(NOT_OFFICIAL_MSG, 1)
            if not overlay[2]:
                self.output.error(NOT_SUPPORTED_MSG)
        return info != {}


    def ListRemote(self):
        ''' Lists the available overlays.
        '''

        self.output.debug('Printing remote overlays.', 6)
        list_printer = ListPrinter(self.config)
        width = list_printer.width

        _complain = self.config['nocheck'] or self.config['verbose']
        info = self.api.get_info_list(local=False, verbose=self.config['verbose'], width=width)
        list_printer.print_shortlist(info, complain=_complain)

        return info != {}


    def ListLocal(self):
        ''' Lists the local overlays.
        '''
        #print "ListLocal()"
        self.output.debug('Printing installed overlays.', 6)
        list_printer = ListPrinter(self.config)

        _complain = self.config['nocheck'] or self.config['verbose']
        #
        # fast way
        info = self.api.get_info_list(verbose=self.config['verbose'],
                                      width=list_printer.width)
        list_printer.print_shortlist(info, complain=_complain)
        #
        # slow way
        #info = self.api.get_all_info(self.api.get_installed(), local=True)
        #list_printer.print_fulldict(info, complain=_complain)

        return info != {}


if __name__ == '__main__':
    import doctest

    # Ignore warnings here. We are just testing
    from warnings     import filterwarnings, resetwarnings
    filterwarnings('ignore')

    doctest.testmod(sys.modules[__name__])

    resetwarnings()