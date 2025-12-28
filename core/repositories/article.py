from models.model import Article
from sqlmodel import Session, select


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

    def get_by_id(self, article_id: int) -> Article:
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
        article = self.session.exec(
            select(Article).where(Article.id == article_id),
        ).first()
        if article is None:
            error_message = f"Article with id {article_id} does not exist."
            raise ValueError(error_message)
        return article

    def get_by_hash(self, hash_value: str) -> Article:
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
        article = self.session.exec(
            select(Article).where(Article.hash == hash_value),
        ).first()
        if article is None:
            error_message = f"Article with hash {hash} does not exist."
            raise ValueError(error_message)
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
