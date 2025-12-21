from models.model import Webhook
from sqlmodel import Session, select


class WebhookRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> list[Webhook]:
        return self.session.exec(select(Webhook).order_by(Webhook.id)).all()

    def get_by_id(self, id: int) -> Webhook:
        webhook = self.session.exec(select(Webhook).where(Webhook.id == id)).first()
        if webhook is None:
            raise ValueError(f"Webhook with id {id} does not exist.")
        return webhook

    def save(self, webhook_: Webhook) -> None:
        self.session.add(webhook_)

    def update(self, webhook_: Webhook) -> None:
        webhook = self.get_by_id(webhook_.id)
        if webhook is None:
            raise ValueError(f"Webhook with id {webhook_.id} does not exist.")
        self.session.add(webhook_)

    def delete_by_id(self, id: int) -> None:
        webhook = self.get_by_id(id)
        if webhook:
            self.session.delete(Webhook)
        else:
            raise ValueError(f"Webhook with id {id} does not exist.")
