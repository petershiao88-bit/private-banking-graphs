"""Self-contained Fabric notebook helpers. Importing this file makes no cloud calls."""

import base64
from collections import Counter
import copy
import json
import re
import uuid
import zlib


def decode_bundle(packed):
    return json.loads(zlib.decompress(base64.b64decode(packed)).decode("utf-8"))


def validated_target(context, workspace_id, lakehouse_id):
    workspace_id, lakehouse_id = str(uuid.UUID(workspace_id)), str(uuid.UUID(lakehouse_id))
    if str(context.get("currentWorkspaceId", "")).lower() != workspace_id:
        raise ValueError("Notebook is not in the selected workspace")
    if str(context.get("defaultLakehouseId", "")).lower() != lakehouse_id:
        raise ValueError("Attach the selected Lakehouse as the notebook default")
    if str(context.get("defaultLakehouseWorkspaceId", "")).lower() != workspace_id:
        raise ValueError("Default Lakehouse must be in the selected workspace")
    return workspace_id, lakehouse_id


def materialize_parts(template, table_paths, workspace_id, lakehouse_id):
    workspace_id, lakehouse_id = str(uuid.UUID(workspace_id)), str(uuid.UUID(lakehouse_id))
    parts = copy.deepcopy(template)
    parts["dataSources.json"]["itemReferences"] = [{"name": "Customer360Lakehouse", "item": {
        "workspaceId": workspace_id, "itemId": lakehouse_id}}]
    parent = "abfss://" + workspace_id + "@onelake.dfs.fabric.microsoft.com/" + lakehouse_id + "/"
    for source in parts["dataSources.json"]["dataSources"]:
        path = source["properties"]["path"]
        match = re.fullmatch(r"\{\{TABLE_PATH:([a-z0-9_]+)\}\}", path)
        if not match or match[1] not in table_paths:
            raise ValueError("Unresolved Delta table path")
        absolute = table_paths[match[1]]
        if not absolute.lower().startswith(parent.lower()):
            raise ValueError("Graph source is outside the selected Lakehouse")
        relative = absolute[len(parent):]
        if not relative.startswith("Tables/") or ".." in relative.split("/"):
            raise ValueError("Graph source must be a Lakehouse table")
        # dataSources 1.1 uses item references and paths relative to that item.
        source["properties"]["path"] = relative
    return parts


def request_payload(parts, display_name):
    return {"displayName": display_name,
        "description": "Customer360 RDF schema + PG metadata; no business SQL execution or customer instances.",
        "definition": {"format": "json", "parts": [
            {"path": name, "payload": base64.b64encode(json.dumps(part, ensure_ascii=False).encode("utf-8")).decode("ascii"),
             "payloadType": "InlineBase64"} for name, part in sorted(parts.items())]}}


def prepare_tables(spark, context, bundle, workspace_id, lakehouse_id):
    from pyspark.sql.types import StringType, StructField, StructType

    workspace_id, lakehouse_id = validated_target(context, workspace_id, lakehouse_id)
    prefix = bundle["manifest"]["table_prefix"]
    if not re.fullmatch(r"c360_v[0-9_]+_[0-9a-f]{8}", prefix):
        raise ValueError("Unsafe table prefix")
    plans = []
    expected = "abfss://" + workspace_id + "@onelake.dfs.fabric.microsoft.com/" + lakehouse_id + "/"
    # Preflight ALL existing tables before the first mutation. Exact snapshots can resume.
    for table in bundle["tables"]:
        name = prefix + "_" + table["suffix"]
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise ValueError("Unsafe table name")
        exists = spark.catalog.tableExists(name)
        if exists:
            location = spark.sql("DESCRIBE DETAIL `" + name + "`").first().asDict()["location"]
            if not location.lower().startswith(expected.lower()):
                raise ValueError("Existing table is outside the selected Lakehouse: " + name)
            actual = spark.table(name)
            if actual.columns != table["columns"]:
                raise ValueError("Existing table schema differs: " + name)
            actual_rows = Counter(json.dumps(r.asDict(), sort_keys=True, ensure_ascii=False) for r in actual.collect())
            expected_rows = Counter(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in table["rows"])
            if actual_rows != expected_rows:
                raise ValueError("Existing table contents differ; refusing overwrite: " + name)
        plans.append((table, name, exists))
    paths = {}
    for table, name, exists in plans:
        if not exists:
            schema = StructType([StructField(c, StringType(), False) for c in table["columns"]])
            frame = spark.createDataFrame(table["rows"], schema)
            frame.coalesce(1).write.format("delta").mode("errorifexists").saveAsTable(name)
        detail = spark.sql("DESCRIBE DETAIL `" + name + "`").first().asDict()
        path = detail["location"]
        # Verify the physical location before using it in a Graph definition.
        if not path.lower().startswith(expected.lower()):
            raise ValueError("Table is outside the selected Lakehouse: " + name)
        paths[table["suffix"]] = path
        print(("Reused " if exists else "Created ") + name)
    return {"table_paths": paths, "parts": materialize_parts(bundle["parts"], paths, workspace_id, lakehouse_id),
            "display_name": "Customer360_Graph_v" + bundle["manifest"]["version"].replace(".", "_") + "_" +
                            bundle["manifest"]["content_sha256"][:8]}


def create_graph_model(notebookutils, prepared, workspace_id):
    import requests
    workspace_id = str(uuid.UUID(workspace_id))
    # Current user token stays in memory; no tokens in notebook outputs or bundle files.
    headers = {"Authorization": "Bearer " + notebookutils.credentials.getToken("pbi"),
               "Content-Type": "application/json"}
    root = "https://api.fabric.microsoft.com/v1/workspaces/" + workspace_id + "/graphModels"
    response = requests.get(root, headers=headers, timeout=60)
    response.raise_for_status()
    page = response.json()
    while True:
        if any(item["displayName"] == prepared["display_name"] for item in page.get("value", [])):
            raise ValueError("Graph model with this snapshot name already exists; open it in Fabric")
        continuation = page.get("continuationToken")
        if not continuation:
            break
        response = requests.get(root, headers=headers, params={"continuationToken": continuation}, timeout=60)
        response.raise_for_status()
        page = response.json()
    response = requests.post(root, headers=headers,
        json=request_payload(prepared["parts"], prepared["display_name"]), timeout=60)
    response.raise_for_status()
    if response.status_code == 202:
        return {"status": "creation_accepted_not_yet_complete", "operation_url": response.headers.get("Location"),
                "retry_after": response.headers.get("Retry-After"), "display_name": prepared["display_name"]}
    item = response.json()
    return {"status": "created_sync_and_query_verification_pending", "id": item.get("id"),
            "display_name": prepared["display_name"]}
