from sqlalchemy import Engine, inspect, text

from apps.persistence.models import Base


def run_migrations(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        _migrate_live_temporal_record_source(engine)


def _migrate_live_temporal_record_source(engine: Engine) -> None:
    columns = {
        column["name"] for column in inspect(engine).get_columns("temporal_records")
    }
    with engine.begin() as connection:
        if "stream_id" not in columns:
            connection.execute(
                text("ALTER TABLE temporal_records ADD COLUMN stream_id VARCHAR")
            )
        connection.execute(
            text("ALTER TABLE temporal_records ALTER COLUMN asset_id DROP NOT NULL")
        )
        connection.execute(
            text(
                """
                UPDATE temporal_records AS record
                SET stream_id = record.payload ->> 'stream_id',
                    asset_id = NULL
                WHERE (record.payload ->> 'stream_id') IS NOT NULL
                  AND EXISTS (
                      SELECT 1
                      FROM rt_streams AS stream
                      WHERE stream.id = record.payload ->> 'stream_id'
                  )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_temporal_records_stream_id
                ON temporal_records (stream_id)
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conrelid = 'temporal_records'::regclass
                          AND contype = 'f'
                          AND pg_get_constraintdef(oid)
                              LIKE 'FOREIGN KEY (stream_id)%'
                    ) THEN
                        ALTER TABLE temporal_records
                        ADD CONSTRAINT fk_temporal_records_stream_id
                        FOREIGN KEY (stream_id) REFERENCES rt_streams (id);
                    END IF;
                END
                $$
                """
            )
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conrelid = 'temporal_records'::regclass
                          AND conname =
                              'ck_temporal_records_exactly_one_source'
                    ) THEN
                        ALTER TABLE temporal_records
                        ADD CONSTRAINT ck_temporal_records_exactly_one_source
                        CHECK (
                            (asset_id IS NOT NULL) <> (stream_id IS NOT NULL)
                        );
                    END IF;
                END
                $$
                """
            )
        )
