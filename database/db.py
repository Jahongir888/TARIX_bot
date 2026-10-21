from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from database.models import Base

# SQLite asinxron fayl manzili
DATABASE_URL = "sqlite+aiosqlite:///./database.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


def _ensure_sqlite_columns(sync_conn):
    """Mavjud jadvallarga yangi ustunlarni xavfsiz qo'shadi (SQLite)."""
    required = {
        "user_octagon_profiles": {
            "subject_focus": "VARCHAR DEFAULT 'tarix'",
            "region": "VARCHAR",
            "subscription_tier": "VARCHAR DEFAULT 'free'",
            "last_seen_at": "DATETIME",
        },
        "products": {
            "is_module": "BOOLEAN DEFAULT 0",
            "parent_product_id": "INTEGER",
            "subject_id": "INTEGER",
        },
        "target_directions": {
            "cipher": "VARCHAR",
            "edu_form": "VARCHAR",
            "edu_lang": "VARCHAR",
            "subject_second": "VARCHAR",
            "mandatory_subjects": "VARCHAR",
            "subject_block": "VARCHAR",
            "grant_ball": "FLOAT DEFAULT 0",
            "contract_ball": "FLOAT DEFAULT 0",
        },
        "exam_quizzes": {
            "command_path": "VARCHAR",
            "visible_at": "DATETIME",
            "starts_at": "DATETIME",
            "base_price": "INTEGER DEFAULT 0",
            "free_for_courses": "VARCHAR DEFAULT ''",
            "share_discount_percent": "INTEGER DEFAULT 0",
            "full_analysis_video": "VARCHAR",
        },
        "exam_questions": {
            "image_top": "VARCHAR",
            "image_bottom": "VARCHAR",
            "difficulty_beta": "FLOAT DEFAULT 2.0",
            "option_sources": "TEXT",
            "solution_text": "TEXT",
            "video_solution_url": "VARCHAR",
        },
        "exam_submissions": {
            "ability_theta": "FLOAT",
        },
    }
    for table, columns in required.items():
        rows = sync_conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        if not rows:
            continue
        existing = {row[1] for row in rows}
        for col_name, col_type in columns.items():
            if col_name not in existing:
                sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))

    dir_rows = sync_conn.execute(text("PRAGMA table_info(target_directions)")).fetchall()
    if dir_rows:
        sync_conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_target_directions_subject_block "
            "ON target_directions (subject_block)"
        ))
        sync_conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_target_directions_cipher "
            "ON target_directions (cipher)"
        ))

    quiz_rows = sync_conn.execute(text("PRAGMA table_info(exam_quizzes)")).fetchall()
    if quiz_rows:
        sync_conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_exam_quizzes_command_path "
            "ON exam_quizzes (command_path)"
        ))


# Jadvallarni avtomatik yaratish funksiyasi
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_sqlite_columns)