from models.model import Article
from sqlmodel import Session, select


class ArticleRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Article]:
        return self.session.exec(select(Article).order_by(Article.id)).all()

    def get_by_id(self, id: int) -> Article:
        article = self.session.exec(select(Article).where(Article.id == id)).first()
        if article is None:
            raise ValueError(f"Article with id {id} does not exist.")
        return article

    def get_by_hash(self, hash: str) -> Article:
        article = self.session.exec(select(Article).where(Article.hash == hash)).first()
        if article is None:
            raise ValueError(f"Article with hash {hash} does not exist.")
        return article

    def save(self, article_: Article) -> None:
        self.session.add(article_)

    def update(self, article_: Article) -> None:
        article = self.get_by_id(article_.id)
        if article is None:
            raise ValueError(f"Article with id {article_.id} does not exist.")
        self.session.add(article_)

    def delete_by_id(self, id: int) -> None:
        article = self.get_by_id(id)
        if article:
            self.session.delete(article)
        else:
            raise ValueError(f"Article with id {id} does not exist.")
