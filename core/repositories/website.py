from models.model import Website
from sqlmodel import Session, select


class WebsiteRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Website]:
        return self.session.exec(select(Website).order_by(Website.id)).all()

    def get_by_id(self, id: int) -> Website:
        website = self.session.exec(select(Website).where(Website.id == id)).first()
        if website is None:
            raise ValueError(f"Website with id {id} does not exist.")
        return website

    def save(self, website_: Website) -> None:
        self.session.add(website_)

    def update(self, website_: Website) -> None:
        website = self.get_by_id(website_.id)
        if website is None:
            raise ValueError(f"Website with id {website_.id} does not exist.")
        self.session.add(website_)

    def delete_by_id(self, id: int) -> None:
        website = self.get_by_id(id)
        if website:
            self.session.delete(Website)
        else:
            raise ValueError(f"Website with id {id} does not exist.")
