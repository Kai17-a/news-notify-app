from sqlmodel import Session, col, func, select

from core.config import logger
from core.models.model import Article
from core.utils import is_older_days


class ArticleRepository:
    """Repository for managing Article database operations.

    This class provides methods to perform CRUD operations on Article objects
    using SQLModel and a database session.

    Attributes:
    ----------
    session : Session
        The SQLModel session for database operations.

    Methods:
    -------
    get_all() -> list[Article]
        Retrieve all articles ordered by id.
    get_by_id(id: int) -> Article
        Retrieve an article by its id.
    get_by_hash(hash: str) -> Article
        Retrieve an article by its hash.
    save(article_: Article) -> None
        Save a new article to the database.
    update(article_: Article) -> None
        Update an existing article in the database.
    delete_by_id(id: int) -> None
        Delete an article by its id.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> list[Article]:
        """Retrieve all articles ordered by id.

        Returns:
        -------
        list[Article]
            A list of all articles in the database, ordered by id.
        """
        return self.session.exec(select(Article).order_by(Article.id)).all()

    def get_with_offset(self, offset: int = 0, limit: int = 20) -> list[Article]:
        """Retrieve articles with offset.

        Parameters
        ----------
        offset : int
        limit : int

        Returns:
        -------
        list[Article]
            A list of all articles in the database, ordered by id.
        """
        articles = self.session.exec(
            select(Article).order_by(col(Article.created_at).desc()).limit(limit).offset(offset)
        ).all()
        return articles

    def get_count(self) -> int:
        return self.session.exec(select(func.count(col(Article.id)))).one()

    def get_by_id(self, article_id: int) -> Article | None:
        """Retrieve an article by its id.

        Parameters
        ----------
        article_id : int
            The id of the article to retrieve.

        Returns:
        -------
        Article
            The article with the specified id.

        Raises:
        ------
        ValueError
            If no article with the specified id exists.
        """
        try:
            article = self.session.get(Article, article_id)
        except Exception:
            logger.exception("Failed to get Article by id")
            return None
        else:
            return article

    def get_by_hash(self, hash_value: str) -> Article | None:
        """Retrieve an article by its hash.

        Parameters
        ----------
        hash_value : str
            The hash of the article to retrieve.

        Returns:
        -------
        Article
            The article with the specified hash.

        Raises:
        ------
        ValueError
            If no article with the specified hash exists.
        """
        try:
            article = self.session.exec(
                select(Article).where(col(Article.hash) == hash_value),
            )
        except Exception:
            logger.exception("Failed to get Article by hash")
            return None
        else:
            return article.first()

    def get_by_url(self, url: str) -> Article | None:
        """Retrieve an article by its url.

        Parameters
        ----------
        url : str
            The URL of the article to retrieve.

        Returns:
        -------
        Article
            The article with the specified URL.

        Raises:
        ------
        ValueError
            If no article with the specified URL exists.
        """
        article = None
        try:
            article = self.session.exec(
                select(Article).where(Article.url == url),
            ).first()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to get Article by url")
            return None
        else:
            return article

    def save(self, article_: Article) -> None:
        """Save a new article to the database.

        Parameters
        ----------
        article_ : Article
            The article object to save.
        """
        self.session.add(article_)

    def update(self, article_: Article) -> None:
        """Update an existing article in the database.

        Parameters
        ----------
        article_ : Article
            The article object with updated values.

        Raises:
        ------
        ValueError
            If no article with the specified id exists.
        """
        article = self.get_by_id(article_.id)
        if article is None:
            error_message = f"Article with id {article_.id} does not exist."
            raise ValueError(error_message)
        self.session.merge(article_)

    def delete_by_id(self, article_id: int) -> None:
        """Delete an article by its id.

        Parameters
        ----------
        article_id : int
            The id of the article to delete.

        Raises:
        ------
        ValueError
            If no article with the specified id exists.
        """
        article = self.get_by_id(article_id)
        if article:
            self.session.delete(article)
        else:
            error_message = f"Article with id {article_id} does not exist."
            raise ValueError(error_message)

    def delete_old_articles(self, days: int = 30) -> int:
        """Delete articles older than the specified number of days.

        Parameters
        ----------
        days : int, optional
            Number of days to keep articles. Articles older than this
            value will be deleted. Default is 30.

        Raises:
        ------
        ValueError
            If an invalid value for `days` is provided.
        """
        if days <= 0:
            error_message = "`days` must be a positive integer."
            raise ValueError(error_message)

        statement = select(Article).where(is_older_days(Article.created_at))
        results = self.session.exec(statement)
        deleted_num = 0
        for result in results.all():
            self.session.delete(result)
            deleted_num += 1

        return deleted_num
