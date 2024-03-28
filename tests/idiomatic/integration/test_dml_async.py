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

import datetime

from typing import Any, Dict, List

import pytest

from astrapy import AsyncCollection
from astrapy.results import DeleteResult, InsertOneResult
from astrapy.exceptions import InsertManyException
from astrapy.constants import DocumentType, ReturnDocument, SortDocuments
from astrapy.cursors import AsyncCursor
from astrapy.operations import (
    AsyncInsertOne,
    AsyncInsertMany,
    AsyncUpdateOne,
    AsyncUpdateMany,
    AsyncReplaceOne,
    AsyncDeleteOne,
    AsyncDeleteMany,
)
from astrapy.ids import ObjectId, UUID


class TestDMLAsync:
    @pytest.mark.describe("test of collection count_documents, async")
    async def test_collection_count_documents_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 0
        )
        await async_empty_collection.insert_one({"doc": 1, "group": "A"})
        await async_empty_collection.insert_one({"doc": 2, "group": "B"})
        await async_empty_collection.insert_one({"doc": 3, "group": "A"})
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 3
        )
        assert (
            await async_empty_collection.count_documents(
                filter={"group": "A"}, upper_bound=100
            )
            == 2
        )

    @pytest.mark.describe("test of overflowing collection count_documents, async")
    async def test_collection_overflowing_count_documents_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        await async_empty_collection.insert_many([{"a": i} for i in range(900)])
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=950)
            == 900
        )
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=2000)
            == 900
        )
        with pytest.raises(ValueError):
            await async_empty_collection.count_documents(
                filter={}, upper_bound=100
            ) == 900
        await async_empty_collection.insert_many([{"b": i} for i in range(200)])
        with pytest.raises(ValueError):
            assert await async_empty_collection.count_documents(
                filter={}, upper_bound=100
            )
        with pytest.raises(ValueError):
            assert await async_empty_collection.count_documents(
                filter={}, upper_bound=2000
            )

    @pytest.mark.describe("test of collection insert_one, async")
    async def test_collection_insert_one_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        io_result1 = await async_empty_collection.insert_one({"doc": 1, "group": "A"})
        assert isinstance(io_result1, InsertOneResult)
        io_result2 = await async_empty_collection.insert_one(
            {"_id": "xxx", "doc": 2, "group": "B"}
        )
        assert io_result2.inserted_id == "xxx"
        assert (
            await async_empty_collection.count_documents(
                filter={"group": "A"}, upper_bound=100
            )
            == 1
        )

    @pytest.mark.describe("test of collection insert_one with vector, async")
    async def test_collection_insert_one_vector_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        await async_empty_collection.insert_one({"tag": "v1"}, vector=[-1, -2])
        retrieved1 = await async_empty_collection.find_one({"tag": "v1"})
        assert retrieved1 is not None
        assert retrieved1["$vector"] == [-1, -2]

        await async_empty_collection.insert_one({"tag": "v2", "$vector": [-3, -4]})
        retrieved2 = await async_empty_collection.find_one({"tag": "v2"})
        assert retrieved2 is not None
        assert retrieved2["$vector"] == [-3, -4]

        with pytest.raises(ValueError):
            await async_empty_collection.insert_one(
                {"tag": "v3", "$vector": [-5, -6]},
                vector=[-5, -6],
            )

    @pytest.mark.describe("test of collection delete_one, async")
    async def test_collection_delete_one_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        await async_empty_collection.insert_one({"doc": 1, "group": "A"})
        await async_empty_collection.insert_one({"doc": 2, "group": "B"})
        await async_empty_collection.insert_one({"doc": 3, "group": "A"})
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 3
        )
        do_result1 = await async_empty_collection.delete_one({"group": "A"})
        assert isinstance(do_result1, DeleteResult)
        assert do_result1.deleted_count == 1
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 2
        )

        # test of sort
        await async_empty_collection.insert_many(
            [{"ts": 1, "seq": i} for i in [2, 0, 1]]
        )
        await async_empty_collection.delete_one({"ts": 1}, sort={"seq": 1})
        assert set(await async_empty_collection.distinct("seq", filter={"ts": 1})) == {
            1,
            2,
        }

    @pytest.mark.describe("test of collection delete_many, async")
    async def test_collection_delete_many_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        await async_empty_collection.insert_one({"doc": 1, "group": "A"})
        await async_empty_collection.insert_one({"doc": 2, "group": "B"})
        await async_empty_collection.insert_one({"doc": 3, "group": "A"})
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 3
        )
        do_result1 = await async_empty_collection.delete_many({"group": "A"})
        assert isinstance(do_result1, DeleteResult)
        assert do_result1.deleted_count == 2
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 1
        )
        with pytest.raises(ValueError):
            await async_empty_collection.delete_many(filter={})

        await async_empty_collection.delete_all()
        await async_empty_collection.insert_many([{"a": 1} for _ in range(50)])
        do_result2 = await async_empty_collection.delete_many({"a": 1})
        assert do_result2.deleted_count == 50
        assert await async_empty_collection.count_documents({}, upper_bound=100) == 0
        with pytest.raises(ValueError):
            await async_empty_collection.delete_many(filter={})

        await async_empty_collection.delete_all()
        await async_empty_collection.insert_many([{"a": 1} for _ in range(50)])
        do_result2 = await async_empty_collection.delete_many({"a": 1})
        assert do_result2.deleted_count == 50
        assert await async_empty_collection.count_documents({}, upper_bound=100) == 0

    @pytest.mark.describe("test of collection delete_all, async")
    async def test_collection_delete_all_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        await async_empty_collection.insert_many([{"a": 1}, {"a": 2}, {"a": 3}])
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 3
        )
        await async_empty_collection.delete_all()
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 0
        )

    @pytest.mark.describe("test of collection chunk-requiring delete_many, async")
    async def test_collection_chunked_delete_many_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        await async_empty_collection.insert_many(
            [{"doc": i, "group": "A"} for i in range(50)]
        )
        await async_empty_collection.insert_many(
            [{"doc": i, "group": "B"} for i in range(10)]
        )
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
        ) == 60
        do_result1 = await async_empty_collection.delete_many({"group": "A"})
        assert isinstance(do_result1, DeleteResult)
        assert do_result1.deleted_count == 50
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
        ) == 10

    @pytest.mark.describe("test of collection find, async")
    async def test_collection_find_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        await async_empty_collection.insert_many([{"seq": i} for i in range(30)])
        Nski = 1
        Nlim = 28
        Nsor = {"seq": SortDocuments.DESCENDING}
        Nfil = {"seq": {"$exists": True}}

        async def _alist(acursor: AsyncCursor) -> List[DocumentType]:
            return [doc async for doc in acursor]

        # case 0000 of find-pattern matrix
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=None, limit=None, sort=None, filter=None
                    )
                )
            )
            == 30
        )

        # case 0001
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=None, limit=None, sort=None, filter=Nfil
                    )
                )
            )
            == 30
        )

        # case 0010
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=None, limit=None, sort=Nsor, filter=None
                    )
                )
            )
            == 20
        )  # NONPAGINATED

        # case 0011
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=None, limit=None, sort=Nsor, filter=Nfil
                    )
                )
            )
            == 20
        )  # NONPAGINATED

        # case 0100
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=None, limit=Nlim, sort=None, filter=None
                    )
                )
            )
            == 28
        )

        # case 0101
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=None, limit=Nlim, sort=None, filter=Nfil
                    )
                )
            )
            == 28
        )

        # case 0110
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=None, limit=Nlim, sort=Nsor, filter=None
                    )
                )
            )
            == 20
        )  # NONPAGINATED

        # case 0111
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=None, limit=Nlim, sort=Nsor, filter=Nfil
                    )
                )
            )
            == 20
        )  # NONPAGINATED

        # case 1000
        # len(list(async_empty_collection.find(skip=Nski, limit=None, sort=None, filter=None)))

        # case 1001
        # len(list(async_empty_collection.find(skip=Nski, limit=None, sort=None, filter=Nfil)))

        # case 1010
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=Nski, limit=None, sort=Nsor, filter=None
                    )
                )
            )
            == 20
        )  # NONPAGINATED

        # case 1011
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=Nski, limit=None, sort=Nsor, filter=Nfil
                    )
                )
            )
            == 20
        )  # NONPAGINATED

        # case 1100
        # len(list(async_empty_collection.find(skip=Nski, limit=Nlim, sort=None, filter=None)))

        # case 1101
        # len(list(async_empty_collection.find(skip=Nski, limit=Nlim, sort=None, filter=Nfil)))

        # case 1110
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=Nski, limit=Nlim, sort=Nsor, filter=None
                    )
                )
            )
            == 20
        )  # NONPAGINATED

        # case 1111
        assert (
            len(
                await _alist(
                    async_empty_collection.find(
                        skip=Nski, limit=Nlim, sort=Nsor, filter=Nfil
                    )
                )
            )
            == 20
        )  # NONPAGINATED

    @pytest.mark.describe("test of cursors from collection.find, async")
    async def test_collection_cursors_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        """
        Functionalities of cursors from find, other than the various
        combinations of skip/limit/sort/filter specified above.
        """
        await async_empty_collection.insert_many(
            [{"seq": i, "ternary": (i % 3)} for i in range(10)]
        )

        # projection
        cursor0 = async_empty_collection.find(projection={"ternary": False})
        document0 = await cursor0.__anext__()
        assert "ternary" not in document0
        cursor0b = async_empty_collection.find(projection={"ternary": True})
        document0b = await cursor0b.__anext__()
        assert "ternary" in document0b

        async def _alist(acursor: AsyncCursor) -> List[DocumentType]:
            return [doc async for doc in acursor]

        # rewinding, slicing and retrieved
        cursor1 = async_empty_collection.find(sort={"seq": 1})
        await cursor1.__anext__()
        await cursor1.__anext__()
        items1 = (await _alist(cursor1))[:2]  # noqa: F841
        assert await _alist(cursor1.rewind()) == await _alist(
            async_empty_collection.find(sort={"seq": 1})
        )
        cursor1.rewind()

        # Note: this, i.e. cursor[i]/cursor[i:j], is disabled
        # pending full skip/limit support by the Data API.
        # # slice indexing of cursor
        # cursor1.rewind()
        # assert items1 == await _alist(cursor1[2:4])  # type: ignore[arg-type]
        # assert cursor1.retrieved == 2

        # address, cursor_id, collection
        assert cursor1.address == async_empty_collection._astra_db_collection.base_path
        assert isinstance(cursor1.cursor_id, int)
        assert cursor1.collection == async_empty_collection

        # clone, alive
        cursor2 = async_empty_collection.find()
        assert cursor2.alive is True
        for _ in range(8):
            await cursor2.__anext__()
        assert cursor2.alive is True
        cursor3 = cursor2.clone()
        assert len(await _alist(cursor2)) == 2
        assert len(await _alist(cursor3)) == 10
        assert cursor2.alive is False

        # close
        cursor4 = async_empty_collection.find()
        for _ in range(8):
            await cursor4.__anext__()
        cursor4.close()
        assert cursor4.alive is False
        with pytest.raises(StopAsyncIteration):
            await cursor4.__anext__()

        # distinct
        cursor5 = async_empty_collection.find()
        dist5 = await cursor5.distinct("ternary")
        assert (len(await _alist(cursor5))) == 10
        assert set(dist5) == {0, 1, 2}
        cursor6 = async_empty_collection.find()
        for _ in range(9):
            await cursor6.__anext__()
        dist6 = await cursor6.distinct("ternary")
        assert (len(await _alist(cursor6))) == 1
        assert set(dist6) == {0, 1, 2}

        # distinct from collections
        assert set(await async_empty_collection.distinct("ternary")) == {0, 1, 2}
        assert set(await async_empty_collection.distinct("nonfield")) == set()

        # Note: this, i.e. cursor[i]/cursor[i:j], is disabled
        # pending full skip/limit support by the Data API.
        # # indexing by integer
        # cursor7 = async_empty_collection.find(sort={"seq": 1})
        # assert cursor7[5]["seq"] == 5

        # # indexing by wrong type
        # with pytest.raises(TypeError):
        #     cursor7.rewind()
        #     cursor7["wrong"]

    @pytest.mark.describe("test of distinct with non-hashable items, async")
    async def test_collection_distinct_nonhashable_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection
        documents: List[Dict[str, Any]] = [
            {},
            {"f": 1},
            {"f": "a"},
            {"f": {"subf": 99}},
            {"f": {"subf": 99, "another": {"subsubf": [True, False]}}},
            {"f": [10, 11]},
            {"f": [11, 10]},
            {"f": [10]},
            {"f": datetime.datetime(2000, 1, 1, 12, 00, 00)},
            {"f": None},
        ]
        await acol.insert_many(documents * 2)

        d_items = await acol.distinct("f")
        expected = [
            1,
            "a",
            {"subf": 99},
            {"subf": 99, "another": {"subsubf": [True, False]}},
            10,
            11,
            datetime.datetime(2000, 1, 1, 12, 0),
            None,
        ]
        assert len(d_items) == len(expected)
        for doc in documents:
            if "f" in doc:
                if isinstance(doc["f"], list):
                    for item in doc["f"]:
                        assert item in d_items
                else:
                    assert doc["f"] in d_items

    @pytest.mark.describe("test of usage of projection in distinct, async")
    async def test_collection_projections_distinct_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection
        await acol.insert_one({"x": [{"y": "Y", "0": "ZERO"}]})

        assert await acol.distinct("x.y") == ["Y"]
        # the one below shows that if index-in-list, then browse-whole-list is off
        assert await acol.distinct("x.0") == [{"y": "Y", "0": "ZERO"}]
        assert await acol.distinct("x.0.y") == ["Y"]
        assert await acol.distinct("x.0.0") == ["ZERO"]

    @pytest.mark.describe("test of unacceptable paths for distinct, async")
    async def test_collection_wrong_paths_distinc_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        with pytest.raises(ValueError):
            await async_empty_collection.distinct("root.1..subf")
        with pytest.raises(ValueError):
            await async_empty_collection.distinct("root..1.subf")
        with pytest.raises(ValueError):
            await async_empty_collection.distinct("root..subf.subsubf")
        with pytest.raises(ValueError):
            await async_empty_collection.distinct("root.subf..subsubf")

    @pytest.mark.describe("test of collection find with vectors, async")
    async def test_collection_find_find_one_vectors_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        q_vector = [3, 3]
        await async_empty_collection.insert_many(
            [
                {"tag": "A", "$vector": [4, 5]},
                {"tag": "B", "$vector": [3, 4]},
                {"tag": "C", "$vector": [3, 2]},
                {"tag": "D", "$vector": [4, 1]},
                {"tag": "E", "$vector": [2, 5]},
            ]
        )

        hits = [
            hit
            async for hit in async_empty_collection.find(
                {},
                projection=["tag"],
                limit=3,
                vector=q_vector,
            )
        ]
        assert [hit["tag"] for hit in hits] == ["A", "B", "C"]

        with pytest.raises(ValueError):
            await async_empty_collection.find(
                {},
                projection=["tag"],
                limit=3,
                vector=q_vector,
                sort={"tag": SortDocuments.DESCENDING},
            ).distinct("tag")

        top_doc = await async_empty_collection.find_one({}, vector=[1, 0])
        assert top_doc is not None
        assert top_doc["tag"] == "D"

        fdoc_no_s = await async_empty_collection.find(
            {}, vector=[1, 1], include_similarity=False
        ).__anext__()
        fdoc_wi_s = await async_empty_collection.find(
            {}, vector=[1, 1], include_similarity=True
        ).__anext__()
        assert fdoc_no_s is not None
        assert fdoc_wi_s is not None
        assert "$similarity" not in fdoc_no_s
        assert "$similarity" in fdoc_wi_s
        assert fdoc_wi_s["$similarity"] > 0.0

        f1doc_no_s = await async_empty_collection.find_one(
            {}, vector=[1, 1], include_similarity=False
        )
        f1doc_wi_s = await async_empty_collection.find_one(
            {}, vector=[1, 1], include_similarity=True
        )
        assert f1doc_no_s is not None
        assert f1doc_wi_s is not None
        assert "$similarity" not in f1doc_no_s
        assert "$similarity" in f1doc_wi_s
        assert f1doc_wi_s["$similarity"] > 0.0

        with pytest.raises(ValueError):
            async_empty_collection.find({}, include_similarity=True).distinct("x")

        with pytest.raises(ValueError):
            await async_empty_collection.find_one({}, include_similarity=True)

    @pytest.mark.describe("test of collection insert_many, async")
    async def test_collection_insert_many_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection

        ins_result1 = await acol.insert_many([{"_id": "a"}, {"_id": "b"}])
        assert set(ins_result1.inserted_ids) == {"a", "b"}
        assert {doc["_id"] async for doc in acol.find()} == {"a", "b"}

        with pytest.raises(InsertManyException):
            await acol.insert_many([{"_id": "a"}, {"_id": "c"}])
        assert {doc["_id"] async for doc in acol.find()} == {"a", "b"}

        with pytest.raises(InsertManyException):
            await acol.insert_many([{"_id": "c"}, {"_id": "a"}, {"_id": "d"}])
        assert {doc["_id"] async for doc in acol.find()} == {"a", "b", "c"}

        with pytest.raises(InsertManyException):
            await acol.insert_many(
                [{"_id": "c"}, {"_id": "d"}, {"_id": "e"}],
                ordered=False,
            )
        assert {doc["_id"] async for doc in acol.find()} == {"a", "b", "c", "d", "e"}

    @pytest.mark.describe("test of collection insert_many with vectors, async")
    async def test_collection_insert_many_vectors_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection
        await acol.insert_many([{"t": 0}, {"t": 1}], vectors=[[0, 1], [1, 0]])
        await acol.insert_many(
            [{"t": 2, "$vector": [0, 2]}, {"t": 3}], vectors=[None, [2, 0]]
        )
        await acol.insert_many(
            [{"t": 4, "$vector": [0, 3]}, {"t": 5, "$vector": [3, 0]}],
            vectors=[None, None],
        )

        vectors = [doc["$vector"] async for doc in acol.find({})]
        assert all(len(vec) == 2 for vec in vectors)

        with pytest.raises(ValueError):
            await acol.insert_many(
                [{"t": "z1"}, {"t": "z2"}, {"t": "z3"}], vectors=[None, None]
            )

        with pytest.raises(ValueError):
            await acol.insert_many([{"t": "z4", "$vector": [2, 2]}], vectors=[[1, 1]])

    @pytest.mark.describe("test of collection find_one, async")
    async def test_collection_find_one_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        col = async_empty_collection
        await col.insert_many(
            [
                {"_id": "?", "seq": 0, "kind": "punctuation"},
                {"_id": "a", "seq": 1, "kind": "letter"},
                {"_id": "b", "seq": 2, "kind": "letter"},
            ]
        )

        fo1 = await col.find_one({"kind": "frog"})
        assert fo1 is None

        Nsor = {"seq": 1}
        Nfil = {"kind": "letter"}

        # case 00 of find-pattern matrix
        doc00 = await col.find_one(sort=None, filter=None)
        assert doc00 is not None
        assert doc00["seq"] in {0, 1, 2}

        # case 01
        doc01 = await col.find_one(sort=None, filter=Nfil)
        assert doc01 is not None
        assert doc01["seq"] in {1, 2}

        # case 10
        doc10 = await col.find_one(sort=Nsor, filter=None)
        assert doc10 is not None
        assert doc10["seq"] == 0

        # case 11
        doc11 = await col.find_one(sort=Nsor, filter=Nfil)
        assert doc11 is not None
        assert doc11["seq"] == 1

        # projection
        doc_full = await col.find_one(sort=Nsor, filter=Nfil)
        doc_proj = await col.find_one(sort=Nsor, filter=Nfil, projection={"kind": True})
        assert doc_proj == {"_id": "a", "kind": "letter"}
        assert doc_full == {"_id": "a", "seq": 1, "kind": "letter"}

    @pytest.mark.describe("test of find_one_and_replace, async")
    async def test_collection_find_one_and_replace_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection

        resp0000 = await acol.find_one_and_replace({"f": 0}, {"r": 1})
        assert resp0000 is None
        assert await acol.count_documents({}, upper_bound=100) == 0

        resp0001 = await acol.find_one_and_replace({"f": 0}, {"r": 1}, sort={"x": 1})
        assert resp0001 is None
        assert await acol.count_documents({}, upper_bound=100) == 0

        resp0010 = await acol.find_one_and_replace({"f": 0}, {"r": 1}, upsert=True)
        assert resp0010 is None
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        resp0011 = await acol.find_one_and_replace(
            {"f": 0}, {"r": 1}, upsert=True, sort={"x": 1}
        )
        assert resp0011 is None
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp0100 = await acol.find_one_and_replace({"f": 0}, {"r": 1})
        assert resp0100 is not None
        assert resp0100["f"] == 0
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp0101 = await acol.find_one_and_replace({"f": 0}, {"r": 1}, sort={"x": 1})
        assert resp0101 is not None
        assert resp0101["f"] == 0
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp0110 = await acol.find_one_and_replace({"f": 0}, {"r": 1}, upsert=True)
        assert resp0110 is not None
        assert resp0110["f"] == 0
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp0111 = await acol.find_one_and_replace(
            {"f": 0}, {"r": 1}, upsert=True, sort={"x": 1}
        )
        assert resp0111 is not None
        assert resp0111["f"] == 0
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        resp1000 = await acol.find_one_and_replace(
            {"f": 0}, {"r": 1}, return_document=ReturnDocument.AFTER
        )
        assert resp1000 is None
        assert await acol.count_documents({}, upper_bound=100) == 0

        resp1001 = await acol.find_one_and_replace(
            {"f": 0}, {"r": 1}, sort={"x": 1}, return_document=ReturnDocument.AFTER
        )
        assert resp1001 is None
        assert await acol.count_documents({}, upper_bound=100) == 0

        resp1010 = await acol.find_one_and_replace(
            {"f": 0}, {"r": 1}, upsert=True, return_document=ReturnDocument.AFTER
        )
        assert resp1010 is not None
        assert resp1010["r"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        resp1011 = await acol.find_one_and_replace(
            {"f": 0},
            {"r": 1},
            upsert=True,
            sort={"x": 1},
            return_document=ReturnDocument.AFTER,
        )
        assert resp1011 is not None
        assert resp1011["r"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp1100 = await acol.find_one_and_replace(
            {"f": 0}, {"r": 1}, return_document=ReturnDocument.AFTER
        )
        assert resp1100 is not None
        assert resp1100["r"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp1101 = await acol.find_one_and_replace(
            {"f": 0}, {"r": 1}, sort={"x": 1}, return_document=ReturnDocument.AFTER
        )
        assert resp1101 is not None
        assert resp1101["r"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp1110 = await acol.find_one_and_replace(
            {"f": 0}, {"r": 1}, upsert=True, return_document=ReturnDocument.AFTER
        )
        assert resp1110 is not None
        assert resp1110["r"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp1111 = await acol.find_one_and_replace(
            {"f": 0},
            {"r": 1},
            upsert=True,
            sort={"x": 1},
            return_document=ReturnDocument.AFTER,
        )
        assert resp1111 is not None
        assert resp1111["r"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        # projection
        await acol.insert_one({"f": 100, "name": "apple", "mode": "old"})
        resp_pr1 = await acol.find_one_and_replace(
            {"f": 100},
            {"f": 100, "name": "carrot", "mode": "replaced"},
            projection=["mode"],
            return_document=ReturnDocument.AFTER,
        )
        assert resp_pr1 is not None
        assert set(resp_pr1.keys()) == {"_id", "mode"}
        resp_pr2 = await acol.find_one_and_replace(
            {"f": 100},
            {"f": 100, "name": "turnip", "mode": "re-replaced"},
            projection={"name": False, "f": False, "_id": False},
            return_document=ReturnDocument.BEFORE,
        )
        assert resp_pr2 is not None
        assert set(resp_pr2.keys()) == {"mode"}
        await acol.delete_all()

    @pytest.mark.describe("test of replace_one, async")
    async def test_collection_replace_one_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection

        result1 = await acol.replace_one(filter={"a": 1}, replacement={"b": 2})
        assert result1.update_info["n"] == 0
        assert result1.update_info["updatedExisting"] is False
        assert result1.update_info["nModified"] == 0
        assert "upserted" not in result1.update_info

        result2 = await acol.replace_one(
            filter={"a": 1}, replacement={"b": 2}, upsert=True
        )
        assert result2.update_info["n"] == 1
        assert result2.update_info["updatedExisting"] is False
        assert result2.update_info["nModified"] == 0
        assert "upserted" in result2.update_info

        result3 = await acol.replace_one(filter={"b": 2}, replacement={"c": 3})
        assert result3.update_info["n"] == 1
        assert result3.update_info["updatedExisting"] is True
        assert result3.update_info["nModified"] == 1
        assert "upserted" not in result3.update_info

        result4 = await acol.replace_one(
            filter={"c": 3}, replacement={"d": 4}, upsert=True
        )
        assert result4.update_info["n"] == 1
        assert result4.update_info["updatedExisting"] is True
        assert result4.update_info["nModified"] == 1
        assert "upserted" not in result4.update_info

        # test of sort
        await async_empty_collection.insert_many(
            [{"ts": 1, "seq": i} for i in [2, 0, 1]]
        )
        await async_empty_collection.replace_one(
            {"ts": 1}, {"ts": 1, "R": True}, sort={"seq": 1}
        )
        assert set(await async_empty_collection.distinct("seq", filter={"ts": 1})) == {
            1,
            2,
        }

    @pytest.mark.describe("test of replace_one with vectors, async")
    async def test_collection_replace_one_vector_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection
        await acol.insert_many(
            [
                {"tag": "h", "$vector": [10, 5]},
                {"tag": "v", "$vector": [2, 20]},
            ]
        )
        result = await acol.replace_one({}, {"new_doc": True}, vector=[0, 1])
        assert result.update_info["updatedExisting"]

        assert (await acol.find_one({"tag": "h"})) is not None

    @pytest.mark.describe("test of update_one, async")
    async def test_collection_update_one_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection

        result1 = await acol.update_one(filter={"a": 1}, update={"$set": {"b": 2}})
        assert result1.update_info["n"] == 0
        assert result1.update_info["updatedExisting"] is False
        assert result1.update_info["nModified"] == 0
        assert "upserted" not in result1.update_info

        result2 = await acol.update_one(
            filter={"a": 1}, update={"$set": {"b": 2}}, upsert=True
        )
        assert result2.update_info["n"] == 1
        assert result2.update_info["updatedExisting"] is False
        assert result2.update_info["nModified"] == 0
        assert "upserted" in result2.update_info

        result3 = await acol.update_one(filter={"b": 2}, update={"$set": {"c": 3}})
        assert result3.update_info["n"] == 1
        assert result3.update_info["updatedExisting"] is True
        assert result3.update_info["nModified"] == 1
        assert "upserted" not in result3.update_info

        result4 = await acol.update_one(
            filter={"c": 3}, update={"$set": {"d": 4}}, upsert=True
        )
        assert result4.update_info["n"] == 1
        assert result4.update_info["updatedExisting"] is True
        assert result4.update_info["nModified"] == 1
        assert "upserted" not in result4.update_info

        # test of sort
        await async_empty_collection.insert_many(
            [{"ts": 1, "seq": i} for i in [2, 0, 1]]
        )
        await async_empty_collection.update_one(
            {"ts": 1}, {"$set": {"U": True}}, sort={"seq": 1}
        )
        updated = await async_empty_collection.find_one({"U": True})
        assert updated is not None
        assert updated["seq"] == 0

    @pytest.mark.describe("test of update_many, async")
    async def test_collection_update_many_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection
        await acol.insert_many([{"a": 1, "seq": i} for i in range(4)])
        await acol.insert_many([{"a": 2, "seq": i} for i in range(2)])

        resp1 = await acol.update_many({"a": 1}, {"$set": {"n": 1}})
        assert resp1.update_info["n"] == 4
        assert resp1.update_info["updatedExisting"] is True
        assert resp1.update_info["nModified"] == 4
        assert "upserted" not in resp1.update_info

        resp2 = await acol.update_many({"a": 1}, {"$set": {"n": 2}}, upsert=True)
        assert resp2.update_info["n"] == 4
        assert resp2.update_info["updatedExisting"] is True
        assert resp2.update_info["nModified"] == 4
        assert "upserted" not in resp2.update_info

        resp3 = await acol.update_many({"a": 3}, {"$set": {"n": 3}})
        assert resp3.update_info["n"] == 0
        assert resp3.update_info["updatedExisting"] is False
        assert resp3.update_info["nModified"] == 0
        assert "upserted" not in resp3.update_info

        resp4 = await acol.update_many({"a": 3}, {"$set": {"n": 4}}, upsert=True)
        assert resp4.update_info["n"] == 1
        assert resp4.update_info["updatedExisting"] is False
        assert resp4.update_info["nModified"] == 0
        assert "upserted" in resp4.update_info

    @pytest.mark.describe("test of update_many, async")
    async def test_collection_paginated_update_many_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection
        await acol.insert_many([{"a": 1} for _ in range(50)])
        await acol.insert_many([{"a": 10} for _ in range(10)])

        um_result = await acol.update_many({"a": 1}, {"$set": {"b": 2}})
        assert um_result.update_info["n"] == 50
        assert um_result.update_info["updatedExisting"] is True
        assert um_result.update_info["nModified"] == 50
        assert "upserted" not in um_result.update_info
        assert "upsertedd" not in um_result.update_info
        assert await acol.count_documents({"b": 2}, upper_bound=100) == 50
        assert await acol.count_documents({}, upper_bound=100) == 60

    @pytest.mark.describe("test of collection find_one_and_delete, async")
    async def test_collection_find_one_and_delete_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        await async_empty_collection.insert_one({"doc": 1, "group": "A"})
        await async_empty_collection.insert_one({"doc": 2, "group": "B"})
        await async_empty_collection.insert_one({"doc": 3, "group": "A"})
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 3
        )

        fo_result1 = await async_empty_collection.find_one_and_delete({"group": "A"})
        assert fo_result1 is not None
        assert set(fo_result1.keys()) == {"_id", "doc", "group"}
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 2
        )

        fo_result2 = await async_empty_collection.find_one_and_delete(
            {"group": "B"}, projection=["doc"]
        )
        assert fo_result2 is not None
        assert set(fo_result2.keys()) == {"_id", "doc"}
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 1
        )

        fo_result3 = await async_empty_collection.find_one_and_delete(
            {"group": "A"}, projection={"_id": False, "group": False}
        )
        assert fo_result3 is not None
        assert set(fo_result3.keys()) == {"doc"}
        assert (
            await async_empty_collection.count_documents(filter={}, upper_bound=100)
            == 0
        )

        fo_result4 = await async_empty_collection.find_one_and_delete({}, sort={"f": 1})
        assert fo_result4 is None

    @pytest.mark.describe("test of collection find_one_and_delete with vectors, async")
    async def test_collection_find_one_and_delete_vectors_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection
        await acol.insert_many(
            [
                {"tag": "h", "$vector": [10, 5]},
                {"tag": "v", "$vector": [2, 20]},
            ]
        )
        deleted = await acol.find_one_and_delete({}, vector=[0, 1])
        assert deleted is not None
        assert deleted["tag"] == "v"

    @pytest.mark.describe("test of find_one_and_update, async")
    async def test_collection_find_one_and_update_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection

        resp0000 = await acol.find_one_and_update({"f": 0}, {"$set": {"n": 1}})
        assert resp0000 is None
        assert await acol.count_documents({}, upper_bound=100) == 0

        resp0001 = await acol.find_one_and_update(
            {"f": 0}, {"$set": {"n": 1}}, sort={"x": 1}
        )
        assert resp0001 is None
        assert await acol.count_documents({}, upper_bound=100) == 0

        resp0010 = await acol.find_one_and_update(
            {"f": 0}, {"$set": {"n": 1}}, upsert=True
        )
        assert resp0010 is None
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        resp0011 = await acol.find_one_and_update(
            {"f": 0}, {"$set": {"n": 1}}, upsert=True, sort={"x": 1}
        )
        assert resp0011 is None
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp0100 = await acol.find_one_and_update({"f": 0}, {"$set": {"n": 1}})
        assert resp0100 is not None
        assert resp0100["f"] == 0
        assert "n" not in resp0100
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp0101 = await acol.find_one_and_update(
            {"f": 0}, {"$set": {"n": 1}}, sort={"x": 1}
        )
        assert resp0101 is not None
        assert resp0101["f"] == 0
        assert "n" not in resp0101
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp0110 = await acol.find_one_and_update(
            {"f": 0}, {"$set": {"n": 1}}, upsert=True
        )
        assert resp0110 is not None
        assert resp0110["f"] == 0
        assert "n" not in resp0110
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp0111 = await acol.find_one_and_update(
            {"f": 0}, {"$set": {"n": 1}}, upsert=True, sort={"x": 1}
        )
        assert resp0111 is not None
        assert resp0111["f"] == 0
        assert "n" not in resp0111
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        resp1000 = await acol.find_one_and_update(
            {"f": 0}, {"$set": {"n": 1}}, return_document=ReturnDocument.AFTER
        )
        assert resp1000 is None
        assert await acol.count_documents({}, upper_bound=100) == 0

        resp1001 = await acol.find_one_and_update(
            {"f": 0},
            {"$set": {"n": 1}},
            sort={"x": 1},
            return_document=ReturnDocument.AFTER,
        )
        assert resp1001 is None
        assert await acol.count_documents({}, upper_bound=100) == 0

        resp1010 = await acol.find_one_and_update(
            {"f": 0},
            {"$set": {"n": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        assert resp1010 is not None
        assert resp1010["n"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        resp1011 = await acol.find_one_and_update(
            {"f": 0},
            {"$set": {"n": 1}},
            upsert=True,
            sort={"x": 1},
            return_document=ReturnDocument.AFTER,
        )
        assert resp1011 is not None
        assert resp1011["n"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp1100 = await acol.find_one_and_update(
            {"f": 0}, {"$set": {"n": 1}}, return_document=ReturnDocument.AFTER
        )
        assert resp1100 is not None
        assert resp1100["n"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp1101 = await acol.find_one_and_update(
            {"f": 0},
            {"$set": {"n": 1}},
            sort={"x": 1},
            return_document=ReturnDocument.AFTER,
        )
        assert resp1101 is not None
        assert resp1101["n"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp1110 = await acol.find_one_and_update(
            {"f": 0},
            {"$set": {"n": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        assert resp1110 is not None
        assert resp1110["n"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        await acol.insert_one({"f": 0})
        resp1111 = await acol.find_one_and_update(
            {"f": 0},
            {"$set": {"n": 1}},
            upsert=True,
            sort={"x": 1},
            return_document=ReturnDocument.AFTER,
        )
        assert resp1111 is not None
        assert resp1111["n"] == 1
        assert await acol.count_documents({}, upper_bound=100) == 1
        await acol.delete_all()

        # projection
        await acol.insert_one({"f": 100, "name": "apple", "mode": "old"})
        resp_pr1 = await acol.find_one_and_update(
            {"f": 100},
            {"$unset": {"mode": ""}},
            projection=["mode", "f"],
            return_document=ReturnDocument.AFTER,
        )
        assert resp_pr1 is not None
        assert set(resp_pr1.keys()) == {"_id", "f"}
        resp_pr2 = await acol.find_one_and_update(
            {"f": 100},
            {"$set": {"mode": "re-replaced"}},
            projection={"name": False, "_id": False},
            return_document=ReturnDocument.BEFORE,
        )
        assert resp_pr2 is not None
        assert set(resp_pr2.keys()) == {"f"}
        await acol.delete_all()

    @pytest.mark.describe("test of vectorize in collection methods, async")
    async def test_collection_methods_vectorize_async(
        self,
        async_empty_service_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_service_collection

        await acol.insert_one({"t": "tower"}, vectorize="How high is this tower?")
        await acol.insert_one({"t": "vectorless"})
        await acol.insert_one({"t": "vectorful"}, vector=[0.01] * 1024)

        await acol.insert_many(
            [{"t": "guide"}, {"t": "seeds"}],
            vectorizes=[
                "This is the instructions manual. Read it!",
                "Other plants rely on wind to propagate their seeds.",
            ],
        )
        await acol.insert_many(
            [{"t": "dog"}, {"t": "cat_novector"}, {"t": "spider"}],
            vectorizes=[
                None,
                None,
                "The eye pattern is a primary criterion to the family.",
            ],
            vectors=[
                [0.01] * 1024,
                None,
                None,
            ],
        )

        doc = await acol.find_one(
            {},
            vectorize="This building is five storeys tall.",
            projection={"$vector": False},
        )
        assert doc is not None
        assert doc["t"] == "tower"

        docs = [
            doc
            async for doc in acol.find(
                {},
                vectorize="This building is five storeys tall.",
                limit=2,
                projection={"$vector": False},
            )
        ]
        assert docs[0]["t"] == "tower"

        rdoc = await acol.find_one_and_replace(
            {},
            {"t": "spider", "$vectorize": "Check out the eyes!"},
            vectorize="The disposition of the eyes tells much",
            projection={"$vector": False},
        )
        assert rdoc["t"] == "spider"

        r1res = await acol.replace_one(
            {},
            {"t": "spider", "$vectorize": "Look at how the eyes are placed"},
            vectorize="The disposition of the eyes tells much",
        )
        assert r1res.update_info["nModified"] == 1

        udoc = await acol.find_one_and_update(
            {},
            {"$set": {"$vectorize": "Consider consulting the how-to"}},
            vectorize="Have a look at the user guide...",
            projection={"$vector": False},
        )
        assert udoc["t"] == "guide"

        u1res = await acol.update_one(
            {},
            {"$set": {"$vectorize": "Know how to operate it before doing so."}},
            vectorize="Have a look at the user guide...",
        )
        assert u1res.update_info["nModified"] == 1

        ddoc = await acol.find_one_and_delete(
            {},
            vectorize="Some trees have seeds that are dispersed in the air!",
            projection={"$vector": False},
        )
        assert ddoc["t"] == "seeds"

        d1res = await acol.delete_one(
            {},
            vectorize="yet another giant construction in this suburb.",
        )
        assert d1res.deleted_count == 1

    @pytest.mark.describe("test of ordered bulk_write, async")
    async def test_collection_ordered_bulk_write_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection

        bw_ops = [
            AsyncInsertOne({"seq": 0}),
            AsyncInsertMany([{"seq": 1}, {"seq": 2}, {"seq": 3}]),
            AsyncUpdateOne({"seq": 0}, {"$set": {"edited": 1}}),
            AsyncUpdateMany({"seq": {"$gt": 0}}, {"$set": {"positive": True}}),
            AsyncReplaceOne({"edited": 1}, {"seq": 0, "edited": 2}),
            AsyncDeleteOne({"seq": 1}),
            AsyncDeleteMany({"seq": {"$gt": 1}}),
            AsyncReplaceOne(
                {"no": "matches"}, {"_id": "seq4", "from_upsert": True}, upsert=True
            ),
        ]

        bw_result = await acol.bulk_write(bw_ops)

        assert bw_result.deleted_count == 3
        assert bw_result.inserted_count == 5
        assert bw_result.matched_count == 5
        assert bw_result.modified_count == 5
        assert bw_result.upserted_count == 1
        assert set(bw_result.upserted_ids.keys()) == {7}

        found_docs = sorted(
            [doc async for doc in acol.find({})],
            key=lambda doc: doc.get("seq", 10),
        )
        assert len(found_docs) == 2
        assert found_docs[0]["seq"] == 0
        assert found_docs[0]["edited"] == 2
        assert "_id" in found_docs[0]
        assert len(found_docs[0]) == 3
        assert found_docs[1] == {"_id": "seq4", "from_upsert": True}

    @pytest.mark.describe("test of unordered bulk_write, async")
    async def test_collection_unordered_bulk_write_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection

        bw_u_ops = [
            AsyncInsertOne({"a": 1}),
            AsyncUpdateOne({"b": 1}, {"$set": {"newfield": True}}, upsert=True),
            AsyncDeleteMany({"x": 100}),
        ]

        bw_u_result = await acol.bulk_write(bw_u_ops, ordered=False, concurrency=4)

        assert bw_u_result.deleted_count == 0
        assert bw_u_result.inserted_count == 2
        assert bw_u_result.matched_count == 0
        assert bw_u_result.modified_count == 0
        assert bw_u_result.upserted_count == 1
        assert set(bw_u_result.upserted_ids.keys()) == {1}

        found_docs = [doc async for doc in acol.find({})]
        no_id_found_docs = [
            {k: v for k, v in doc.items() if k != "_id"} for doc in found_docs
        ]
        assert len(no_id_found_docs) == 2
        assert {"a": 1} in no_id_found_docs
        assert {"b": 1, "newfield": True} in no_id_found_docs

    @pytest.mark.describe("test of bulk_write with vectors, async")
    async def test_collection_bulk_write_vector_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        acol = async_empty_collection

        bw_ops = [
            AsyncInsertOne({"a": 1}, vector=[1, 1]),
            AsyncInsertMany([{"a": 2}, {"z": 0}], vectors=[[1, 10], [-1, 1]]),
            AsyncUpdateOne({}, {"$set": {"b": 1}}, vector=[1, 15]),
            AsyncReplaceOne({}, {"a": 10}, vector=[5, 6]),
            AsyncDeleteOne({}, vector=[-8, 7]),
        ]
        await acol.bulk_write(bw_ops)
        found = [
            {k: v for k, v in doc.items() if k != "_id"}
            async for doc in acol.find({}, projection=["a", "b"])
        ]
        assert len(found) == 2
        assert {"a": 10} in found
        assert {"a": 2, "b": 1} in found

    @pytest.mark.describe("test of the various ids in the document id field, async")
    async def test_collection_ids_as_doc_id_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        types_and_ids = {
            "uuid1": UUID("8ccd6ff8-e61b-11ee-a2fc-7df4a8c4164b"),
            "uuid3": UUID("6fa459ea-ee8a-3ca4-894e-db77e160355e"),
            "uuid4": UUID("4f16cba8-1115-43ab-aa39-3a9c29f37db5"),
            "uuid5": UUID("886313e1-3b8a-5372-9b90-0c9aee199e5d"),
            "uuid6": UUID("1eee61b9-8f2d-69ad-8ebb-5054d2a1a2c0"),
            "uuid7": UUID("018e57e5-f586-7ed6-be55-6b0de3041116"),
            "uuid8": UUID("018e57e5-fbcd-8bd4-b794-be914f2c4c85"),
            "objectid": ObjectId("65f9cfa0d7fabb3f255c25a1"),
        }

        await async_empty_collection.insert_many(
            [
                {"_id": t_id, "id_type": t_id_type}
                for t_id_type, t_id in types_and_ids.items()
            ]
        )

        for t_id_type, t_id in types_and_ids.items():
            this_doc = await async_empty_collection.find_one(
                {"_id": t_id},
                projection={"id_type": True},
            )
            assert this_doc is not None
            assert this_doc["id_type"] == t_id_type

    @pytest.mark.describe(
        "test of ids in various parameters of various DML methods, async"
    )
    async def test_collection_ids_throughout_dml_methods_async(
        self,
        async_empty_collection: AsyncCollection,
    ) -> None:
        types_and_ids = {
            "uuid1": UUID("8ccd6ff8-e61b-11ee-a2fc-7df4a8c4164b"),
            "uuid3": UUID("6fa459ea-ee8a-3ca4-894e-db77e160355e"),
            "uuid4": UUID("4f16cba8-1115-43ab-aa39-3a9c29f37db5"),
            "uuid5": UUID("886313e1-3b8a-5372-9b90-0c9aee199e5d"),
            "uuid6": UUID("1eee61b9-8f2d-69ad-8ebb-5054d2a1a2c0"),
            "uuid7": UUID("018e57e5-f586-7ed6-be55-6b0de3041116"),
            "uuid8": UUID("018e57e5-fbcd-8bd4-b794-be914f2c4c85"),
            "objectid": ObjectId("65f9cfa0d7fabb3f255c25a1"),
        }
        wide_document = {
            "all_ids": types_and_ids,
            "_id": 0,
            "name": "wide_document",
            "touched_times": 0,
        }
        await async_empty_collection.insert_one(wide_document)

        full_doc = await async_empty_collection.find_one({})
        assert full_doc == wide_document

        for t_id_type, t_id in types_and_ids.items():
            doc = await async_empty_collection.find_one(
                {f"all_ids.{t_id_type}": t_id}, projection={"name": True}
            )
            assert doc is not None
            assert doc["name"] == "wide_document"

        for upd_index, (t_id_type, t_id) in enumerate(types_and_ids.items()):
            updated_doc = await async_empty_collection.find_one_and_update(
                {f"all_ids.{t_id_type}": t_id},
                {"$inc": {"touched_times": 1}},
                return_document=ReturnDocument.AFTER,
            )
            assert updated_doc is not None
            assert updated_doc["touched_times"] == upd_index + 1

        await async_empty_collection.delete_one({"_id": 0})

        await async_empty_collection.insert_many(
            [{"_id": t_id} for t_id in types_and_ids.values()]
        )

        count = await async_empty_collection.count_documents({}, upper_bound=20)
        assert count == len(types_and_ids)

        for del_index, t_id in enumerate(types_and_ids.values()):
            del_result = await async_empty_collection.delete_one({"_id": t_id})
            assert del_result.deleted_count == 1
            count = await async_empty_collection.count_documents({}, upper_bound=20)
            assert count == len(types_and_ids) - del_index - 1
