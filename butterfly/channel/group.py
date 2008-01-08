# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
# Copyright (C) 2007 Johann Prieur <johann.prieur@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import logging

import telepathy
import pymsn
import pymsn.event

from butterfly.util.decorator import async
from butterfly.handle import ButterflyHandleFactory
from butterfly.channel.contact_list import ButterflyListChannel

__all__ = ['ButterflyGroupChannel']

logger = logging.getLogger('Butterfly.GroupChannel')


class ButterflyGroupChannel(ButterflyListChannel,
            pymsn.event.AddressBookEventInterface):

    def __init__(self, connection, handle):
        self.__pending_add = []
        self.__pending_remove = []
        ButterflyListChannel.__init__(self, connection, handle)
        pymsn.event.AddressBookEventInterface.__init__(self, connection.msn_client)
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD | 
                telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE, 0)
        # Create this group on the server if not existant
        # FIXME: Move the server-side group creation into the GroupHandle.__init__
        @async
        def create_group():
            if handle.group is None:
                connection.msn_client.address_book.add_group(handle.name)
        create_group()

    def AddMembers(self, contacts, message):
        ab = self._conn.msn_client.address_book
        if self._handle.group is None:
            for contact_handle_id in contacts:
                contact_handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT,
                            contact_handle_id)
                logger.info("Adding contact %r to pending group %r" %
                        (contact_handle, self._handle))
                if contact_handle_id in self.__pending_remove:
                    self.__pending_remove.remove(contact_handle_id)
                else:
                    self.__pending_add.append(contact_handle_id)
            return
        else:
            for contact_handle_id in contacts:
                contact_handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT,
                            contact_handle_id)
                logger.info("Adding contact %r to group %r" %
                        (contact_handle, self._handle))
                contact = contact_handle.contact
                group = self._handle.group
                ab.add_contact_to_group(group, contact)

    def RemoveMembers(self, contacts, message):
        ab = self._conn.msn_client.address_book
        if self._handle.group is None:
            for contact_handle_id in contacts:
                contact_handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT,
                            contact_handle_id)
                logger.info("Adding contact %r to pending group %r" %
                        (contact_handle, self._handle))
                if contact_handle_id in self.__pending_add:
                    self.__pending_add.remove(contact_handle_id)
                else:
                    self.__pending_remove.append(contact_handle_id)
            return
        else:
            for contact_handle_id in contacts:
                contact_handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT,
                            contact_handle_id)
                logger.info("Removing contact %r from pending group %r" %
                        (contact_handle, self._handle))
                contact = contact_handle.contact
                group = self._handle.group
                ab.delete_contact_from_group(group, contact)

    def Close(self):
        logger.debug("Deleting group %s" % self._handle.name)
        ab = self._conn.msn_client.address_book
        group = self._handle.group
        ab.delete_group(group)

    def _filter_contact(self, contact):
        for group in contact.groups:
            if group.name == self._handle.name:
                return (True, False, False)
        return (False, False, False)

    def on_addressbook_group_added(self, group):
        if group.name == self._handle.name:
            self.AddMembers(self.__pending_add, None)
            self.__pending_add = []
            self.RemoveMembers(self.__pending_remove, None)
            self.__pending_remove = []

    def on_addressbook_group_deleted(self, group):
        if group.name == self._handle.name:
            self.Closed()
            self._conn.remove_channel(self)

    def on_addressbook_group_contact_added(self, group, contact):
        if group.name == self._handle.name:
            handle = ButterflyHandleFactory(self._conn_ref(), 'contact', contact)

            added = set()
            added.add(handle)

            self.MembersChanged('', added, (), (), (), 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

            logger.debug("Contact %s added to group %s" % (handle.name,
                    group.name))

    def on_addressbook_group_contact_deleted(self, group, contact):
        if group.name == self._handle.name:
            handle = ButterflyHandleFactory(self._conn_ref(), 'contact', contact)

            removed = set()
            removed.add(handle)

            self.MembersChanged('', (), removed, (), (), 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

            logger.debug("Contact %s removed from group %s" % (handle.name,
                    group.name))
