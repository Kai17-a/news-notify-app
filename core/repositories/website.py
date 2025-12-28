from models.model import Website
from sqlmodel import Session, select


class WebsiteRepository:
    """Repository for managing Website entities.

    Attributes:
    ----------
    session : Session
        SQLModel session for database operations.

    Methods:
    -------
    get_all() -> list[Website]
        Retrieve all websites ordered by id.
    get_by_id(id: int) -> Website
        Retrieve a website by its id.
    save(website_: Website) -> None
        Save a new website to the database.
    update(website_: Website) -> None
        Update an existing website.
    delete_by_id(id: int) -> None
        Delete a website by its id.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> list[Website]:
        """Retrieve all websites ordered by id.

        Returns:
        -------
        list[Website]
            A list of all website objects ordered by id.
        """
        return self.session.exec(select(Website).order_by(Website.id)).all()

    def get_by_id(self, website_id: int) -> Website:
        """Retrieve a website by its id.

        Parameters:
        ----------
        website_id : int
            The id of the website to retrieve.

        Returns:
        -------
        Website
            The website object with the specified id.

        Raises:
        ------
        ValueError
            If the website with the given id does not exist.
        """
        website = self.session.exec(
            select(Website).where(Website.id == website_id),
        ).first()
        if website is None:
            msg = f"Website with id {id} does not exist."
            raise ValueError(msg)
        return website

    def save(self, website_: Website) -> None:
        """Save a new website to the database.

        Parameters:
        ----------
        website_ : Website
            The website object to save.
        """
        self.session.add(website_)

    def update(self, website_: Website) -> None:
        """Update an existing website in the database.

        Parameters:
        ----------
        website_ : Website
            The website object with updated data.

        Raises:
        ------
        ValueError
            If the website with the given id does not exist.
        """
        website = self.get_by_id(website_.id)
        if website is None:
            msg = f"Website with id {website_.id} does not exist."
            raise ValueError(msg)
        self.session.add(website_)

    def delete_by_id(self, website_id: int) -> None:
        """Delete a website by its id.

        Parameters:
        ----------
        website_id : int
            The id of the website to delete.

        Raises:
        ------
        ValueError
            If the website with the given id does not exist.
        """
        website = self.get_by_id(website_id)
        if website:
            self.session.delete(website)
        else:
            msg = f"Website with id {website_id} does not exist."
            raise ValueError(msg)
