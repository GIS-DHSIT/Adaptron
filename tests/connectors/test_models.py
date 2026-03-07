from adaptron.connectors.models import (
    ConnectorConfig,
    CredentialConfig,
    CollectionSchema,
    DataSchema,
    FetchQuery,
    FieldInfo,
)


def test_connector_config_defaults():
    cfg = ConnectorConfig(connector_type="postgres")
    assert cfg.connector_type == "postgres"
    assert cfg.connection_string is None
    assert cfg.host is None
    assert cfg.port is None
    assert cfg.database is None
    assert cfg.credentials is None
    assert cfg.options == {}


def test_credential_config_with_env_var():
    cred = CredentialConfig(env_var="DB_PASSWORD")
    assert cred.env_var == "DB_PASSWORD"
    assert cred.profile is None
    assert cred.aws_secret is None
    assert cred.azure_vault is None
    assert cred.username is None
    assert cred.password is None


def test_field_info_with_samples():
    fi = FieldInfo(name="age", data_type="integer", sample_values=[25, 30, 45])
    assert fi.name == "age"
    assert fi.data_type == "integer"
    assert fi.nullable is True
    assert fi.is_primary_key is False
    assert fi.sample_values == [25, 30, 45]


def test_collection_schema():
    f = FieldInfo(name="id", data_type="integer", is_primary_key=True)
    cs = CollectionSchema(name="users", fields=[f], source_type="table", row_count=100)
    assert cs.name == "users"
    assert len(cs.fields) == 1
    assert cs.fields[0].is_primary_key is True
    assert cs.row_count == 100
    assert cs.source_type == "table"
    assert cs.relationships == []


def test_data_schema():
    ds = DataSchema(connector_type="postgres", database="mydb")
    assert ds.connector_type == "postgres"
    assert ds.database == "mydb"
    assert ds.collections == []
    assert ds.metadata == {}


def test_fetch_query_defaults():
    fq = FetchQuery(collection="users")
    assert fq.collection == "users"
    assert fq.columns is None
    assert fq.filters is None
    assert fq.limit is None
    assert fq.offset == 0
    assert fq.raw_query is None
    assert fq.options == {}


def test_fetch_query_with_raw():
    fq = FetchQuery(collection="users", raw_query="SELECT * FROM users", limit=10)
    assert fq.raw_query == "SELECT * FROM users"
    assert fq.limit == 10
    assert fq.collection == "users"
