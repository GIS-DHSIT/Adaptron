from adaptron.synthesize.detector import TrainingFormatDetector, FormatRecommendation
from adaptron.connectors.models import DataSchema, CollectionSchema, FieldInfo


def test_detect_qa_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="faq",
            fields=[
                FieldInfo(name="question", data_type="string"),
                FieldInfo(name="answer", data_type="string"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "qa"
    assert result.confidence >= 0.8


def test_detect_instruction_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="training",
            fields=[
                FieldInfo(name="instruction", data_type="string"),
                FieldInfo(name="response", data_type="string"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "instruction"


def test_detect_dpo_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="prefs",
            fields=[
                FieldInfo(name="prompt", data_type="string"),
                FieldInfo(name="chosen", data_type="string"),
                FieldInfo(name="rejected", data_type="string"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "dpo"


def test_detect_chat_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="mongodb", database="test",
        collections=[CollectionSchema(
            name="messages",
            fields=[
                FieldInfo(name="role", data_type="string"),
                FieldInfo(name="content", data_type="string"),
                FieldInfo(name="session_id", data_type="string"),
            ],
            source_type="collection",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "chat"


def test_detect_text2sql_complex_schema():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[
            CollectionSchema(name="users", fields=[
                FieldInfo(name="id", data_type="integer", is_primary_key=True),
                FieldInfo(name="name", data_type="string"),
            ], relationships=["orders.user_id -> users.id"], source_type="table"),
            CollectionSchema(name="orders", fields=[
                FieldInfo(name="id", data_type="integer", is_primary_key=True),
                FieldInfo(name="user_id", data_type="integer"),
                FieldInfo(name="total", data_type="float"),
            ], source_type="table"),
            CollectionSchema(name="products", fields=[
                FieldInfo(name="id", data_type="integer", is_primary_key=True),
                FieldInfo(name="name", data_type="string"),
                FieldInfo(name="price", data_type="float"),
            ], source_type="table"),
        ],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "text2sql"


def test_detect_corpus_format():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="articles",
            fields=[
                FieldInfo(name="id", data_type="integer", is_primary_key=True),
                FieldInfo(name="title", data_type="string"),
                FieldInfo(name="body", data_type="string"),
                FieldInfo(name="published_at", data_type="datetime"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert result.primary_format == "corpus"


def test_detect_low_confidence():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="redis", database="0",
        collections=[CollectionSchema(
            name="keys",
            fields=[FieldInfo(name="key", data_type="string"), FieldInfo(name="value", data_type="string")],
            source_type="keyspace",
        )],
    )
    result = detector.detect(schema, [])
    assert result.confidence < 0.8
    assert result.reasoning != ""


def test_format_recommendation_has_column_mapping():
    detector = TrainingFormatDetector()
    schema = DataSchema(
        connector_type="postgresql", database="test",
        collections=[CollectionSchema(
            name="faq",
            fields=[
                FieldInfo(name="question", data_type="string"),
                FieldInfo(name="answer", data_type="string"),
            ],
            source_type="table",
        )],
    )
    result = detector.detect(schema, [])
    assert "question" in result.column_mapping or "answer" in result.column_mapping
