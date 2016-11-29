# Copyright 2012 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import glance_store
from oslo_log import log as logging
from oslo_utils import excutils
import webob.exc

import glance.api.policy
from glance.common import exception
from glance.common import utils
from glance.common import wsgi
import glance.db
import glance.gateway
from glance import i18n
import glance.notifier


LOG = logging.getLogger(__name__)
_ = i18n._
_LE = i18n._LE

class ImageLinkController(object):
    def __init__(self, db_api=None, store_api=None,
                 policy_enforcer=None, notifier=None,
                 gateway=None):
        if gateway is None:
            db_api = db_api or glance.db.get_api()
            store_api = store_api or glance_store
            policy = policy_enforcer or glance.api.policy.Enforcer()
            notifier = notifier or glance.notifier.Notifier()
            gateway = glance.gateway.Gateway(db_api, store_api,
                                             notifier, policy)
        self.gateway = gateway

    def get(self, req, image_id):
        image_repo = self.gateway.get_repo(req.context)
        try:
            image = image_repo.get(image_id)
            if image.status == 'deactivated':
                msg = _('The requested image has been deactivated. '
                        'Image data download is forbidden.')
                raise exception.Forbidden(message=msg)
        except exception.ImageDataNotFound as e:
            raise webob.exc.HTTPNoContent(explanation=e.msg)
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.msg)
        except exception.Forbidden as e:
            raise webob.exc.HTTPForbidden(explanation=e.msg)

        try:
            image_direct_path = image.get_link()
        except Exception as e:
            raise webob.exc.HTTPForbidden(explanation=e.msg)	

        return {'image_path':image_direct_path, 'image_checksum':image.checksum}

def create_resource():
    """Image data resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    controller = ImageLinkController()
    return wsgi.Resource(controller, deserializer, serializer)
