from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Field, Session, SQLModel, create_engine, select


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
    created_at: str = Field(default_factory=lambda: datetime.now())  # noqa: DTZ005


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def create_heroes():
    hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson")
    hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador")
    hero_3 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)
    hero_4 = Hero(name="Tarantula", secret_name="Natalia Roman-on", age=32)
    hero_5 = Hero(name="Black Lion", secret_name="Trevor Challa", age=35)
    hero_6 = Hero(name="Dr. Weird", secret_name="Steve Weird", age=36)
    hero_7 = Hero(name="Captain North America", secret_name="Esteban Rogelios", age=93)

    with Session(engine) as session:
        session.add(hero_1)
        session.add(hero_2)
        session.add(hero_3)
        session.add(hero_4)
        session.add(hero_5)
        session.add(hero_6)
        session.add(hero_7)

        session.commit()


def is_older_days(date, days: str = 30) -> bool:
    """指定された日時文字列が指定日付よりも古いかチェック.

    時刻部分は無視し、日付のみで比較する。

    Parameters
    ----------
        date : str
            "%Y-%m-%d %H:%M:%S" 形式の日時文字列(JST)
        days : str
            日付差分

    Returns:
        bool: 指定日数以上であれば True、そうでなければ False
    """
    jst = ZoneInfo("Asia/Tokyo")

    today = datetime.now(jst).date()
    threshold_date = today - timedelta(days=days)

    return date <= threshold_date


def delete_heroes():
    with Session(engine) as session:
        statement = select(Hero).where(Hero.age).limit(1)
        results = session.exec(statement)
        # hero = results.one()
        # print("Hero: ", results.one())
        for hero in results:
            print(hero.age)

        # for result in results.all():
        #     session.delete(result)
        # session.commit()

        # print("Deleted hero:", hero)

        # statement = select(Hero).where(Hero.name == "Spider-Youngster")
        # results = session.exec(statement)
        # hero = results.first()

        # if hero is None:
        #     print("There's no hero named Spider-Youngster")


def main():
    create_db_and_tables()
    create_heroes()
    delete_heroes()


if __name__ == "__main__":
    main()
