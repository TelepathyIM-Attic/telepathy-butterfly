# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
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
from pymsn.service.description.AB.constants import \
    ContactGeneral, ContactAnnotations

from butterfly.handle import ButterflyHandleFactory
from butterfly.util.decorator import async

__all__ = ['ButterflyAliasing']

logger = logging.getLogger('Butterfly.Aliasing')

class ButterflyAliasing(
        telepathy.server.ConnectionInterfaceAliasing,
        pymsn.event.ContactEventInterface):

    def __init__(self):
        telepathy.server.ConnectionInterfaceAliasing.__init__(self)
        pymsn.event.ContactEventInterface.__init__(self, self.msn_client)

    def RequestAliases(self, contacts):
        result = []
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle == ButterflyHandleFactory(self, 'self'):
                display_name = self.msn_client.profile.display_name
                if display_name == "":
                    display_name = handle.get_name().split('@', 1)[0]
                    display_name = display_name.replace("_", " ")
                result.append(unicode(display_name, 'utf-8'))
            else:
                contact = handle.contact
                if contact is None:
                    result.append(handle.account, 'utf-8')
                else:
                    alias = contact.infos.get(ContactGeneral.ANNOTATIONS, {}).\
                        get(ContactAnnotations.NICKNAME, None)
                    if alias == "" or alias is None:
                         alias = contact.display_name
                    result.append(unicode(alias, 'utf-8'))
        return result

    def SetAliases(self, aliases):
        for handle_id, alias in aliases.iteritems():
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle != ButterflyHandleFactory(self, 'self'):
                contact = handle.contact
                # FIXME: we would maybe like to queue it until the contact is created ?
                if contact is None:
                    continue
                # FIXME: we don't want this, do we ? 
                if contact.id == "00000000-0000-0000-0000-000000000000":
                    continue

                if alias == handle.name: 
                    alias = ""
                infos = { ContactGeneral.ANNOTATIONS : \
                     { ContactAnnotations.NICKNAME : alias.encode('utf-8') }}
                self.msn_client.address_book.\
                    update_contact_infos(contact, infos)
            else:
                self.msn_client.profile.display_name = alias
                logger.info("Self alias changed to '%s'" % alias)
                self.AliasesChanged(((ButterflyHandleFactory(self, 'self'), alias), ))

    # pymsn.event.ContactEventInterface
    def on_contact_display_name_changed(self, contact):
        self._contact_alias_changed(contact)

    # pymsn.event.ContactEventInterface
    def on_contact_infos_changed(self, contact, updated_infos):
        alias = updated_infos.get(ContactGeneral.ANNOTATIONS, {}).\
            get(ContactAnnotations.NICKNAME, None)

        if alias is not None or alias != "":
            self._contact_alias_changed(contact)

    @async
    def _contact_alias_changed(self, contact):
        handle = ButterflyHandleFactory(self, 'contact',
                contact.account, contact.network_id)

        alias = contact.infos.get(ContactGeneral.ANNOTATIONS, {}).\
            get(ContactAnnotations.NICKNAME, None)

        if alias == "" or alias is None:
            alias = contact.display_name

        alias = unicode(alias, 'utf-8')
        logger.info("Contact %r alias changed to '%s'" % (handle, alias))
        self.AliasesChanged(((handle, alias), ))

