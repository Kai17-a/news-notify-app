from sqlmodel import Session, select

from core.config import logger
from core.models.model import Website


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
        try:
            results = self.session.exec(select(Website).order_by(Website.id)).all()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to get all website")
            return []
        else:
            return results

    def get_all_with_active(self) -> list[Website]:
        """Retrieve all websites with status is active ordered by id.

        Returns:
        -------
        list[Website]
            A list of all website objects with active ordered by id.
        """
        try:
            results = self.session.exec(
                select(Website).where(Website.is_active).order_by(Website.id),
            ).all()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to get website with active status")
            return []
        else:
            return results

    def get_by_id(self, website_id: int) -> Website | None:
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

        website.name = website_.name
        website.type = website_.type
        website.url = website_.url
        website.avatar = website_.avatar
        website.selector = website_.selector
        website.is_active = website_.is_active
        website.needs_translation = website_.needs_translation
        website.target_webhook_ids = website_.target_webhook_ids

        self.session.add(website_)
        self.session.refresh(website_)

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
