# import_targets.py
import asyncio
from sqlalchemy import select
from database.db import async_session, init_db
from database.models import TargetInstitution, TargetDirection


async def seed_targets():
    # 1. Avval jadvallar mavjudligini ta'minlaymiz
    await init_db()

    async with async_session() as session:
        # Tekshiruv: agar bazada allaqachon muassasalar bo'lsa, qayta-qayta qo'shilmasligi uchun to'xtaymiz
        check_existing = await session.execute(select(TargetInstitution))
        if check_existing.scalars().first():
            print("⚠️ Muassasalar bazada allaqachon mavjud! Dublikat bo'lmasligi uchun to'xtatildi.")
            return

        print("🚀 Muassasa va yo'nalishlar bazaga kiritilmoqda...")

        # -------------------------------------------------------------
        # 1. OTM (Fuqarolik): O'zbekiston Milliy Universiteti (O'zMU)
        # -------------------------------------------------------------
        inst_ozmu = TargetInstitution(
            name="O'zbekiston Milliy Universiteti",
            short_name="O'zMU",
            inst_type="otm",
            region="Toshkent shahri",
            logo_url="🏛️"
        )
        session.add(inst_ozmu)
        await session.flush()  # ID sini olish uchun

        dir_ozmu_1 = TargetDirection(
            institution_id=inst_ozmu.id,
            title="Tarix (yo'nalishlar bo'yicha)",
            subject_main="Tarix",
            subject_secondary="Geografiya",
            education_lang="O'zbek",
            grant_score=172.5,
            contract_score=134.2,
            quota=65,
            mock_quiz_id=1
        )
        dir_ozmu_2 = TargetDirection(
            institution_id=inst_ozmu.id,
            title="Falsafa va Mantiq",
            subject_main="Tarix",
            subject_secondary="Ona tili va adabiyot",
            education_lang="O'zbek",
            grant_score=158.0,
            contract_score=118.4,
            quota=30,
            mock_quiz_id=1
        )
        session.add_all([dir_ozmu_1, dir_ozmu_2])

        # -------------------------------------------------------------
        # 2. OTM (Fuqarolik): Toshkent Davlat Yuridik Universiteti (TDYU)
        # -------------------------------------------------------------
        inst_tdyu = TargetInstitution(
            name="Toshkent Davlat Yuridik Universiteti",
            short_name="TDYU",
            inst_type="otm",
            region="Toshkent shahri",
            logo_url="⚖️"
        )
        session.add(inst_tdyu)
        await session.flush()

        dir_tdyu = TargetDirection(
            institution_id=inst_tdyu.id,
            title="Yurisprudensiya (Davlat-huquqiy faoliyat)",
            subject_main="Huquqshunoslik",
            subject_secondary="Tarix",
            education_lang="O'zbek",
            grant_score=184.8,
            contract_score=156.3,
            quota=250,
            mock_quiz_id=2
        )
        session.add(dir_tdyu)

        # -------------------------------------------------------------
        # 3. OTM (Harbiy): Qurolli Kuchlar Akademiyasi
        # -------------------------------------------------------------
        inst_qka = TargetInstitution(
            name="Qurolli Kuchlar Akademiyasi",
            short_name="QKA",
            inst_type="otm_harbiy",
            region="Toshkent shahri",
            logo_url="🎖️"
        )
        session.add(inst_qka)
        await session.flush()

        dir_qka = TargetDirection(
            institution_id=inst_qka.id,
            title="Harbiy xizmat va qo'mondonlik",
            subject_main="Tarix",
            subject_secondary="Matematika",
            education_lang="O'zbek",
            grant_score=165.0,
            contract_score=0.0,
            quota=120,
            mock_quiz_id=3
        )
        session.add(dir_qka)

        # -------------------------------------------------------------
        # 4. Litsey (Harbiy): Temurbeklar Maktabi
        # -------------------------------------------------------------
        inst_tm = TargetInstitution(
            name="Temurbeklar Maktabi Harbiy Akademik Litseyi",
            short_name="TM Litsey",
            inst_type="litsey_harbiy",
            region="Farg'ona",
            logo_url="🛡️"
        )
        session.add(inst_tm)
        await session.flush()

        dir_tm = TargetDirection(
            institution_id=inst_tm.id,
            title="Ijtimoiy-gumanitar fanlar",
            subject_main="Tarix",
            subject_secondary="Psixologiya",
            education_lang="O'zbek",
            grant_score=162.0,
            contract_score=0.0,
            quota=100,
            mock_quiz_id=4
        )
        session.add(dir_tm)

        # -------------------------------------------------------------
        # 5. Litsey (Fuqarolik): SamDU huzuridagi Akademik Litsey
        # -------------------------------------------------------------
        inst_samdu = TargetInstitution(
            name="SamDU huzuridagi Akademik Litsey",
            short_name="SamDU Litsey",
            inst_type="litsey",
            region="Samarqand",
            logo_url="🏫"
        )
        session.add(inst_samdu)
        await session.flush()

        dir_samdu = TargetDirection(
            institution_id=inst_samdu.id,
            title="Ijtimoiy-gumanitar fanlar",
            subject_main="Tarix",
            subject_secondary="Ona tili va adabiyot",
            education_lang="O'zbek",
            grant_score=145.5,
            contract_score=110.0,
            quota=80,
            mock_quiz_id=5
        )
        session.add(dir_samdu)

        # O'zgarishlarni bazaga saqlash
        await session.commit()
        print("✅ Barcha namunaviy muassasalar va yo'nalishlar bazaga muvaffaqiyatli saqlandi!")


if __name__ == "__main__":
    asyncio.run(seed_targets())