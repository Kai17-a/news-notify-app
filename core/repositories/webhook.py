from models.model import Webhook
from sqlmodel import Session, select


class WebhookRepository:
    """Repository for managing Webhook entities.

    This class provides methods to perform CRUD operations on Webhook objects
    using SQLModel session.

    Attributes:
    ----------
    session : Session
        The SQLModel session for database operations.

    Methods:
    -------
    get_all() -> list[Webhook]
        Retrieve all webhooks ordered by id.
    get_by_id(id: int) -> Webhook
        Retrieve a webhook by its id.
    save(webhook_: Webhook) -> None
        Save a new webhook to the database.
    update(webhook_: Webhook) -> None
        Update an existing webhook.
    delete_by_id(id: int) -> None
        Delete a webhook by its id.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> list[Webhook]:
        """Retrieve all webhooks ordered by id.

        Returns:
        --------
        list[Webhook]
            A list of all webhook objects ordered by id.
        """
        return self.session.exec(select(Webhook).order_by(Webhook.id)).all()

    def get_by_id(self, webhook_id: int) -> Webhook:
        """Retrieve a webhook by its id.

        Parameters:
        -----------
        webhook_id : int
            The id of the webhook to retrieve.

        Returns:
        --------
        Webhook
            The webhook object with the specified id.

        Raises:
        -------
        ValueError
            If no webhook with the specified id exists.
        """
        webhook = self.session.exec(
            select(Webhook).where(Webhook.id == webhook_id),
        ).first()
        if webhook is None:
            error_message = f"Webhook with id {webhook_id} does not exist."
            raise ValueError(error_message)
        return webhook

    def save(self, webhook_: Webhook) -> None:
        """Save a new webhook to the database.

        Parameters:
        -----------
        webhook_ : Webhook
            The webhook object to save.
        """
        self.session.add(webhook_)

    def update(self, webhook_: Webhook) -> None:
        """Update an existing webhook.

        Parameters:
        -----------
        webhook_ : Webhook
            The webhook object with updated values.
        """
        webhook = self.get_by_id(webhook_.id)
        if webhook is None:
            error_message = f"Webhook with id {webhook_.id} does not exist."
            raise ValueError(error_message)
        self.session.add(webhook_)

    def delete_by_id(self, webhook_id: int) -> None:
        """Delete a webhook by its id.

        Parameters:
        -----------
        webhook_id : int
            The id of the webhook to delete.
        """
        webhook = self.get_by_id(webhook_id)
        if webhook:
            self.session.delete(webhook)
        else:
            error_message = f"Webhook with id {webhook_id} does not exist."
            raise ValueError(error_message)
