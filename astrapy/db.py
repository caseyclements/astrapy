# Copyright DataStax, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from astrapy.defaults import DEFAULT_AUTH_HEADER, DEFAULT_KEYSPACE_NAME
from astrapy.ops import AstraDBOps
from astrapy.utils import make_payload, make_request, http_methods

import logging

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 20
DEFAULT_BASE_PATH = "/api/json/v1"


class AstraDBCollection:
    def __init__(
            self,
            collection_name,
            astra_db=None,
            db_id=None,
            token=None,
            db_region=None,
            namespace=None,
        ):
        if astra_db is None:
            if db_id is None or token is None:
                raise AssertionError("Must provide db_id and token")

            astra_db = AstraDB(
                db_id=db_id, token=token, db_region=db_region, namespace=namespace
            )

        self.astra_db = astra_db
        self.collection_name = collection_name
        self.base_path = f"{self.astra_db.base_path}/{collection_name}"


    def _request(self, *args, **kwargs):
        result = make_request(
            *args,
            **kwargs,
            base_url=self.astra_db.base_url,
            auth_header=DEFAULT_AUTH_HEADER,
            token=self.astra_db.token,
        )

        return result

    def _get(self, path=None, options=None):
        full_path = f"{self.base_path}/{path}" if path else self.base_path
        response = self._request(
            method=http_methods.GET, path=full_path, url_params=options
        )
        if isinstance(response, dict):
            return response
        return None

    def _post(self, path=None, document=None):
        return self._request(
            method=http_methods.POST, path=f"{self.base_path}", json_data=document
        )

    def get(self, path=None):
        return self._get(path=path)

    def find(self, filter=None, projection=None, sort=None, options=None):
        json_query = make_payload(
            top_level="find",
            filter=filter,
            projection=projection,
            options=options,
            sort=sort
        )

        response = self._request(
            method=http_methods.POST,
            path=f"{self.base_path}",
            json_data=json_query,
        )

        return response

    def pop(self, filter, update, options):
        json_query = make_payload(
            top_level="findOneAndUpdate",
            filter=filter,
            update=update,
            options=options
        )

        response = self._request(
            method=http_methods.POST,
            path=self.base_path,
            json_data=json_query,
        )

        return response

    def push(self, filter, update, options):
        json_query = make_payload(
            top_level="findOneAndUpdate",
            filter=filter,
            update=update,
            options=options
        )

        response = self._request(
            method=http_methods.POST,
            path=self.base_path,
            json_data=json_query,
        )

        return response

    def find_one_and_replace(
        self, sort=None, filter=None, replacement=None, options=None
    ):
        json_query = make_payload(
            top_level="findOneAndReplace",
            filter=filter,
            replacement=replacement,
            options=options,
            sort=sort
        )

        response = self._request(
            method=http_methods.POST, path=f"{self.base_path}", json_data=json_query
        )

        return response

    def find_one_and_update(self, sort=None, update=None, filter=None, options=None):
        json_query = make_payload(
            top_level="findOneAndUpdate",
            filter=filter,
            update=update,
            options=options,
            sort=sort
        )

        response = self._request(
            method=http_methods.POST,
            path=f"{self.base_path}",
            json_data=json_query,
        )

        return response

    def find_one(self, filter={}, projection={}, sort={}, options={}):
        json_query = make_payload(
            top_level="findOne",
            filter=filter,
            projection=projection,
            options=options,
            sort=sort
        )

        response = self._request(
            method=http_methods.POST,
            path=f"{self.base_path}",
            json_data=json_query,
        )

        return response

    def insert_one(self, document):
        json_query = make_payload(
            top_level="insertOne",
            document=document
        )

        response = self._request(
            method=http_methods.POST, path=self.base_path, json_data=json_query
        )
        
        return response
    
    def insert_many(self, documents):
        json_query = make_payload(
            top_level="insertMany",
            documents=documents
        )

        return self._request(
            method=http_methods.POST,
            path=f"{self.base_path}",
            json_data=json_query,
        )

    def update_one(self, filter, update):
        json_query = make_payload(
            top_level="updateOne",
            filter=filter,
            update=update
        )

        return self._request(
            method=http_methods.POST,
            path=f"{self.base_path}",
            json_data=json_query,
        )

    def replace(self, path, document):
        return self._put(path=path, document=document)

    def delete(self, id):
        return self._request(
            method=http_methods.POST,
            path=f"{self.base_path}",
            json_data={"deleteOne": {"filter": {"_id": id}}},
        )

    def delete_subdocument(self, id, subdoc):
        json_query = {
            "findOneAndUpdate": {
                "filter": {"_id": id},
                "update": {"$unset": {subdoc: ""}},
            }
        }

        return self._request(
            method=http_methods.POST, path=f"{self.base_path}", json_data=json_query
        )


class AstraDB:
    def __init__(
        self,
        db_id=None,
        token=None,
        db_region=None,
        namespace=None,
    ):
        if db_id is None or token is None:
            raise AssertionError("Must provide db_id and token")
        
        if namespace is None:
            logger.info(f"ASTRA_DB_KEYSPACE is not set. Defaulting to '{DEFAULT_KEYSPACE_NAME}'")
            namespace = DEFAULT_KEYSPACE_NAME
        
        # Store the initial parameters
        self.db_id = db_id
        self.token = token
        
        # Handle the region parameter
        if not db_region:
            db_region = AstraDBOps(token=token).get_database(db_id)["info"]["region"]
        self.db_region = db_region

        # Set the Base URL for the API calls
        self.base_url = f"https://{db_id}-{db_region}.apps.astra.datastax.com"
        self.base_path = f"{DEFAULT_BASE_PATH}/{namespace}"

        # Set the namespace parameter
        self.namespace = namespace


    def _request(self, *args, **kwargs):
        result = make_request(
            *args,
            **kwargs,
            base_url=self.base_url,
            auth_header=DEFAULT_AUTH_HEADER,
            token=self.token,
        )

        return result


    def collection(self, collection_name):
        return AstraDBCollection(
            collection_name=collection_name,
            astra_db=self
        )

    def get_collections(self):
        res = self._request(
            method=http_methods.POST,
            path=self.base_path,
            json_data={"findCollections": {}},
        )
        return res

    def create_collection(self, size=None, options={}, function="", collection_name=""):
        if size and not options:
            options = {"vector": {"size": size}}
            if function:
                options["vector"]["function"] = function
        if options:
            jsondata = {"name": collection_name, "options": options}
        else:
            jsondata = {"name": collection_name}
        return self._request(
            method=http_methods.POST,
            path=f"{self.base_path}",
            json_data={"createCollection": jsondata},
        )

    def delete_collection(self, collection_name=""):
        return self._request(
            method=http_methods.POST,
            path=f"{self.base_path}",
            json_data={"deleteCollection": {"name": collection_name}},
        )
